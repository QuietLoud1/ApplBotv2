from time import time
from aiogram import Router, types, Bot
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from lexicon.lexicon import LEXICON
from config.config import Config, load_config
from database.database import detach_application, add_user_role, set_default_role_by_id, accept_application, is_application_available, get_mechanic_applications
from middlewares.role_checker import RolesMiddleware, require_role
from aiogram import F
from keyboards.reply_menu_keyboards import create_manager_keyboard,create_admin_keyboard,create_mechanic_keyboard
from keyboards.inline_keyboards import pick_restaurant_keyboard, application_writing_complete, get_user_name
import logging
from aiogram.fsm.state import default_state
from aiogram.filters import StateFilter
from states.states import MenuStates, pagination_manager
from aiogram.fsm.context import FSMContext
from database.database import (
    get_applications_in_work,
    get_all_pending_applications,
    complete_application,
    delete_application,
    update_application_mechanic,
    get_user_role,
    update_user_info,
    dict_of_topics,
    get_restaurant_by_id,
    get_user_created_and_description_by_id
)
from middlewares.role_checker import RoleFilter
from aiogram.types import ReplyKeyboardRemove
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from typing import List, Dict, Optional
from aiogram import types
from aiogram.exceptions import TelegramBadRequest
from aiogram.enums import ChatType
applications_view = Router()

