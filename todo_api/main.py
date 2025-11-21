from dotenv import load_dotenv
from fastapi import FastAPI
from tortoise.contrib.fastapi import tortoise_exception_handlers

from routers.auth import api_auth_router
from routers.user_items import api_user_items_router
from shared.lib.fastapi_utils import app_add_cors, app_lifespan

load_dotenv()

app = FastAPI(
    lifespan=app_lifespan(
        app_folder="todo_api",
        modules={
            "entities": [
                "todo_api.data.entities.data_item",
            ]
        },
    ),
    exception_handlers=tortoise_exception_handlers(),
)
app_add_cors(app)
app.include_router(api_user_items_router, prefix="/api/v1")
app.include_router(api_auth_router, prefix="/api/v1")
