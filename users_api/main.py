from dotenv import load_dotenv
from fastapi import FastAPI
from tortoise.contrib.fastapi import tortoise_exception_handlers

from shared.lib.constants import APP_NAME_USERS_API, EXCHANGE_USERS
from shared.lib.fastapi_utils import app_add_cors, app_lifespan
from shared.lib.rabbitmq_client.rabbitmq_exchange_client import (
    get_rabbit_mq_exchange_client,
)
from shared.queue_consumers.user_credentials_consumers import (
    consume_user_credentials_created_async,
)
from users_api.queuing.user_credentials_handlers import (
    handle_user_credentials_created_async,
)
from users_api.routers.auth_proxy import api_auth_router
from users_api.routers.users import api_users_router


async def app_on_init_async(_: FastAPI):
    rabbit_mq_exchange_client = get_rabbit_mq_exchange_client()
    await rabbit_mq_exchange_client.declare_exchange_async(EXCHANGE_USERS)

    await consume_user_credentials_created_async(
        app_name=APP_NAME_USERS_API, async_handler=handle_user_credentials_created_async
    )


load_dotenv()


app = FastAPI(
    lifespan=app_lifespan(
        app_folder=APP_NAME_USERS_API,
        modules={
            "entities": [
                f"{APP_NAME_USERS_API}.data.entities.data_user",
            ]
        },
        use_redis=True,
        use_rabbit_mq=True,
        additional_app_on_init_async=app_on_init_async,
    ),
    exception_handlers=tortoise_exception_handlers(),
)
app_add_cors(app)
app.include_router(api_users_router, prefix="/api/v1")
app.include_router(api_auth_router, prefix="/api/v1")