@applications_view.callback_query(F.data.startswith("picking_application_") | F.data.startswith("skip_pending_application_"), RoleFilter(role=["mechanic", "admin"]))
async def handle_application_response(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if callback.data.startswith("picking_application_"):
        await callback.answer()
        await callback.message.edit_reply_markup(reply_markup=None)
        application_id = int(callback.data.split("_")[-1])
        
        if not is_application_available(application_id):
            await callback.message.answer(text=LEXICON["mechanic_application_unavailable"])
            return
        user_id = callback.from_user.id
        accept_application(application_id=application_id, mechanic_id=user_id)
        dict_for_notification = get_user_created_and_description_by_id(application_id=application_id)
        text = dict_for_notification['description']
        cropped_text = text[:15] + "..."
        mechanic_id = dict_for_notification['mechanic_id']
        user_accepted = await get_user_name(bot=bot,user_id=mechanic_id)
        await callback.bot.send_message(chat_id=dict_for_notification['user_created_id'], text=f"""
                                  ❗ Ваша заявка с текстом: {cropped_text}\n\n<b>Была принята в работу 👨🏼‍🔧{user_accepted}</b>
                                  """)
        await callback.message.answer(text=LEXICON["mechanic_picked_application"])        
    elif callback.data.startswith("skip_pending_application_"):
        await callback.message.delete()
        await callback.message.answer(text=LEXICON["mechanic_skipped_application"])

async def get_username(bot, user_id: str) -> str:
    """Получить имя пользователя по ID"""
    try:
        # Преобразуем user_id в int
        user_id_int = int(user_id)
        chat = await bot.get_chat(user_id_int)
        if chat.first_name or chat.last_name:
            return f"{chat.first_name or ''} {chat.last_name or ''}".strip()
        elif chat.username:
            return f"@{chat.username}"
        else:
            return f"ID: {user_id}"
    except ValueError:
        return f"ID: {user_id}"
    except Exception as e:
        logging.error(f"Ошибка получения имени пользователя {user_id}: {e}")
        return f"ID: {user_id}"

def create_pagination_keyboard(
    current_index: int, 
    total_count: int, 
    application_id: int,
    app_type: str
) -> InlineKeyboardMarkup:
    """Создать клавиатуру пагинации"""
    keyboard = []
    
    # Кнопки навигации
    nav_buttons = []
    
    if current_index > 0:
        nav_buttons.append(
            InlineKeyboardButton(text="◀ Предыдущая", callback_data=f"prev_{app_type}")
        )
    
    # Неактивная кнопка с номером
    nav_buttons.append(
        InlineKeyboardButton(
            text=f"{current_index + 1}/{total_count}", 
            callback_data="page_info"
        )
    )
    
    if current_index < total_count - 1:
        nav_buttons.append(
            InlineKeyboardButton(text="Следующая ▶", callback_data=f"next_{app_type}")
        )
    
    keyboard.append(nav_buttons)
    
    # Кнопки действий
    if app_type == 'in_work':
        action_buttons = [
            InlineKeyboardButton(
                text="✔ Заявка выполнена", 
                callback_data=f"complete_{application_id}"
            ),
            InlineKeyboardButton(
                text="❌ Удалить заявку", 
                callback_data=f"delete_{application_id}"
            )
        ]
    else:  # pending
        action_buttons = [
            InlineKeyboardButton(
                text="✔ Принять заявку", 
                callback_data=f"accept_{application_id}"
            )
        ]
    
    keyboard.append(action_buttons)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def show_application(
    bot, 
    user_id: int, 
    chat_id: int, 
    message_id: Optional[int] = None,
    edit: bool = False
):
    """Показать заявку пользователю"""
    state = pagination_manager.get_state(user_id)
    
    if not state or not state.applications:
        if state and state.application_type == 'in_work':
            text = "Все заявки в работе выполнены. Больше нет активных заявок."
        elif state and state.application_type == 'pending':
            text = "Непринятых заявок больше нет. Нажмите на кнопку 🍭 Заявки в работе, чтобы увидеть текущие заявки в работе."
        else:
            text = "Нет заявок для отображения."
        
        if edit and message_id:
            try:
                await bot.edit_message_text(
                    text=text,
                    chat_id=chat_id,
                    message_id=message_id
                )
            except Exception as e:
                # Если не удалось отредактировать (например, было фото), удаляем и отправляем новое
                try:
                    await bot.delete_message(chat_id, message_id)
                except:
                    pass
                await bot.send_message(chat_id, text)
        else:
            await bot.send_message(chat_id, text)
        return
    
    app = state.applications[state.current_index]
    
    # Получаем имена пользователей
    creator_name = await get_username(bot, app['user_created_id'])
    
    if state.application_type == 'in_work':
        mechanic_name = await get_username(bot, app['mechanic_id']) if app['mechanic_id'] else "Не назначен"
        text = f"""➖ 🔨 Заявка ➖
🟡 Статус: В работе
🎱 № {app['id']}
💁🏼‍♂️ Создал заявку: {creator_name}
🍽: {app['restaurant']}\n
🔧 Текст заявки: {app['description']}
👷🏼‍♂️ Техник, принявший в работу: {mechanic_name}\n

Подача: {app['date_created']}
Принята: {app['date_accepted']}\n\n"""
    else:  # pending
        text = f"""➖ 🔨 Заявка ➖
🔴 Статус: еще не принята
🎱 № {app['id']}
💁🏼‍♂️ Cоздал заявку: {creator_name}

🍽: {app['restaurant']}
🔧 Текст заявки: {app['description']}
📅 Создана: {app['date_created']}"""
    
    # Создаем клавиатуру
    keyboard = create_pagination_keyboard(
        current_index=state.current_index,
        total_count=len(state.applications),
        application_id=app['id'],
        app_type=state.application_type
    )
    
    # Проверяем есть ли фото
    file_id = app.get('file_id')
    image_data = app.get('image_data')
    
    # Определяем, есть ли фото в текущей заявке
    has_photo = file_id is not None or image_data is not None
    
    if edit and message_id:
        try:
            if has_photo:
                # Если есть фото, редактируем подпись к фото
                await bot.edit_message_caption(
                    chat_id=chat_id,
                    message_id=message_id,
                    caption=text[:1024],  # Ограничение Telegram для caption
                    reply_markup=keyboard
                )
            else:
                # Если нет фото, редактируем текст
                await bot.edit_message_text(
                    text=text,
                    chat_id=chat_id,
                    message_id=message_id,
                    reply_markup=keyboard
                )
        except Exception as e:
            # Если возникла ошибка (например, пытаемся отредактировать фото как текст или наоборот)
            # Удаляем старое сообщение и отправляем новое
            logging.error(f"Ошибка при редактировании сообщения: {e}")
            
            try:
                await bot.delete_message(chat_id, message_id)
            except:
                pass
            
            # Отправляем новое сообщение с правильным типом
            if has_photo:
                if file_id:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=file_id,
                        caption=text[:1024],
                        reply_markup=keyboard
                    )
                elif image_data:
                    await bot.send_photo(
                        chat_id=chat_id,
                        photo=image_data,
                        caption=text[:1024],
                        reply_markup=keyboard
                    )
            else:
                await bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=keyboard
                )
    else:
        # Отправляем новое сообщение
        if has_photo:
            if file_id:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=file_id,
                    caption=text[:1024],
                    reply_markup=keyboard
                )
            elif image_data:
                await bot.send_photo(
                    chat_id=chat_id,
                    photo=image_data,
                    caption=text[:1024],
                    reply_markup=keyboard
                )
        else:
            await bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=keyboard
            )

