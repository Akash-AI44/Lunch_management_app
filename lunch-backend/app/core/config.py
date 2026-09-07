import os

from dotenv import load_dotenv


load_dotenv()


class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", ""))

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "")

    ALLOWED_EMAIL_DOMAIN: str = os.getenv(
        "ALLOWED_EMAIL_DOMAIN", "")

    TIMEZONE: str = os.getenv("TIMEZONE", "")
    CUTOFF_HOUR: int = int(os.getenv("CUTOFF_HOUR", ""))
    CUTOFF_MINUTE: int = int(os.getenv("CUTOFF_MINUTE", ""))

    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")

    MEDIA_ROOT: str = os.getenv("MEDIA_ROOT", "")

    SEED_ADMIN_NAME: str = os.getenv("SEED_ADMIN_NAME", "")
    SEED_ADMIN_EMAIL: str = os.getenv("SEED_ADMIN_EMAIL", "")
    SEED_ADMIN_PASSWORD: str = os.getenv("SEED_ADMIN_PASSWORD", "")


settings = Settings()
