import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config.config import Config, load_config
from database.database import init_db
from handlers.notifications import notifications
from handlers.main_menu import main_menu
from handlers.application_writing import application_writing
from handlers.applications_view import applications_view
from middlewares.role_checker import RolesMiddleware
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
import database.database as db
from apscheduler.triggers.cron import CronTrigger
import pytz
from handlers.admin_functions import admin_functions
from aiogram.client.session.aiohttp import AiohttpSession
from aiohttp import BasicAuth
logger = logging.getLogger(__name__)

async def on_startup():
    database: dict = init_db()
    pass

async def main():
    config: Config = load_config()

    logging.basicConfig(
        level=logging.getLevelName(level=config.log.level),
        format=config.log.format,
    )

    logger.info("Starting bot")

    proxy_url = config.bot.proxy_url
    if proxy_url:
        # Создаём auth только если есть прокси
        auth = BasicAuth(login=config.bot.proxy_login, password=config.bot.proxy_password)
        session = AiohttpSession(proxy=(proxy_url, auth))
        logger.info(f"Using proxy: {proxy_url}")
    else:
        session = AiohttpSession()
        logger.info("No proxy configured")

    bot = Bot(
        token=config.bot.token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        session=session
    )
    
    # Redis - можно тоже вынести в config, но оставим localhost для примера
    redis = Redis(host='localhost')
    storage = RedisStorage(redis=redis)
    dp = Dispatcher(storage=storage)

    dp.startup.register(on_startup)

    dp.include_router(main_menu)
    dp.include_router(notifications)
    dp.include_router(admin_functions)
    dp.include_router(application_writing)
    dp.include_router(applications_view)

    await dp.start_polling(bot)
    

if __name__ == "__main__":
    asyncio.run(main())
    
