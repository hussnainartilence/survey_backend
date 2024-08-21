"""Default configuration settings"""

import os
from datetime import timedelta
from pathlib import Path
from typing import Any, Sequence

from dotenv import load_dotenv
from pydantic import BaseSettings, Field
from sqlalchemy import URL

# pylint: disable = too-few-public-methods, unsupported-binary-operation

# load environment variables from .env
load_dotenv()

# general
BASE_DIR = Path(__file__).resolve(strict=True).parent
# load docker environment variables from docker.env

SERVICE_CODE = "microservice-auth"
SERVICE_NAME = "Auth Service"
SERVICE_VERSION = "0.1"
SERVICE_API_VERSION = "0.1"
GZIP_MIN_SIZE = 102400  # minimum size in bytes to return gzip payoad

# security settings
SECRET_KEY = os.getenv("SECRET_KEY", "")
SYSTEM_API_KEY = os.getenv("SYSTEM_API_KEY", "")
HASH_ALGORITHM = "HS256"
JWT_EXPIRATION_DELTA = timedelta(3600)
REFRESH_TOKEN_EXPIRATION_DELTA = timedelta(days=1)
PASSWORD_MAX_LOGIN_ATTEMPTS = 10
SHOW_API_DOCS = os.getenv("SHOW_API_DOCS", "False").lower() in (
    "true",
    "1",
    "t",
)

EMAIL_FROM = os.getenv("EMAIL_FROM", "")
EMAIL_PASS = os.getenv("EMAIL_PASS", "")


DEFAULT_SA_ENGINE_OPTIONS = {"future": True, "pool_pre_ping": True}

DBSettingsT = BaseSettings | dict[str, Any]


def get_uri(schema: str, db_settings: DBSettingsT) -> str | URL:
    return db_settings.uri or URL.create(
        drivername=schema,
        username=db_settings.user,
        password=db_settings.pass_,
        host=db_settings.host,
        port=db_settings.port,
        database=db_settings.name,
    )


class LeaderDBSettings(BaseSettings):
    host: str | None = None
    port: int = 5432
    name: str | None = None
    pass_: str = Field(default=None, env="LEADER_DB_PASS")
    user: str | None = None
    uri: str | None = None
    cli_uri: str | None = None
    engine_options: dict = DEFAULT_SA_ENGINE_OPTIONS

    class Config:
        env_prefix = "LEADER_DB_"


class FollowerDBSettings(BaseSettings):
    host: str | None = None
    port: int = 5432
    name: str | None = None
    pass_: str = Field(default=None, env="FOLLOWER_DB_PASS")
    user: str | None = None
    uri: str | None = None
    cli_uri: str | None = None
    engine_options: dict = DEFAULT_SA_ENGINE_OPTIONS

    class Config:
        env_prefix = "FOLLOWER_DB_"


class DBSettings(BaseSettings):
    """
    Database settings.
    """

    leader: LeaderDBSettings = LeaderDBSettings()
    follower: FollowerDBSettings = FollowerDBSettings()
    name_test: str = "test_db"


db_settings = DBSettings()  # type: ignore
# If the envvar `DB_URI` is defined, override the pieces above. We expect this to be the
# fully formed appropriate URI with driver.
LIVE_DATABASE_LEADER_URI = get_uri("postgresql+asyncpg", db_settings.leader)
LIVE_DATABASE_FOLLOWER_URI = get_uri("postgresql+asyncpg", db_settings.follower)
CLI_DATABASE_LEADER_URI = get_uri("postgresql", db_settings.leader)
TEST_DATABASE_PATH = f"{BASE_DIR}/../tmp/{db_settings.name_test}.db"
TEST_DATABASE_URI = f"sqlite+aiosqlite:///{TEST_DATABASE_PATH}"


class CORSSettings(BaseSettings):
    """Allows control of the CORS middleware, mostly for the FE folk"""

    allow_origins: Sequence[str] = ["*"]
    allow_methods: Sequence[str] = ["*"]
    allow_headers: Sequence[str] = ["*"]
    allow_credentials: bool = False
    allow_origin_regex: str | None = None
    expose_headers: Sequence[str] = ()
    max_age: int = 600
