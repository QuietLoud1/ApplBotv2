from aiogram import Router, types
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from lexicon.lexicon import LEXICON
from config.config import Config, load_config
from database.database import add_user_role, get_user_role
from middlewares.role_checker import RolesMiddleware, require_role
from aiogram import F
from keyboards.reply_menu_keyboards import create_manager_keyboard,create_admin_keyboard,create_mechanic_keyboard
from keyboards.inline_keyboards import pick_restaurant_keyboard, application_writing_complete
import logging
from aiogram.fsm.state import default_state
from aiogram.filters import StateFilter
from states.states import MenuStates
from aiogram.fsm.context import FSMContext
from database.database import restaurants
from aiogram.enums import ChatType
from middlewares.role_checker import RoleFilter

notifications = Router()

@notifications.message(F.text.contains("Выбрать мои рестораны"), StateFilter(MenuStates.main_menu), F.chat.type == ChatType.PRIVATE)
@require_role("mechanic")
async def choose_restaurants_button_mechanic(message: Message):
    await message.answer("Функция в разработке. Пока что вам доступны уведомления из всех ресторанов сети. \n\nНо вы сами можете выбрать за какую заявку беретесь")