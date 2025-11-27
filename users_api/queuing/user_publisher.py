from shared.event_models.users import UserCreated
from shared.lib.constants import TOPIC_USER_CREATED
from shared.lib.rabbitmq_client.rabbitmq_exchange_client import (
    get_rabbit_mq_exchange_client,
)


async def publish_user_created_async(dto: UserCreated):
    rabbit_mq_exchange_client = get_rabbit_mq_exchange_client()

    await rabbit_mq_exchange_client.publish_async(
        topic_name=TOPIC_USER_CREATED, dto=dto
    )
