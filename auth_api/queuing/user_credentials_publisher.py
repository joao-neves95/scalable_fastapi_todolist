from shared.event_models.user_credentials import UserCredentialsCreated
from shared.lib.constants import (
    TOPIC_USER_CREDENTIALS_CREATED,
)
from shared.lib.rabbitmq_client.rabbitmq_exchange_client import (
    get_rabbit_mq_exchange_client,
)


async def publish_user_credentials_created_async(dto: UserCredentialsCreated):
    rabbit_mq_exchange_client = get_rabbit_mq_exchange_client()

    await rabbit_mq_exchange_client.publish_async(
        topic_name=TOPIC_USER_CREDENTIALS_CREATED, dto=dto
    )
