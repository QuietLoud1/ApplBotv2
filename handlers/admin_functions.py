from aiogram import Router, Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from lexicon.lexicon import LEXICON
from config.config import Config, load_config
from database.database import get_user_role, add_user_role, get_top_mechanics_with_stats
from middlewares.role_checker import RolesMiddleware, require_role
from aiogram import F
from keyboards.reply_menu_keyboards import create_manager_keyboard,create_admin_keyboard,create_mechanic_keyboard
from keyboards.inline_keyboards import pick_restaurant_keyboard, application_writing_complete, admin_panel_menu_keyboard, back_to_statistics_menu_button_keyboard, excel_section_keyboard
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
    
    


