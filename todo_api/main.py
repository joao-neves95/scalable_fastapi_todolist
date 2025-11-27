from dotenv import load_dotenv
from fastapi import FastAPI
from tortoise.contrib.fastapi import tortoise_exception_handlers

from shared.lib.constants import APP_NAME_TODO_API
from shared.lib.fastapi_utils import app_add_cors, app_lifespan
from todo_api.routers.auth_proxy import api_auth_router
from todo_api.routers.user_items import api_user_items_router

load_dotenv()

app = FastAPI(
    lifespan=app_lifespan(
        app_folder=APP_NAME_TODO_API,
        modules={
            "entities": [
                f"{APP_NAME_TODO_API}.data.entities.data_item",
            ]
        },
    ),
    exception_handlers=tortoise_exception_handlers(),
)
app_add_cors(app)
app.include_router(api_user_items_router, prefix="/api/v1")
app.include_router(api_auth_router, prefix="/api/v1")
