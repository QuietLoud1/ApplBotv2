from dataclasses import dataclass
import logging
from environs import Env
import os

logger = logging.getLogger(__name__)

DEFAULT_RESTAURANTS = (
    "ДУО",
    "ТАРТАР",
    "АЗИЯ",
    "ХАРВЕСТ",
    "РЕБОРН",
    "ФРАНЦУЗ",
    "ОДЖИ",
    "ПЕРЕМЕНА",
    "ЛАВРАКИ",
    "БАМБИНО",
)


@dataclass
class BotSettings:
    token: str
    admin_password: str
    manager_password: str
    mechanic_password: str
    yadisk_token: str
    yadisk_folder_name: str
    database_path_for_excel: str
    proxy_url: str 
    proxy_login: str
    proxy_password: str


@dataclass
class DatabaseSettings:
    name: str
    host: str
    port: int
    user: str
    password: str


@dataclass
class RedisSettings:
    host: str
    port: int
    db: int
    password: str
    username: str


@dataclass
class LoggSettings:
    level: str
    format: str


@dataclass
class Config:
    bot: BotSettings
    db: DatabaseSettings
    redis: RedisSettings
    log: LoggSettings
    restaurants: list[str]
    google_script_url: str


def load_config(path: str | None = None) -> Config:
    env = Env()

    if path:
        if not os.path.exists(path):
            logger.warning(".env file not found at '%s', skipping...", path)
        else:
            logger.info("Loading .env from '%s'", path)

    env.read_env(path)

    restaurants = [
        restaurant.strip()
        for restaurant in env.list("RESTAURANTS", default=list(DEFAULT_RESTAURANTS))
    ]
    if not restaurants or any(not restaurant for restaurant in restaurants):
        raise ValueError("RESTAURANTS must contain at least one non-empty name")

    google_script_url = env("GOOGLE_SCRIPT_URL").strip()
    if not google_script_url:
        raise ValueError("GOOGLE_SCRIPT_URL must not be empty")

    token = env("BOT_TOKEN")

    if not token:
        raise ValueError("BOT_TOKEN must not be empty")

    raw_ids = env.list("ADMIN_IDS", default=[])

    try:
        admin_ids = [int(x) for x in raw_ids]
    except ValueError as e:
        raise ValueError(f"ADMIN_IDS must be integers, got: {raw_ids}") from e
    
    db = DatabaseSettings(
        name=env("POSTGRES_DB"),
        host=env("POSTGRES_HOST"),
        port=env.int("POSTGRES_PORT"),
        user=env("POSTGRES_USER"),
        password=env("POSTGRES_PASSWORD"),
    )

    redis = RedisSettings(
        host=env("REDIS_HOST"),
        port=env.int("REDIS_PORT"),
        db=env.int("REDIS_DATABASE"),
        password=env("REDIS_PASSWORD", default=""),
        username=env("REDIS_USERNAME", default=""),
    )

    logg_settings = LoggSettings(
        level=env("LOG_LEVEL"),
        format=env("LOG_FORMAT")
    )

    logger.info("Configuration loaded successfully")

    return Config(
        bot=BotSettings(
            token=token,
            admin_password=env("ADMIN_PASSWORD"), 
            manager_password=env("MANAGER_PASSWORD"), 
            mechanic_password=env("MECHANIC_PASSWORD"), 
            yadisk_token=env("YADISK_TOKEN"), 
            yadisk_folder_name=env("YADISK_FOLDER_NAME"), 
            database_path_for_excel=env("DATABASE_PATH_FOR_EXCEL"),
            proxy_url=env("PROXY_URL", default=""),           # <-- добавить default
            proxy_password=env("PROXY_PASSWORD", default=""), # <-- добавить default
            proxy_login=env("PROXY_LOGIN", default="")        # <-- добавить default
        ),
        db=db,
        redis=redis,
        log=logg_settings,
        restaurants=restaurants,
        google_script_url=google_script_url,
)