from redis.asyncio import Redis

from shared.lib.constants import ONE_DAY_IN_SECONDS
from shared.models.auth_dtos import UserCredentials


async def get_cached_user_credentials_async(redis_client: Redis, user_ulid: str):
    return await redis_client.get(f"user_credentials:{user_ulid}")


async def set_cached_user_credentials_async(
    redis_client: Redis, user_ulid: str, user_credentials: UserCredentials
):
    await redis_client.set(
        f"user_credentials:{user_ulid}",
        user_credentials.model_dump_json(),
        ex=ONE_DAY_IN_SECONDS,
    )
