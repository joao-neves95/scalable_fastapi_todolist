from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from pydantic import AfterValidator

from shared.clients.auth_client import get_user_credentials_async
from shared.lib.fastapi_utils import request_is_internal_api_key_valid
from shared.lib.HTTPException_utils import (
    invalid_credentials_exception,
    raise_if_user_has_no_permissions,
    user_has_no_permissions_exception,
)
from shared.lib.jwt_utils import decode_token, is_user_jwt_admin
from shared.lib.ulid_validators import validate_str_ulid
from shared.models.auth_dtos import UserCredentials
from shared.models.status_response_dto import StatusResponse
from shared.models.user_dto import User
from users_api.data.entities.data_user import DataUser
from users_api.data.mapper_utils import data_user_to_model, update_data_user_from_model
from users_api.data.query_utils import (
    select_user_by_ulid_async,
)

api_users_router = APIRouter(prefix="/users")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/logins/openapi")


def get_is_user_jwt_admin(token: Annotated[str, Depends(oauth2_scheme)]) -> bool:
    try:
        return is_user_jwt_admin(token)

    except InvalidTokenError:
        raise invalid_credentials_exception


async def get_jwt_data_user_async(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> DataUser:
    try:
        token_data = decode_token(token=token)

    except InvalidTokenError:
        raise invalid_credentials_exception

    user = await select_user_by_ulid_async(token_data.sub)
    if user is None:
        raise invalid_credentials_exception

    return user


async def get_jwt_user_async(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User:
    data_user = await get_jwt_data_user_async(token)
    return data_user_to_model(data_user)


# TODO: add pagination.
@api_users_router.get("/")
async def get_users(
    is_current_user_admin: Annotated[bool, Depends(get_is_user_jwt_admin)],
) -> StatusResponse[list[User]]:
    if not is_current_user_admin:
        raise user_has_no_permissions_exception

    all_users = await DataUser.all()
    all_users = [data_user_to_model(data_user) for data_user in all_users]

    return StatusResponse(
        status_code=200, message="List of all users", content=all_users
    )


@api_users_router.get("/{ulid}")
async def get_user(
    ulid: Annotated[str, Path(), AfterValidator(validate_str_ulid)],
    current_user: Annotated[User, Depends(get_jwt_user_async)],
) -> StatusResponse[User]:
    raise_if_user_has_no_permissions(
        token_user_ulid=current_user.ulid, request_user_ulid=current_user.ulid
    )

    user_credentials = await get_user_credentials_async(ulid)
    current_user.credentials = UserCredentials(
        user_ulid=current_user.ulid, email=user_credentials.email
    )

    return StatusResponse(
        status_code=200,
        message=f"User '{ulid}' found",
        content=current_user,
    )


# TODO: Make this method private, only accessible inside a private network.
@api_users_router.post("/")
async def create_user(request: Request) -> StatusResponse[User]:
    if not request_is_internal_api_key_valid(request):
        raise HTTPException(status_code=403, detail="Forbidden")

    new_user = await DataUser.create()

    return StatusResponse(
        status_code=201,
        message=f"User '{new_user.ulid}' created",
        content=data_user_to_model(new_user),
    )


@api_users_router.put("/{user_ulid}")
async def update_user(
    user_ulid: Annotated[str, Path(), AfterValidator(validate_str_ulid)],
    user_model: User,
    current_data_user: Annotated[DataUser, Depends(get_jwt_data_user_async)],
) -> StatusResponse[User]:
    raise_if_user_has_no_permissions(
        token_user_ulid=current_data_user.ulid, request_user_ulid=user_ulid
    )

    update_data_user_from_model(current_data_user, user_model)
    await current_data_user.save()

    return StatusResponse(
        status_code=204,
        message=f"User '{user_ulid}' updated",
        content=data_user_to_model(current_data_user),
    )


# TODO: Make this method private, only accessible inside a private network.
@api_users_router.delete("/{ulid}")
async def delete_user(
    ulid: Annotated[str, Path(), AfterValidator(validate_str_ulid)], request: Request
) -> StatusResponse:
    if not request_is_internal_api_key_valid(request):
        raise HTTPException(status_code=403, detail="Forbidden")

    user = await select_user_by_ulid_async(ulid)
    if user is not None:
        await user.delete()

    return StatusResponse(
        status_code=204,
        message=f"User '{ulid}' deleted",
    )
