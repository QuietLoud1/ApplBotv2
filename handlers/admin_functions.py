from aiogram import Router, Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from lexicon.lexicon import LEXICON
from config.config import Config, load_config
from database.database import get_user_role, add_user_role, get_top_mechanics_with_stats, get_admin_ids
from middlewares.role_checker import RolesMiddleware, require_role
from aiogram import F
from keyboards.reply_menu_keyboards import create_manager_keyboard,create_admin_keyboard,create_mechanic_keyboard
from keyboards.inline_keyboards import pick_restaurant_keyboard, application_writing_complete, admin_panel_menu_keyboard, back_to_statistics_menu_button_keyboard, excel_section_keyboard, users_buttons_picker, create_admins_keyboard_custom,_user_names_cache
import logging
from aiogram.fsm.state import default_state
from aiogram.filters import StateFilter
from states.states import MenuStates
from aiogram.fsm.context import FSMContext
from database.database import restaurants
from middlewares.role_checker import RoleFilter
from aiogram.types import ReplyKeyboardRemove
from aiogram.exceptions import TelegramBadRequest
from database.excel import export_applications_to_excel_and_upload
from aiogram.enums import ChatType
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from keyboards.inline_keyboards import get_user_name

admin_functions = Router()


@admin_functions.message(F.text == LEXICON["admin_panel"], RoleFilter(role="admin"), F.chat.type == ChatType.PRIVATE)
async def admin_panel_button_handler(message: Message, state: FSMContext):
    await message.answer(text=LEXICON["admin_panel_description"], reply_markup=admin_panel_menu_keyboard())
    
    
