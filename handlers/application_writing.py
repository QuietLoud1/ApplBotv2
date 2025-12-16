from aiogram import Router, types
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery
from lexicon.lexicon import LEXICON
from config.config import Config, load_config
from database.database import add_user_role, get_user_role, create_application, dict_of_topics
from middlewares.role_checker import RolesMiddleware, require_role, RoleFilter
from aiogram import F
from keyboards.reply_menu_keyboards import create_manager_keyboard,create_admin_keyboard,create_mechanic_keyboard
from keyboards.inline_keyboards import pick_restaurant_keyboard, application_writing_complete, pick_application_by_mechanic
import logging
from aiogram.fsm.state import default_state
from aiogram.filters import StateFilter
from states.states import MenuStates
from aiogram.fsm.context import FSMContext
from database.database import restaurants
from database.database import get_mechanic_ids, get_admin_ids, update_user_info, get_restaurant_by_id
from aiogram.methods import SendMessage
from aiogram import Bot
from aiogram.enums import ChatType

application_writing = Router()
@application_writing.callback_query(F.data.in_("completed_writing_application") 
                                    | F.data.in_("cancelled_writing_application"), 
                                    StateFilter(MenuStates.report_a_problem_with_text), 
                                    RoleFilter(role=["admin", "manager"]),
)
async def application_complition_ended(callback: CallbackQuery, state: FSMContext, bot: Bot):
    if callback.data == "completed_writing_application":
        await callback.answer()
        data = await state.get_data()
        
        texts = data.get("texts_list", [])
        photo_id = data.get("photo_id")  # Может быть None!
        username = data.get("username", "Не указан")
        restaurant = data.get("restaurant", "Не указан")  # Получаем ресторан из состояния
        application_text = f"{'\n'.join(texts) if texts else 'Нет текста'}"
        mechanic_ids = get_mechanic_ids()
        admin_ids = get_admin_ids()
        
        admin_and_mechanic_ids = mechanic_ids + admin_ids
        
        image_data = None
        file_id = None
        
        # ПРОВЕРЯЕМ ЕСТЬ ЛИ PHOTO_ID ПЕРЕД СКАЧИВАНИЕМ
        if photo_id:
            try:
                file = await bot.get_file(photo_id)
                image_bytes = await bot.download_file(file.file_path)
                
                if hasattr(image_bytes, 'read'):
                    image_data = image_bytes.read()
                else:
                    image_data = image_bytes
                    
                file_id = photo_id
                
            except Exception as e:
                logging.error(f"Ошибка загрузки фото: {e}")
                await callback.message.answer("⚠️ Фото не удалось загрузить, заявка создана без фото")
        
        # Создаем заявку (с фото или без) - ТЕПЕРЬ С РЕСТОРАНОМ
        user_id = callback.from_user.id
        application_id = create_application(
            user_created_id=str(user_id), 
            description=application_text,  # Убрал обрезку до 50 символов, чтобы сохранялся полный текст
            restaurant=restaurant,  # Добавляем ресторан
            image_data=image_data, 
            file_id=file_id,
        )
        
        if not application_id:
            await callback.message.answer("❌ Ошибка при создании заявки")
            await state.clear()
            await state.set_state(MenuStates.main_menu)
            return
        await callback.message.answer(text="✅ Заявка заполнена и отправлена техникам")
        try:
            thread_id = dict_of_topics[restaurant]
            mess = f"""🎇 Новая заявка!
                        
ID заявки: {application_id}
От: @{username}
Ресторан: {restaurant}

Проблема: {application_text[:500]}""" 
            if photo_id and file_id:
                await callback.message.bot.send_photo(
                            photo=file_id if file_id else photo_id,
                            chat_id=-1003420551552,
                            message_thread_id=thread_id,
                            caption=mess
                        )
            else:
                await callback.message.bot.send_message(
                            chat_id=-1003420551552,
                            message_thread_id=thread_id,
                            text=mess
                        )
        except Exception as e:
                logging.error(f"Ошибка отправки заявки в тему в супергруппе: {e}")        
        for user_notified_id in admin_and_mechanic_ids:
            try:
                if photo_id and file_id:
                    mess = f"""Заявка в работе\n
ID заявки: {application_id}
От: {username}
🥩 {restaurant}

📑 {application_text[:500]}""" 
                    # Отправляем с фото
                    await callback.message.bot.send_photo(
                        chat_id=int(user_notified_id),
                        photo=file_id if file_id else photo_id,
                        reply_markup=pick_application_by_mechanic(application_id),
                        caption=mess # Обрезаем для отображения в телеграме
                    )
                else:
                    mess = f"""🎇 Новая заявка!
                        
ID заявки: {application_id}
От: @{username}
Ресторан: {restaurant}

Проблема: {application_text[:500]}"""
                    # Отправляем без фото
                    await callback.message.bot.send_message(
                        chat_id=int(user_notified_id),
                        reply_markup=pick_application_by_mechanic(application_id),
                        text=mess # Обрезаем для отображения в телеграме
                    )
                    
            except Exception as e:
                logging.error(f"Ошибка отправки заявки технику {user_notified_id}: {e}")
            
    elif callback.data == "cancelled_writing_application":
        await callback.message.answer("❌ Заявка отменена")
    
    await state.clear()
    await state.set_state(MenuStates.main_menu)
        
        
