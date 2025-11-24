from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Request
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from pydantic import AfterValidator
from redis.asyncio import Redis
from tortoise.transactions import in_transaction

from shared.clients.auth_client import get_user_credentials_async
from shared.lib.fastapi_utils import request_is_internal_api_key_valid
from shared.lib.HTTPException_utils import (
    invalid_credentials_exception,
    raise_if_user_has_no_permissions,
    user_has_no_permissions_exception,
    user_not_found_exception,
)
from shared.lib.jwt_utils import decode_token, is_user_jwt_admin
from shared.lib.redis_utils import get_redis_client_async
from shared.lib.ulid_validators import validate_str_ulid
from shared.models.auth_dtos import UserCredentials
from shared.models.jwt_dtos import JwtTokenData
from shared.models.status_response_dto import StatusResponse
from shared.models.user_dto import User
from users_api.data.db_query_utils import (
    select_user_by_ulid_async,
)
from users_api.data.entities.data_user import DataUser
from users_api.data.mapper_utils import data_user_to_model, update_data_user_from_model
from users_api.data.redis_query_utils import (
    delete_cached_user_async,
    get_cached_user_async,
    set_cached_user_async,
)

api_users_router = APIRouter(prefix="/users")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/logins/openapi")


def get_is_user_jwt_admin(token: Annotated[str, Depends(oauth2_scheme)]) -> bool:
    try:
        return is_user_jwt_admin(token)

    except InvalidTokenError:
        raise invalid_credentials_exception


def get_token_data(token: Annotated[str, Depends(oauth2_scheme)]):
    return decode_token(token)


async def get_jwt_data_user_async(
    token_data: Annotated[JwtTokenData, Depends(get_token_data)],
) -> DataUser:
    user = await select_user_by_ulid_async(token_data.sub)
    if user is None:
        raise user_not_found_exception(token_data.sub)

    return user


async def get_jwt_user_async(
    token_data: Annotated[JwtTokenData, Depends(get_token_data)],
    redis: Annotated[Redis, Depends(get_redis_client_async)],
) -> User:
    return await get_cached_user_async(redis, token_data.sub)


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


@api_users_router.post("/")
async def create_user(
    request: Request, redis: Annotated[Redis, Depends(get_redis_client_async)]
) -> StatusResponse[User]:
    if not request_is_internal_api_key_valid(request):
        raise HTTPException(status_code=403, detail="Forbidden")

    async with in_transaction():
        try:
            new_user = await DataUser.create()
            user = data_user_to_model(new_user)
            await set_cached_user_async(redis, new_user.ulid, user)

        except Exception:
            raise HTTPException(
                status_code=500, detail="Something went wrong during user creation.",
            )

    return StatusResponse(
        status_code=201,
        message=f"User '{new_user.ulid}' created",
        content=user,
    )


@api_users_router.put("/{user_ulid}")
async def update_user(
    user_ulid: Annotated[str, Path(), AfterValidator(validate_str_ulid)],
    user_model: User,
    current_data_user: Annotated[DataUser, Depends(get_jwt_data_user_async)],
    redis: Annotated[Redis, Depends(get_redis_client_async)],
) -> StatusResponse[User]:
    raise_if_user_has_no_permissions(
        token_user_ulid=current_data_user.ulid, request_user_ulid=user_ulid
    )

    update_data_user_from_model(current_data_user, user_model)

    async with in_transaction():
        try:
            await current_data_user.save()
            user = data_user_to_model(current_data_user)
            await set_cached_user_async(redis, user_ulid, user)

        except Exception:
            raise HTTPException(
                status_code=500, detail="Something went wrong during user update."
            )

    return StatusResponse(
        status_code=204,
        message=f"User '{user_ulid}' updated",
        content=user,
    )


@api_users_router.delete("/{ulid}")
async def delete_user(
    user_ulid: Annotated[str, Path(), AfterValidator(validate_str_ulid)],
    request: Request,
    redis: Annotated[Redis, Depends(get_redis_client_async)],
) -> StatusResponse:
    if not request_is_internal_api_key_valid(request):
        raise HTTPException(status_code=403, detail="Forbidden")

    user = await select_user_by_ulid_async(user_ulid)
    if not user:
        raise user_not_found_exception(user_ulid)

    async with in_transaction():
        try:
            await user.delete()
            await delete_cached_user_async(redis, user_ulid)

        except Exception:
            raise HTTPException(
                status_code=500, detail="Something went wrong during user creation."
            )

    return StatusResponse(
        status_code=204,
        message=f"User '{user_ulid}' deleted",
    )
