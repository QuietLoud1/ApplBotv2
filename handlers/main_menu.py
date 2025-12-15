from aiogram import Router, Bot, types
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from lexicon.lexicon import LEXICON
from config.config import Config, load_config
from database.database import get_user_role, add_user_role, set_default_role_by_id, update_user_info
from middlewares.role_checker import RolesMiddleware, require_role
from aiogram import F
from keyboards.reply_menu_keyboards import create_manager_keyboard,create_admin_keyboard,create_mechanic_keyboard
from keyboards.inline_keyboards import pick_restaurant_keyboard, application_writing_complete, topic_message_keyboard
import logging
from aiogram.fsm.state import default_state
from aiogram.filters import StateFilter
from states.states import MenuStates
from aiogram.fsm.context import FSMContext
from database.database import restaurants
from middlewares.role_checker import RoleFilter
from aiogram.types import ReplyKeyboardRemove
from aiogram.enums import ChatType

logger = logging.getLogger(__name__)
main_menu = Router()
main_menu.message.middleware(RolesMiddleware())
main_menu.callback_query.middleware(RolesMiddleware())

config : Config = load_config()

@main_menu.message(F.text == "/get_id", F.chat.type == ChatType.SUPERGROUP, ~RoleFilter(role="banned"))
async def get_id_command_handler(message: Message, bot: Bot):
    chat_id = message.chat.id
    thread_id = message.message_thread_id
    await message.answer(text=f"Chat_id - {chat_id}")
    await message.answer(text=f"Chat_id - {thread_id}")
    
@main_menu.message(F.text == "/starter_topic_message", F.chat.type == ChatType.SUPERGROUP, ~RoleFilter(role="banned"))
async def get_id_command_handler(message: Message, bot: Bot):
    await message.answer(text="Теперь для того, чтобы сообщить о неисправности, нужно воспользоваться специальным ботом! \nПароль для входа можно взять у администратора.", reply_markup=topic_message_keyboard())
    
    
    
@main_menu.message(CommandStart(), RoleFilter(["admin", "manager", "mechanic"]), F.chat.type == ChatType.PRIVATE, ~RoleFilter(role="banned"))
async def start_command_handler(message: Message, state: FSMContext):
    user_role = get_user_role(message.from_user.id)
    user = message.from_user
    if user_role == "admin":
        await message.answer(text=LEXICON["login_start_authorized"], reply_markup=create_admin_keyboard())
        await state.set_state(MenuStates.main_menu)
        user = message.from_user
        update_user_info(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    elif user_role == "manager":
        await message.answer(text=LEXICON["login_start_authorized"], reply_markup=create_manager_keyboard())
        await state.set_state(MenuStates.main_menu)
        user = message.from_user
        update_user_info(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    elif user_role == "mechanic":
        await message.answer(text=LEXICON["login_start_authorized"], reply_markup=create_mechanic_keyboard())
        await state.set_state(MenuStates.main_menu)
        user = message.from_user
        update_user_info(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    
    await state.set_data({})
    
    
@main_menu.message(CommandStart(), RoleFilter(role="default"), F.chat.type == ChatType.PRIVATE)
async def start_command_handler(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    await message.answer(text=LEXICON["login_start_unauthorized"])
    
@main_menu.message(F.text == "🚪 Выйти из системы", RoleFilter(role=["admin", "manager", "mechanic"]), F.chat.type == ChatType.PRIVATE, ~RoleFilter(role="banned"))
async def reauthorize(message: Message, state: FSMContext):
    user_id = message.from_user.id
    set_default_role_by_id(user_id)
    await state.clear()
    await message.answer(text="Вы успешно вышли из системы. Авторизуйтесь снова!", reply_markup=ReplyKeyboardRemove())
    await message.answer(text=LEXICON["login_start_unauthorized"])
    
    
@main_menu.message(F.text, StateFilter(default_state), RoleFilter(role="default"), F.chat.type == ChatType.PRIVATE)
async def login_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    
    if message.text == config.bot.admin_password:
        # Добавление роли админ человеку в бд
        add_user_role(user_id, "admin")
        logger.info(f"Сохраняем role=admin для user_id={user_id} (type={type(user_id)})")
        await message.answer(LEXICON["admin_login"], reply_markup=create_admin_keyboard())
        await state.set_state(MenuStates.main_menu)
    elif message.text == config.bot.manager_password:
        # Добавление роли менеджер человеку в бд
        add_user_role(user_id, "manager")
        await message.answer(LEXICON["manager_login"], reply_markup=create_manager_keyboard())
        await state.set_state(MenuStates.main_menu)
    elif message.text == config.bot.mechanic_password:
        # Добавление роли техник человеку в бд
        add_user_role(user_id, "mechanic")
        await message.answer(LEXICON["mechanic_login"], reply_markup=create_mechanic_keyboard())
        await state.set_state(MenuStates.main_menu)
    else:
        await message.answer(LEXICON["incorrect_password"])
    user = message.from_user
    update_user_info(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
        
@main_menu.message(Command("role"), F.chat.type == ChatType.PRIVATE, ~RoleFilter(role="banned"))
async def role_viewer(message: Message):
    user_role = get_user_role(message.from_user.id)
    await message.answer(f"Ваша роль: {user_role}")

@main_menu.message(~F.text, StateFilter(default_state), RoleFilter(role="default"), F.chat.type == ChatType.PRIVATE, ~RoleFilter(role="banned"))
async def login_handler(message: Message):
    await message.answer(LEXICON["incorrect_content_type"])

    

        