@admin_functions.callback_query(F.data == "statistics_admin_panel_back_button", RoleFilter(role="admin"))
async def statistics_admin_button_pressed(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(text=LEXICON["admin_panel_description"], reply_markup=admin_panel_menu_keyboard())
    
    
async def get_username_by_id(id: int, bot: Bot) -> str:
    try:
        # Получаем информацию о чате
        chat = await bot.get_chat(id)
        
        # Всегда проверяем на наличие
        if chat.username:
            return chat.username
        else:
            return chat.first_name
        
    except TelegramBadRequest as e:
        # Пользователь не найден или недоступен
        return " "
        
    
@admin_functions.callback_query(F.data == "statistics_admin_button", RoleFilter(role="admin"))
async def statistics_shower(callback: CallbackQuery, state: FSMContext):
    # ЭТО СИНХРОННАЯ ФУНКЦИЯ - УБЕРИТЕ await
    top_mechanics = get_top_mechanics_with_stats()

    # Формируем список задач для получения имен
    result_lines = []
    for i, mech in enumerate(top_mechanics):
        if mech:
            # Асинхронно получаем имя пользователя
            username = await get_username_by_id(id=mech['user_id'], bot=callback.bot)
            result_lines.append(f"{i+1}. Техник: @{username} - {mech['applications_done']} заявок")
        else:
            result_lines.append(f"{i+1}.")
    
    result = "\n".join(result_lines)
    await callback.message.edit_text(text=f"""
*** Здесь могу добавить статистику, которая вас интересует.                                     
Например топ техников :D ***\n                                      
Топ техников за все время: \n                       
{result}""", reply_markup=back_to_statistics_menu_button_keyboard())
   
    
@admin_functions.callback_query(F.data == "back_to_menu_from_admin_panel", RoleFilter(role="admin"))
async def back_admin_button_pressed(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🎨 Админ панель скрыта. Используйте кнопки под клавиатурой, чтобы управлять ботом.")
    
@admin_functions.callback_query(F.data == "excel_menu_button", RoleFilter(role="admin"))
async def excel_section_button_clicked(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Чтобы сформировать эксель файл с текущими заявками нажмите «Сформировать файл Excel»\nЧтобы вернуться назад нажмите «Нажмите»", reply_markup=excel_section_keyboard())
    
@admin_functions.callback_query(F.data == "back_from_excel_section_to_admin_panel", RoleFilter(role="admin"))
async def back_from_excel_section_to_admin_panel(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(text=LEXICON["admin_panel_description"], reply_markup=admin_panel_menu_keyboard())
    
@admin_functions.callback_query(F.data == "hard_update_excel_tables", RoleFilter(role="admin"))
async def back_from_excel_section_to_admin_panel(callback: CallbackQuery, state: FSMContext, bot: Bot):
    # Добавляем индикатор загрузки
    await callback.message.edit_text("Чтобы сформировать эксель файл с текущими заявками нажмите «Сформировать файл Excel»\nЧтобы вернуться назад нажмите «Нажмите»", reply_markup=None)
    await callback.answer("Формирование Excel файла...")
    
    try:
        # Запускаем экспорт
        result = export_applications_to_excel_and_upload()
        
        if result['success']:
            if result['yadisk_url']:
                # Форматируем сообщение с ссылкой
                message_text = (
                    f"✅ Файл Excel успешно сформирован!\n\n"
                    f"📁 Имя файла: {result['local_file']}\n"
                    f"📎 Ссылка на Яндекс.Диск: {result['yadisk_url']}"
                )
            else:
                message_text = (
                    f"✅ Файл Excel успешно сформирован!\n\n"
                    f"📁 Имя файла: {result['local_file']}\n"
                    f"⚠️ Файл не загружен на Яндекс.Диск (проверьте токен)"
                )
            
            # Отправляем сообщение с результатом
            await callback.message.edit_text(
                text=message_text,
                reply_markup=excel_section_keyboard(),
                disable_web_page_preview=True  # Чтобы ссылка не разворачивалась
            )
        else:
            # Обработка ошибки
            await callback.message.edit_text(
                text=f"❌ Ошибка при формировании файла:\n{result['message']}",
                reply_markup=excel_section_keyboard()
            )
            
    except Exception as e:
        await callback.message.edit_text(
            text=f"❌ Неожиданная ошибка: {str(e)}",
            reply_markup=excel_section_keyboard()
        )
    
@admin_functions.callback_query(F.data == "users_admin_button", RoleFilter(role="admin"))
async def users_admin_button_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.edit_text("В этом разделе вы можете управлять участниками бота! \nВыберите нужную категорию участников", reply_markup=users_buttons_picker())

@admin_functions.callback_query(F.data == "pick_mechanics", RoleFilter(role="admin"))
async def pick_mechanic_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.edit_text("Выберите техника, с которым хотите взаимодействовать", reply_markup=await create_admins_keyboard_custom(role="mechanic", bot=bot))

@admin_functions.callback_query(F.data.contains("mechanic_select_"), RoleFilter(role="admin"))
async def mechanic_picked(callback: CallbackQuery, state: FSMContext, bot: Bot):
    mechanic_id = int(callback.data.split("_")[2])
    
    # Получаем имя админа (можем использовать кэшированное значение)
    if _user_names_cache.get(mechanic_id):
        mechanic_name = _user_names_cache.get(mechanic_id, f"Техник {mechanic_id}")
    else:
        mechanic_name_temp = await get_user_name(user_id=mechanic_id, bot=bot)
        mechanic_name = f"Админ {mechanic_name_temp}"
    
    # Здесь можно добавить дополнительную логику
    
    # Обновляем сообщение
    await callback.message.edit_text(
        f"✅ Вы выбрали администратора: {mechanic_name}\n\nЧто вы хотите сделать?",
        reply_markup=create_actions_keyboard(id=mechanic_id)  # Дополнительная функция
    )

@admin_functions.callback_query(F.data == "pick_managers", RoleFilter(role="admin"))
async def pick_manager_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.edit_text("Выберите менеджера, с которым хотите взаимодействовать", reply_markup=await create_admins_keyboard_custom(role="manager", bot=bot))

@admin_functions.callback_query(F.data.contains("manager_select_"), RoleFilter(role="admin"))
async def manager_picked(callback: CallbackQuery, state: FSMContext, bot: Bot):
    manager_id = int(callback.data.split("_")[2])
    
    # Получаем имя админа (можем использовать кэшированное значение)
    if _user_names_cache.get(manager_id):
        manager_name = _user_names_cache.get(manager_id, f"Менеджер {manager_id}")
    else:
        manager_name_temp = await get_user_name(user_id=manager_id, bot=bot)
        manager_name = f"Админ {manager_name_temp}"
    
    # Здесь можно добавить дополнительную логику
    
    # Обновляем сообщение
    await callback.message.edit_text(
        f"✅ Вы выбрали администратора: {manager_name}\n\nЧто вы хотите сделать?",
        reply_markup=create_actions_keyboard(id=manager_id)  # Дополнительная функция
    )

@admin_functions.callback_query(F.data == "pick_banned", RoleFilter(role="admin"))
async def pick_banned_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.edit_text("Выберите забаненного пользователя, с которым хотите взаимодействовать", reply_markup=await create_admins_keyboard_custom(role="banned", bot=bot))

@admin_functions.callback_query(F.data.contains("banned_select_"), RoleFilter(role="admin"))
async def banned_picked(callback: CallbackQuery, state: FSMContext, bot: Bot):
    banned_id = int(callback.data.split("_")[2])
    
    # Получаем имя админа (можем использовать кэшированное значение)
    if _user_names_cache.get(banned_id):
        banned_name = _user_names_cache.get(banned_id, f"Заблокированный пользователь {banned_id}")
    else:
        banned_name_temp = await get_user_name(user_id=banned_id, bot=bot)
        banned_name = f"Заблокированный пользователь {banned_name_temp}"
    
    # Здесь можно добавить дополнительную логику
    
    # Обновляем сообщение
    await callback.message.edit_text(
        f"✅ Вы выбрали заблокированного пользователя: {banned_name}\n\nЧто вы хотите сделать?",
        reply_markup=create_unbanning_keyboard(id=banned_id)  # Дополнительная функция
    )
    


@admin_functions.callback_query(F.data == "pick_admins", RoleFilter(role="admin"))
async def pick_admin_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.edit_text("Выберите админа, с которым хотите взаимодействовать", reply_markup=await create_admins_keyboard_custom(role="admin", bot=bot))

@admin_functions.callback_query(F.data.contains("admin_select_"), RoleFilter(role="admin"))
async def admin_picked(callback: CallbackQuery, state: FSMContext, bot: Bot):
    admin_id = int(callback.data.split("_")[2])
    
    # Получаем имя админа (можем использовать кэшированное значение)
    if _user_names_cache.get(admin_id):
        admin_name = _user_names_cache.get(admin_id, f"Админ {admin_id}")
    else:
        admin_name_temp = await get_user_name(user_id=admin_id, bot=bot)
        admin_name = f"Админ {admin_name_temp}"
    
    # Здесь можно добавить дополнительную логику
    
    # Обновляем сообщение
    await callback.message.edit_text(
        f"✅ Вы выбрали администратора: {admin_name}\n\nЧто вы хотите сделать?",
        reply_markup=create_actions_keyboard(id=admin_id)  # Дополнительная функция
    )
    
def create_actions_keyboard(id: int):
    actions_kb_builder = InlineKeyboardBuilder()
    
    actions_kb_builder.row(
        InlineKeyboardButton(text="Забанить в боте", callback_data=f"ban_picked_user_{id}"),
        InlineKeyboardButton(text="❌ Назад", callback_data=f"users_admin_button"),
        
    )

    return actions_kb_builder.as_markup()

def create_unbanning_keyboard(id: int):
    actions_kb_builder = InlineKeyboardBuilder()
    
    actions_kb_builder.row(
        InlineKeyboardButton(text="Разбанить в боте", callback_data=f"unblock_picked_user_{id}"),
        InlineKeyboardButton(text="❌ Назад", callback_data=f"users_admin_button"),
        
    )

    return actions_kb_builder.as_markup()


@admin_functions.callback_query(F.data.contains("ban_picked_user_"), RoleFilter(role="admin") )
async def ban_user_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = int(callback.data.split("_")[3])
    add_user_role(user_id=user_id, role="banned")
    await callback.message.edit_text("Вы успешно забанили пользователя!")
    await callback.bot.send_message(chat_id=user_id, text="😭 Вы были заблокированы в боте! Все ваши запросы в боте будут проигрорированы.\n\nЕсли есть вопросы обратитесь к администратору.")
    
@admin_functions.callback_query(F.data.contains("unblock_picked_user_"), RoleFilter(role="admin") )
async def unban_user_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    user_id = int(callback.data.split("_")[3])
    add_user_role(user_id=user_id, role="default")
    await callback.message.edit_text("Вы успешно разблокировали пользователя!")
    await callback.bot.send_message(chat_id=user_id, text="🎉 Вы были разблокированы в боте. Пройдем регистрацию еще раз. \nОтправьте текстом пароль от администратора")
    
@admin_functions.callback_query(F.data.contains("close_menu_with_users"), RoleFilter(role="admin") )
async def unban_user_handler(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.edit_text("В этом разделе вы можете управлять участниками бота! \nВыберите нужную категорию участников", reply_markup=users_buttons_picker())