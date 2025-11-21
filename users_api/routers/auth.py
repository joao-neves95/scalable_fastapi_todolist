from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from shared.clients.auth_client import login_user_async
from shared.models.jwt_dtos import JwtToken

api_auth_router = APIRouter(prefix="/auth")


@api_auth_router.post(
    "/logins/openapi", responses={401: {"description": "Unauthorized"}}
)
async def login_open_api(
    login_form_data: OAuth2PasswordRequestForm = Depends(),
) -> JwtToken:
    status_response = await login_user_async(login_form_data)

    if status_response.content is None:
        raise HTTPException(status_code=500)

    return status_response.content.token
