from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError
from pydantic import AfterValidator
from tortoise.transactions import in_transaction

from shared.clients.users_client import get_user_by_ulid_async
from shared.lib.HTTPException_utils import (
    invalid_credentials_exception,
    raise_if_user_has_no_permissions,
)
from shared.lib.jwt_utils import decode_token
from shared.lib.list_utils import try_get
from shared.lib.ulid_validators import validate_str_ulid
from shared.models.items_dtos import Item, NewItem
from shared.models.status_response_dto import StatusResponse
from shared.models.user_dto import User
from todo_api.data.entities.data_item import DataItem
from todo_api.data.mapper_utils import data_item_to_model, update_data_item_from_model

api_user_items_router = APIRouter(prefix="/users/{user_ulid}/items")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/logins/openapi")


# TODO: Add caching here.
async def get_jwt_user_async(
    token: Annotated[str, Depends(oauth2_scheme)],
) -> User | None:
    try:
        token_data = decode_token(token=token)

    except InvalidTokenError:
        raise invalid_credentials_exception

    return (await get_user_by_ulid_async(token_data.sub, token)).content


# TODO: add pagination.
@api_user_items_router.get("/")
async def get_all_user_items(
    user_ulid: Annotated[str, Path(), AfterValidator(validate_str_ulid)],
    current_user: Annotated[User, Depends(get_jwt_user_async)],
) -> StatusResponse[list[Item]]:
    raise_if_user_has_no_permissions(
        token_user_ulid=current_user.ulid, request_user_ulid=user_ulid
    )

    all_user_items = await DataItem.filter(user_ulid=current_user.ulid)

    all_user_items = [data_item_to_model(item) for item in all_user_items]

    return StatusResponse(
        status_code=200,
        message=f"All items for user '{user_ulid}'",
        content=all_user_items,
    )


@api_user_items_router.get("/{ulid}", responses={404: {"description": "Not found"}})
async def get_item(
    user_ulid: Annotated[str, Path(), AfterValidator(validate_str_ulid)],
    ulid: Annotated[str, Path(), AfterValidator(validate_str_ulid)],
    current_user: Annotated[User, Depends(get_jwt_user_async)],
) -> StatusResponse[Item]:
    raise_if_user_has_no_permissions(
        token_user_ulid=current_user.ulid, request_user_ulid=user_ulid
    )

    data_item = try_get(await DataItem.filter(ulid=ulid), 0)

    if data_item is None:
        raise HTTPException(status_code=404, detail=f"Item '{ulid} not found")

    return StatusResponse(
        status_code=200,
        message=f"Item '{data_item.ulid}' found",
        content=data_item_to_model(data_item),
    )


@api_user_items_router.post("/")
async def create_item(
    user_ulid: Annotated[str, Path(), AfterValidator(validate_str_ulid)],
    item: NewItem,
    current_user: Annotated[User, Depends(get_jwt_user_async)],
) -> StatusResponse[Item]:
    raise_if_user_has_no_permissions(
        token_user_ulid=current_user.ulid, request_user_ulid=user_ulid
    )

    new_data_item = update_data_item_from_model(DataItem(), item)

    async with in_transaction():
        await new_data_item.save()

    return StatusResponse(
        status_code=201,
        message=f"Item '{new_data_item.ulid}' created",
        content=data_item_to_model(data_item=new_data_item),
    )


@api_user_items_router.put("/{ulid}")
async def update_item(
    user_ulid: Annotated[str, Path(), AfterValidator(validate_str_ulid)],
    ulid: Annotated[str, Path(), AfterValidator(validate_str_ulid)],
    item: Item,
    current_user: Annotated[User, Depends(get_jwt_user_async)],
) -> StatusResponse[Item]:
    raise_if_user_has_no_permissions(
        token_user_ulid=current_user.ulid, request_user_ulid=user_ulid
    )

    data_item = await DataItem.get(ulid=ulid, user_ulid=current_user.ulid)
    update_data_item_from_model(data_item, item)
    await data_item.save()

    return StatusResponse(
        status_code=200,
        message=f"Item '{ulid}' updated",
        content=data_item_to_model(data_item=data_item),
    )


@api_user_items_router.delete("/{ulid}")
async def delete_item(
    user_ulid: Annotated[str, Path(), AfterValidator(validate_str_ulid)],
    ulid: Annotated[str, Path(), AfterValidator(validate_str_ulid)],
    current_user: Annotated[User, Depends(get_jwt_user_async)],
) -> StatusResponse:
    raise_if_user_has_no_permissions(
        token_user_ulid=current_user.ulid, request_user_ulid=user_ulid
    )

    deleted_count = await DataItem.filter(
        ulid=ulid, user_ulid=current_user.ulid
    ).delete()

    if not deleted_count:
        raise HTTPException(status_code=404, detail=f"Item '{ulid}' not found")

    return StatusResponse(
        status_code=204, message=f"Item '{ulid}' deleted", content=None
    )
