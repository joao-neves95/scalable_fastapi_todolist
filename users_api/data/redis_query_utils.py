from redis.asyncio import Redis

from shared.lib.constants import ONE_DAY_IN_SECONDS
from shared.models.user_dto import User


async def get_cached_user_async(redis_client: Redis, user_ulid: str) -> User | None:
    cached_user = await redis_client.get(f"user:{user_ulid}")

    if not cached_user:
        return None

    return User.model_validate_json(cached_user)


async def set_cached_user_async(redis_client: Redis, user_ulid: str, user: User):
    await redis_client.set(
        f"user:{user_ulid}",
        user.model_dump_json(),
        ex=ONE_DAY_IN_SECONDS,
    )


async def delete_cached_user_async(redis_client: Redis, user_ulid: str):
    return await redis_client.delete(f"user:{user_ulid}")
