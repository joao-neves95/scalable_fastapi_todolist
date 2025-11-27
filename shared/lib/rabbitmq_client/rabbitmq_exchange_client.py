import aio_pika
from pydantic import BaseModel


class RabbitMqExchangeClient:
    def __init__(self):
        self.connection: aio_pika.abc.AbstractRobustConnection | None = None
        self.channel: aio_pika.abc.AbstractChannel | None = None
        self.exchange: aio_pika.abc.AbstractExchange | None = None

    async def connect_async(self, url: str):
        self.connection = await aio_pika.connect_robust(
            url,
            heartbeat=60,
        )

        self.channel = await self.connection.channel()

    async def close_async(self):
        if self.channel and not self.channel.is_closed:
            await self.channel.close()
        if self.connection and not self.connection.is_closed:
            await self.connection.close()

    async def declare_exchange_async(self, exchange_name: str):
        if not self.channel:
            raise RuntimeError("RabbitMqExchangeClient.connection not initialized")

        self.exchange = await self.channel.declare_exchange(
            exchange_name, aio_pika.ExchangeType.TOPIC
        )

    async def publish_async(self, topic_name: str, dto: BaseModel):
        if not self.exchange:
            raise RuntimeError("RabbitMqExchangeClient.exchange not initialized")

        message = aio_pika.Message(body=dto.model_dump_json().encode())
        await self.exchange.publish(message, routing_key=topic_name)


_rabbit_mq_exchange_client: RabbitMqExchangeClient | None = None


def init_rabbit_mq_exchange_client():
    global _rabbit_mq_exchange_client
    if _rabbit_mq_exchange_client is None:
        _rabbit_mq_exchange_client = RabbitMqExchangeClient()

    return _rabbit_mq_exchange_client


def get_rabbit_mq_exchange_client() -> RabbitMqExchangeClient:
    if _rabbit_mq_exchange_client is None:
        raise RuntimeError("RabbitMQ not initialized")

    return _rabbit_mq_exchange_client


async def close_rabbit_mq_exchange_client_async():
    global _rabbit_mq_exchange_client
    if _rabbit_mq_exchange_client:
        await _rabbit_mq_exchange_client.close_async()
        _rabbit_mq_exchange_client = None
