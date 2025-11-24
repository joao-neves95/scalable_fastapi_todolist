from dotenv import load_dotenv
from fastapi import FastAPI
from tortoise.contrib.fastapi import tortoise_exception_handlers

from routers.auth import api_auth_router
from shared.lib.fastapi_utils import app_add_cors, app_lifespan

load_dotenv()

app = FastAPI(
    lifespan=app_lifespan(
        app_folder="auth_api",
        modules={
            "entities": [
                "auth_api.data.entities.data_user_credentials",
            ]
        },
        use_redis=True
    ),
    exception_handlers=tortoise_exception_handlers(),
)
app_add_cors(app)
app.include_router(api_auth_router, prefix="/api/v1")
