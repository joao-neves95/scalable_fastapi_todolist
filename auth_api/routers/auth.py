from datetime import timedelta
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Path, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt import InvalidTokenError
from pydantic import AfterValidator
from tortoise.transactions import in_transaction

from auth_api.data.entities.data_user_credentials import DataUserCredentials
from auth_api.data.mapper_utils import data_user_credentials_to_model
from auth_api.data.query_utils import (
    select_user_credentials_by_email_async,
    select_user_credentials_by_user_ulid_async,
)
from shared.clients.users_client import (
    create_user_with_client_async,
    delete_user_with_client_async,
)
from shared.lib.application_variables import ApplicationVariables
from shared.lib.crypto import hash_password, verify_password
from shared.lib.HTTPException_utils import (
    email_already_exists_exception,
    invalid_credentials_exception,
    invalid_login_credentials_exception,
    raise_if_user_has_no_permissions,
)
from shared.lib.jwt_utils import (
    create_access_token,
    decode_token,
    is_user_jwt_admin,
)
from shared.lib.ulid_validators import validate_str_ulid
from shared.models.auth_dtos import (
    LoginUser,
    LoginUserResponse,
    RegisterUser,
    UserCredentials,
)
from shared.models.jwt_dtos import JwtToken, JwtTokenDataInput
from shared.models.status_response_dto import StatusResponse

api_auth_router = APIRouter(prefix="/auth")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/logins/openapi")


def get_is_user_jwt_admin(token: Annotated[str, Depends(oauth2_scheme)]) -> bool:
    try:
        return is_user_jwt_admin(token)

    except InvalidTokenError:
        raise invalid_credentials_exception


async def get_jwt_data_user_credentials_async(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> DataUserCredentials:
    try:
        token_data = decode_token(token=token)

    except InvalidTokenError:
        raise invalid_credentials_exception

    user = await select_user_credentials_by_user_ulid_async(token_data.sub)
    if user is None:
        raise invalid_credentials_exception

    return user


async def get_jwt_user_credentials_async(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> UserCredentials:
    data_user = await get_jwt_data_user_credentials_async(token)
    return data_user_credentials_to_model(data_user)


# TODO: Make this method private, only accessible inside a private network.
# TODO: Cache this.
@api_auth_router.get("/{ulid}")
async def get_user_credentials(
    ulid: Annotated[str, Path(), AfterValidator(validate_str_ulid)],
    x_internal_api_key: Annotated[str, Header()],
) -> StatusResponse[UserCredentials]:
    if x_internal_api_key != ApplicationVariables.INTERNAL_API_KEY():
        raise HTTPException(status_code=403, detail="Forbidden")

    data_user_credentials = await select_user_credentials_by_user_ulid_async(ulid)

    if data_user_credentials is None:
        return StatusResponse(
            status_code=404,
            message=f"User '{ulid}' not found",
        )

    return StatusResponse(
        status_code=200,
        message=f"User '{ulid}' found",
        content=data_user_credentials_to_model(data_user_credentials),
    )


@api_auth_router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(register_user_model: RegisterUser) -> StatusResponse:
    data_user_credentials = await select_user_credentials_by_email_async(
        register_user_model.email
    )
    if data_user_credentials is not None:
        raise email_already_exists_exception

    async with in_transaction():
        new_user = None
        new_user_ulid = None
        async with httpx.AsyncClient() as client:
            try:
                new_user = await create_user_with_client_async(client)
                new_user_ulid = new_user.content.ulid if new_user.content else ""

                (hash, salt) = hash_password(register_user_model.password)

                await DataUserCredentials.create(
                    user_ulid=new_user_ulid,
                    email=register_user_model.email,
                    password_hash=hash,
                    salt=salt,
                )
            except Exception as e:
                if new_user is not None and new_user_ulid is not None:
                    await delete_user_with_client_async(client, new_user_ulid)
                raise e

    if new_user is None:
        raise HTTPException(
            status_code=500, detail="An error occurred. User not created"
        )

    return StatusResponse(status_code=201, message=f"User {new_user_ulid} created")


@api_auth_router.put("/{user_ulid}/credentials")
async def update_user_credentials(
    user_ulid: Annotated[str, Path(), AfterValidator(validate_str_ulid)],
    register_user_model: RegisterUser,
    current_data_user_credentials: Annotated[
        DataUserCredentials, Depends(get_jwt_data_user_credentials_async)
    ],
) -> StatusResponse:
    raise_if_user_has_no_permissions(
        token_user_ulid=current_data_user_credentials.user_ulid,
        request_user_ulid=user_ulid,
    )

    (hash, salt) = hash_password(register_user_model.password)
    current_data_user_credentials.password_hash = hash
    current_data_user_credentials.salt = salt
    await current_data_user_credentials.save()

    return StatusResponse(
        status_code=204, message=f"User '{user_ulid}' credentials updated"
    )


@api_auth_router.post(
    "/logins/openapi", responses={401: {"description": "Unauthorized"}}
)
async def login_open_api(
    login_form_data: OAuth2PasswordRequestForm = Depends(),
) -> JwtToken:
    _, access_token = await login_async(
        login_form_data.username, login_form_data.password
    )

    return JwtToken(access_token=access_token, token_type="bearer")


@api_auth_router.post("/logins", responses={401: {"description": "Unauthorized"}})
async def login_user(
    login_user_model: LoginUser,
) -> StatusResponse[LoginUserResponse]:
    data_user_credentials, access_token = await login_async(
        login_user_model.email, login_user_model.password
    )

    return StatusResponse(
        status_code=200,
        message="Authentication successful",
        content=LoginUserResponse(
            user_credentials=data_user_credentials_to_model(data_user_credentials),
            token=JwtToken(access_token=access_token, token_type="bearer"),
        ),
    )


async def login_async(email: str, password: str) -> tuple[DataUserCredentials, str]:
    data_user_credentials = await select_user_credentials_by_email_async(email)

    if data_user_credentials is None:
        raise invalid_login_credentials_exception

    if not verify_password(
        data_user_credentials.password_hash,
        password,
        data_user_credentials.salt,
    ):
        raise invalid_login_credentials_exception

    return (
        data_user_credentials,
        create_access_token(
            JwtTokenDataInput(sub=data_user_credentials.user_ulid, admin=True),
            expires_delta=timedelta(minutes=ApplicationVariables.JWT_EXPIRE_MINUTES()),
        ),
    )
