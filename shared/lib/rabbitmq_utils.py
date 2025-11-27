import asyncio
from typing import Awaitable, Callable, Type, TypeVar

import aio_pika
from pydantic import BaseModel

from shared.lib.application_variables import ApplicationVariables

TMessage = TypeVar("TMessage", bound=BaseModel)
AsyncHandler = Callable[[TMessage], Awaitable[None]]


async def consume_topic_async(
    exchange_name: str,
    topic_name: str,
    queue_name: str,
    model_type: Type[TMessage],
    async_handler: AsyncHandler,
):
    """
    Creates a queue and binds it to an exchange, and starts listening on a new asyncio Task.

    Example Usage: `consume_topic_async(exchange_name, topic_name, queue_name, ModelType, async_handler)`

    Args:
        exchange_name (str)
        topic_name (str)
        queue_name (str)
        model_type (Type[TMessage])
        async_handler (Callable[[TMessage], Awaitable[None]])
    """
    asyncio.create_task(
        _consume_async(exchange_name, topic_name, queue_name, model_type, async_handler)
    )


async def _consume_async(
    exchange_name: str,
    topic_name: str,
    queue_name: str,
    model_type: Type[TMessage],
    async_handler: AsyncHandler,
):
    while True: # retry
        try:
            connection = await aio_pika.connect_robust(
                ApplicationVariables.RABBIT_MQ_URL()
            )

            async with connection:
                channel = await connection.channel()
                queue = await channel.declare_queue(queue_name, durable=True)
                await queue.bind(exchange_name, routing_key=topic_name)

                async with queue.iterator() as queue_iter:
                    async for message in queue_iter:
                        async with message.process():
                            await async_handler(
                                model_type.model_validate_json(message.body)
                            )
        except (
            aio_pika.exceptions.AMQPConnectionError,
            aio_pika.exceptions.AMQPChannelError,
            ConnectionResetError,
        ) as e:
            print(f"RabbitMQ disconnected ({e}), reconnecting in 5s...")
            await asyncio.sleep(5)
        except Exception as e:
            print(f"Unexpected error in listener: {e}")
            await asyncio.sleep(5)
