import httpx
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from shared.lib.application_variables import ApplicationVariables
from shared.lib.constants import INTERNAL_API_KEY_HEADER_NAME
from shared.models.auth_dtos import LoginUserResponse, UserCredentials
from shared.models.status_response_dto import StatusResponse


async def get_user_credentials_async(user_ulid: str) -> UserCredentials:
    async with httpx.AsyncClient() as client:
        user_credentials_response = await client.get(
            f"{ApplicationVariables.AUTH_API_PRIVATE_URL()}/api/v1/auth/{user_ulid}",
            headers={
                INTERNAL_API_KEY_HEADER_NAME: ApplicationVariables.INTERNAL_API_KEY()
                or ""
            },
        )

    user_credentials_response.raise_for_status()
    response = StatusResponse[UserCredentials](**user_credentials_response.json())

    if response.content is None:
        raise HTTPException(status_code=500)

    return response.content


async def login_user_async(
    login_form_data: OAuth2PasswordRequestForm,
) -> StatusResponse[LoginUserResponse]:
    async with httpx.AsyncClient() as client:
        create_response = await client.post(
            f"{ApplicationVariables.AUTH_API_PRIVATE_URL()}/api/v1/auth/logins",
            json={
                "email": login_form_data.username,
                "password": login_form_data.password,
            },
        )

    create_response.raise_for_status()

    return StatusResponse[LoginUserResponse](**create_response.json())
