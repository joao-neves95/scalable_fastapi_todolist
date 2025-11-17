from contextlib import asynccontextmanager
import os

from fastapi import FastAPI
from tortoise.contrib.fastapi import RegisterTortoise, tortoise_exception_handlers

from routers.auth import api_auth_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with RegisterTortoise(
        app=app,
        modules={"entities": ["auth_api.data.entities.data_user_credentials"]},
        db_url=f"sqlite:///{os.path.abspath('db.sqlite3')}",
        # Use UTC.
        use_tz=True,
        add_exception_handlers=True,
        generate_schemas=True,
    ):
        yield


app = FastAPI(lifespan=lifespan, exception_handlers=tortoise_exception_handlers())
app.include_router(api_auth_router, prefix="/api/v1")
