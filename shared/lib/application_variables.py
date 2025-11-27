from os import getenv

from shared.lib.constants import DEFAULT_JWT_EXPIRE_MINUTES


class ApplicationVariables:
    @staticmethod
    def JWT_ALGORITHM():
        return getenv("JWT_ALGORITHM")

    @staticmethod
    def JWT_EXPIRE_MINUTES() -> float:
        return float(getenv("JWT_EXPIRE_MINUTES") or DEFAULT_JWT_EXPIRE_MINUTES)

    @staticmethod
    def AUTH_API_PRIVATE_URL():
        return getenv("AUTH_API_PRIVATE_URL")

    @staticmethod
    def USERS_API_PRIVATE_URL():
        return getenv("USERS_API_PRIVATE_URL")

    @staticmethod
    def INTERNAL_API_KEY():
        return getenv("INTERNAL_API_KEY")

    @staticmethod
    def JWT_SECRET_KEY():
        return getenv("JWT_SECRET_KEY")

    @staticmethod
    def REDIS_HOST() -> str | None:
        return getenv("REDIS_HOST")

    @staticmethod
    def RABBIT_MQ_URL() -> str | None:
        return getenv("RABBIT_MQ_URL")
