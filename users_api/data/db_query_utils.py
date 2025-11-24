from users_api.data.entities.data_user import DataUser


async def select_user_by_ulid_async(ulid: str) -> DataUser | None:
    try:
        return await DataUser.filter(ulid=ulid).first()
    except Exception:
        return None
