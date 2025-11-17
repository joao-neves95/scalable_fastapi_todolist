from fastapi import FastAPI
from tortoise.contrib.fastapi import tortoise_exception_handlers

from routers.user_items import api_user_items_router
from shared.lib.fastapi_utils import app_lifespan

app = FastAPI(
    lifespan=app_lifespan(
        modules={
            "entities": [
                "todo_api.data.entities.data_item",
            ]
        }
    ),
    exception_handlers=tortoise_exception_handlers(),
)
app.include_router(api_user_items_router, prefix="/api/v1")
