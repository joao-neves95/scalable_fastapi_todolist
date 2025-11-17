from fastapi import FastAPI
from tortoise.contrib.fastapi import tortoise_exception_handlers

from routers.users import api_users_router
from shared.lib.fastapi_utils import app_lifespan

app = FastAPI(
    lifespan=app_lifespan(
        modules={
            "entities": [
                "users_api.data.entities.data_user",
            ]
        }
    ),
    exception_handlers=tortoise_exception_handlers(),
)
app.include_router(api_users_router, prefix="/api/v1")