@applications_view.message(F.text == "🍭 Заявки в работе", RoleFilter(role=["mechanic", "admin"]), F.chat.type == ChatType.PRIVATE)
async def show_in_work_applications(message: Message, bot):
    user = message.from_user
    update_user_info(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    """Показать заявки в работе"""
    user_id = message.from_user.id
    
    # Проверяем роль пользователя
    role = get_user_role(str(user_id))
    if role not in ['mechanic', 'admin']:
        await message.answer("У вас нет доступа к этой функции.")
        return
    
    applications = get_applications_in_work()
    
    if not applications:
        await message.answer("Все заявки в работе выполнены. Больше нет активных заявок.")
        return
    
    # Устанавливаем состояние
    pagination_manager.set_state(user_id, applications, 'in_work')
    
    # Показываем первую заявку
    await show_application(bot, user_id, message.chat.id)

@applications_view.message(F.text == "🕕 Новые заявки", RoleFilter(role=['mechanic', 'admin']), F.chat.type == ChatType.PRIVATE)
async def show_pending_applications(message: Message, bot):
    user = message.from_user
    update_user_info(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    """Показать непринятые заявки"""
    user_id = message.from_user.id
    
    # Проверяем роль пользователя
    role = get_user_role(str(user_id))
    if role not in ['mechanic', 'admin']:
        await message.answer("У вас нет доступа к этой функции.")
        return
    
    applications = get_all_pending_applications()
    
    if not applications:
        await message.answer("Непринятых заявок больше нет. Нажмите на кнопку 🍭 Заявки в работе, чтобы увидеть текущие заявки в работе.")
        return
    
    # Устанавливаем состояние
    pagination_manager.set_state(user_id, applications, 'pending')
    
    # Показываем первую заявку
    await show_application(bot, user_id, message.chat.id)

@applications_view.callback_query(F.data.startswith("prev_"), RoleFilter(role=["mechanic", "admin"]))
async def handle_prev(callback: CallbackQuery, bot):
    """Обработка кнопки "Назад" """
    user_id = callback.from_user.id
    app_type = callback.data.replace("prev_", "")
    
    state = pagination_manager.get_state(user_id)
    if not state or state.application_type != app_type:
        await callback.answer("Сессия истекла. Выберите заявки заново.")
        return
    
    # Сохраняем chat_id перед удалением сообщения
    chat_id = callback.message.chat.id
    
    # Удаляем старое сообщение
    try:
        await callback.message.delete()
    except Exception as e:
        logging.error(f"Ошибка при удалении сообщения: {e}")
    
    # Уменьшаем индекс
    pagination_manager.update_index(user_id, -1)
    
    # Проверяем есть ли еще заявки
    state = pagination_manager.get_state(user_id)
    if state and state.applications:
        # Отправляем новую заявку
        await show_application(bot, user_id, chat_id, edit=False)
    else:
        # Если нет заявок, отправляем сообщение
        await bot.send_message(chat_id, "Нет заявок для отображения.")
    
    await callback.answer()

@applications_view.callback_query(F.data.startswith("next_"), RoleFilter(role=["mechanic", "admin"]))
async def handle_next(callback: CallbackQuery, bot):
    """Обработка кнопки "Вперед" """
    user_id = callback.from_user.id
    app_type = callback.data.replace("next_", "")
    
    state = pagination_manager.get_state(user_id)
    if not state or state.application_type != app_type:
        await callback.answer("Сессия истекла. Выберите заявки заново.")
        return
    
    # Сохраняем chat_id перед удалением сообщения
    chat_id = callback.message.chat.id
    
    # Удаляем старое сообщение
    try:
        await callback.message.delete()
    except Exception as e:
        logging.error(f"Ошибка при удалении сообщения: {e}")
    
    # Увеличиваем индекс
    pagination_manager.update_index(user_id, 1)
    
    # Проверяем есть ли еще заявки
    state = pagination_manager.get_state(user_id)
    if state and state.applications:
        # Отправляем новую заявку
        await show_application(bot, user_id, chat_id, edit=False)
    else:
        # Если нет заявок, отправляем сообщение
        await bot.send_message(chat_id, "Нет заявок для отображения.")
    
    await callback.answer()

@applications_view.callback_query(F.data == "page_info", RoleFilter(role=["mechanic", "admin"]))
async def handle_page_info(callback: CallbackQuery):
    """Обработка кнопки с номером страницы (ничего не делаем)"""
    await callback.answer()

@applications_view.callback_query(F.data.startswith("complete_"), RoleFilter(role=["mechanic", "admin"]))
async def handle_complete(callback: CallbackQuery, bot):
    """Обработка кнопки "Заявка выполнена" """
    user_id = callback.from_user.id
    application_id = int(callback.data.replace("complete_", ""))
    
    state = pagination_manager.get_state(user_id)
    if not state or state.application_type != 'in_work':
        await callback.answer("Сессия истекла. Выберите заявки заново.")
        return
    
    # Обновляем заявку
    success = update_application_mechanic(application_id, str(user_id))
    has_photo = callback.message.photo is not None and len(callback.message.photo) > 0
    

    if success:
        text_of_application = callback.message.text
        # Удаляем заявку из состояния
        pagination_manager.remove_application(user_id, application_id)
        restaurant = get_restaurant_by_id(application_id)
        thread_id = dict_of_topics[restaurant]
        # Проверяем есть ли еще заявки
        state = pagination_manager.get_state(user_id)
        dict_for_notification = get_user_created_and_description_by_id(application_id=application_id)
        text = dict_for_notification['description']
        cropped_text = text[:15] + "..."
        mechanic_id = dict_for_notification['mechanic_id']
        user_accepted = await get_user_name(bot=bot,user_id=mechanic_id)
        await callback.bot.send_message(chat_id=dict_for_notification['user_created_id'], text=f"""
                                  ❗ Ваша заявка с текстом: {cropped_text}\n\n<b>✔ Была выполнена 👨🏼‍🔧{user_accepted}</b>
                                  """)
        
        if has_photo:
            original_text = callback.message.caption
            lines = original_text.split('\n')
            new_lines = ["🟢 ВЫПОЛНЕННАЯ ЗАЯВКА", *lines[2:12]]
            modified_text = '\n'.join(new_lines)
            await callback.message.bot.send_photo(
                            chat_id=-1003420551552,
                            message_thread_id=thread_id,
                            caption=modified_text,
                            photo=callback.message.photo[-1].file_id
                        )
        else:
            original_text = callback.message.text
            # Текстовое сообщение
            lines = original_text.split('\n')
            new_lines = ["➖ 🔨 Заявка ➖", f"🟢 Статус: выполнена", *lines[2:11]]
            modified_text = '\n'.join(new_lines)
            await callback.message.bot.send_message(
                            chat_id=-1003420551552,
                            message_thread_id=thread_id,
                            text=modified_text
                        )
        
        if not state or not state.applications:
            await callback.message.delete()
            await bot.send_message(
                callback.message.chat.id,
                "Все заявки в работе выполнены. Больше нет активных заявок."
            )
            pagination_manager.clear_state(user_id)
        else:
            # Обновляем сообщение
            await show_application(
                bot, user_id, callback.message.chat.id,
                message_id=callback.message.message_id,
                edit=False
            )
            await callback.answer("Заявка отмечена как выполненная!")

    else:
        await callback.answer("Ошибка при обновлении заявки", show_alert=True)

@applications_view.callback_query(F.data.startswith("delete_"), RoleFilter(role=["mechanic", "admin"]))
async def handle_delete(callback: CallbackQuery, bot):
    """Обработка кнопки "Удалить заявку" """
    user_id = callback.from_user.id
    application_id = int(callback.data.replace("delete_", ""), RoleFilter(role=["mechanic", "admin"]))
    
    state = pagination_manager.get_state(user_id)
    if not state:
        await callback.answer("Сессия истекла. Выберите заявки заново.")
        return
    
    # Проверяем права
    role = get_user_role(str(user_id))
    if role != 'admin':
        await callback.answer("Только администратор может удалять заявки", show_alert=True)
        return
    
    # Удаляем заявку
    success = delete_application(application_id)
    
    if success:
        # Удаляем заявку из состояния
        pagination_manager.remove_application(user_id, application_id)
        
        # Проверяем есть ли еще заявки
        state = pagination_manager.get_state(user_id)
        
        if not state or not state.applications:
            await callback.message.delete()
            
            if state.application_type == 'in_work':
                text = "✨ Все заявки в работе выполнены. Нажмите на кнопку 🕕 Заявки в ожидании"
            else:
                text = "Непринятых заявок больше нет. Нажмите на кнопку 🍭 Заявки в работе, чтобы увидеть текущие заявки в работе."
            
            await bot.send_message(callback.message.chat.id, text)
            pagination_manager.clear_state(user_id)
        else:
            # Обновляем сообщение
            await show_application(
                bot, user_id, callback.message.chat.id,
                message_id=callback.message.message_id,
                edit=False
            )
            await callback.answer("Заявка удалена!")
    else:
        await callback.answer("Ошибка при удалении заявки", show_alert=True)

@applications_view.callback_query(F.data.startswith("accept_"), RoleFilter(role=["mechanic", "admin"]))
async def handle_accept(callback: CallbackQuery, bot):
    """Обработка кнопки "Принять заявку" """
    user_id = callback.from_user.id
    application_id = int(callback.data.replace("accept_", ""))
    
    state = pagination_manager.get_state(user_id)
    if not state or state.application_type != 'pending':
        await callback.answer("Сессия истекла. Выберите заявки заново.")
        return
    
    # Принимаем заявку
    success = accept_application(application_id, str(user_id))
    
    if success:
        # Удаляем заявку из состояния
        pagination_manager.remove_application(user_id, application_id)
        
        # Проверяем есть ли еще заявки
        state = pagination_manager.get_state(user_id)
        dict_for_notification = get_user_created_and_description_by_id(application_id=application_id)
        text = dict_for_notification['description']
        cropped_text = text[:15] + "..."
        mechanic_id = dict_for_notification['mechanic_id']
        user_accepted = await get_user_name(bot=bot,user_id=mechanic_id)
        await callback.bot.send_message(chat_id=dict_for_notification['user_created_id'], text=f"""
                                  ❗ Ваша заявка с текстом: {cropped_text}\n\n<b>👨🏼‍🔧 Была принята в работу {user_accepted}</b>
                                  """)
        if not state or not state.applications:
            await callback.message.delete()
            await bot.send_message(
                callback.message.chat.id,
                "Непринятых заявок больше нет. Нажмите на кнопку 🍭 Заявки в работе, чтобы увидеть текущие заявки в работе."
            )
            pagination_manager.clear_state(user_id)
        else:
            # Обновляем сообщение
            await show_application(
                bot, user_id, callback.message.chat.id,
                message_id=callback.message.message_id,
                edit=False
            )
            await callback.answer("Заявка принята в работу!")
    else:
        await callback.answer("Не удалось принять заявку", show_alert=True)