from auth_api.data.entities.data_user_credentials import DataUserCredentials


async def select_user_credentials_by_user_ulid_async(
    ulid: str,
) -> DataUserCredentials | None:
    try:
        return await DataUserCredentials.filter(user_ulid=ulid).first()
    except Exception:
        return None


async def select_user_credentials_by_email_async(
    email: str,
) -> DataUserCredentials | None:
    try:
        return await DataUserCredentials.filter(email=email).first()
    except Exception:
        return None