@application_writing.message(F.text.contains(LEXICON['send_request']), RoleFilter(role=["admin", "manager"]), F.chat.type == ChatType.PRIVATE)
async def send_request_message_handler(message: Message, state: FSMContext):
    await message.answer(
        text=LEXICON["request_pick_a_restaurant"],
        reply_markup=pick_restaurant_keyboard()
    )
    user = message.from_user
    update_user_info(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name
    )
    await state.set_state(MenuStates.report_problem_restaurant_pick)
    
@application_writing.callback_query(F.data.in_(restaurants), StateFilter(MenuStates.report_problem_restaurant_pick), RoleFilter(role=["admin", "manager"]))
async def process_buttons_click(callback: CallbackQuery, state: FSMContext):
    await state.update_data(restaurant=callback.data)
    await callback.message.edit_text(LEXICON['write_a_text_about_problem'])
    logging.info(f"Current state: {await state.get_state()}")
    await state.update_data(texts_list = [], photos_list = [])
    await state.set_state(state=MenuStates.report_a_problem_with_text)

@application_writing.message(F.text | F.photo, StateFilter(MenuStates.report_a_problem_with_text, ~Command("get_application")), RoleFilter(role=["admin", "manager"]), F.chat.type == ChatType.PRIVATE)
async def process_sent_problem(message: Message, state: FSMContext):
    logging.info(f"Received message: {message.content_type}")
    logging.info(f"Current state: {await state.get_state()}")
    data = await state.get_data()
    texts_list = data.get("texts_list", [])
    
    last_buttons_id = data.get("last_buttons_id")
    
    if last_buttons_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=last_buttons_id)
        except:
            pass
    await state.update_data(username=message.from_user.username)
    if message.content_type == "text":
        texts_list.append(message.text)
        await state.update_data(texts_list=texts_list)
        buttons_message = await message.answer(text=LEXICON["text_added"],reply_markup=application_writing_complete())
        
    if message.content_type == "photo":
        photo_id = message.photo[0].file_id
        await state.update_data(photo_id=photo_id)
        buttons_message = await message.answer(LEXICON["photo_added"],reply_markup=application_writing_complete())
        if message.caption:
            texts_list.append(message.caption)
            await state.update_data(texts_list=texts_list)
    await state.update_data(last_buttons_id=buttons_message.message_id)
            
@application_writing.message(~F.text & ~F.photo, StateFilter(MenuStates.report_a_problem_with_text,  ~Command("get_application")), RoleFilter(role=["admin", "manager"]), F.chat.type == ChatType.PRIVATE)
async def process_sent_problem(message: Message, state: FSMContext):
    logging.info(f"Current state: {await state.get_state()}")
    await message.answer(LEXICON["incorrect_content_type_in_application"])