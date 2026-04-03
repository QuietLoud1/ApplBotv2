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
from database.google_service import validate_claim, save_claim


logger = logging.getLogger(__name__)

application_writing = Router()
@application_writing.callback_query(
    F.data.in_({"completed_writing_application", "cancelled_writing_application"}),
    StateFilter(MenuStates.report_a_problem_with_text),
    RoleFilter(role=["admin", "manager"]),
)
async def application_complition_ended(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.message.edit_text(
        "⏳ Обрабатываю заявку, пожалуйста, подождите...",
        reply_markup=None  # убираем клавиатуру полностью
    )
    if callback.data == "completed_writing_application":
        await callback.answer()
        data = await state.get_data()
        
        texts = data.get("texts_list", [])
        photo_id = data.get("photo_id")
        username = data.get("username", "Не указан")
        restaurant = data.get("restaurant", "Не указан")
        application_text = "\n".join(texts) if texts else "Заявка отправлена без текста"
        
        mechanic_ids = get_mechanic_ids()
        admin_ids = get_admin_ids()
        
        admin_and_mechanic_ids = mechanic_ids + admin_ids
        
        # Загрузка фото (если есть)
        image_data = None
        file_id = None
        if photo_id:
            try:
                file = await bot.get_file(photo_id)
                image_bytes = await bot.download_file(file.file_path)
                image_data = image_bytes.read() if hasattr(image_bytes, 'read') else image_bytes
                file_id = photo_id
            except Exception as e:
                logging.error(f"Ошибка загрузки фото: {e}")
                await callback.message.answer("⚠️ Фото не загружено, заявка без фото")
        
        # Создание заявки в БД
        application_id = create_application(
            user_created_id=str(callback.from_user.id),
            description=application_text,
            restaurant=restaurant,
            image_data=image_data,
            file_id=file_id,
        )
        
        # Сохранение в Google Sheets
        result_sheets = await save_claim(id=application_id, restaurant=restaurant, task=application_text, file_id=photo_id)
        if result_sheets and result_sheets.get('success'):
            logger.info("✅ Заявка добавлена в Google Sheets")
        else:
            error_msg = result_sheets.get('error', 'Неизвестная ошибка') if result_sheets else 'Нет ответа'
            logger.error(f"❌ Ошибка при добавлении в таблицу: {error_msg}")
        
        # Отправка уведомлений техникам и админам
        for user_id in admin_and_mechanic_ids:
            mess = (f"🎇 Новая заявка!\n\n"
                    f"ID: {application_id}\n"
                    f"От: @{username}\n"
                    f"Ресторан: {restaurant}\n\n"
                    f"Проблема: {application_text[:500]}")
            try:
                if photo_id and file_id:
                    await bot.send_photo(
                        chat_id=int(user_id),
                        photo=file_id,
                        caption=mess,
                        reply_markup=pick_application_by_mechanic(application_id)
                    )
                else:
                    await bot.send_message(
                        chat_id=int(user_id),
                        text=mess,
                        reply_markup=pick_application_by_mechanic(application_id)
                    )
            except Exception as e:
                logging.error(f"Ошибка отправки технику {user_id}: {e}")
        
        # (Опционально) отправка в супергруппу с топиком
        # thread_id = dict_of_topics.get(restaurant)  # безопасно
        # if thread_id:
        #     await bot.send_message(chat_id=GROUP_ID, message_thread_id=thread_id, text=mess)
        
        # ✅ Редактируем исходное сообщение – убираем кнопки
        await callback.message.edit_text(
            "✅ Заявка успешно отправлена техникам.",
            reply_markup=None
        )
        
    elif callback.data == "cancelled_writing_application":
        await callback.answer("❌ Заявка отменена")
        await callback.message.edit_text("Заявка отменена.", reply_markup=None)
    
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
        photo_id = message.photo[-1].file_id
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


@application_writing.message(F.photo, F.caption.startswith("#заявка"), F.chat.type == ChatType.GROUP)
async def correct_application_handler(message: Message, bot: Bot):
    if message.caption is None:
        await message.reply("Добавьте подпись к фото с заявкой!")
        return

    photo_id = message.photo[-1].file_id  # самое большое фото
    text = message.caption
    isClaimed, restaurant, task_text, error_text = validate_claim(text)


    user_id = message.from_user.id
    if isClaimed:
        file_id = photo_id
        image_data = None

        try:
            image_bytes_io = await bot.download(photo_id)   # получаем BytesIO
            image_data = image_bytes_io.getvalue()         # преобразуем в bytes
        except Exception as e:
            logging.error(f"Ошибка загрузки фото в бд: {e}")
            await message.reply("⚠️ Не удалось загрузить фото, заявка не сохранена.")
            return

        application_id = create_application(
            user_created_id=str(user_id),
            description=task_text,
            restaurant=restaurant,
            image_data=image_data,
            file_id=file_id,
        )
        await message.reply(f"✅ Заявка из {restaurant} отправлена!")

            # Отправка в гугл щитс
        result_sheets = await save_claim(id=application_id,restaurant=restaurant, task=task_text, file_id=photo_id)
        if result_sheets and result_sheets.get('success'):
            logger.info("✅ В таблицу добавлена новая заявка с фото - через беседу")
        else:
            error_msg = result_sheets.get('error', 'Неизвестная ошибка') if result_sheets else 'Нет ответа'
            logger.error(f"❌ Ошибка при добавлении заявки в таблицу: {error_msg}")
            await message.reply("⚠️ Заявка принята, но возникла ошибка при сохранении в таблицу. Администратор уведомлён.")

    else:
        await message.reply(f"❌ {error_text}")
        return



@application_writing.message(F.text.startswith("#заявка"), ~F.photo, F.chat.type == ChatType.GROUP)
async def incorrect_application_handler_no_photo(message: Message):
    await message.reply("Заявку можно отправить только с фотографией!")