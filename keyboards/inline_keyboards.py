from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from lexicon.lexicon import LEXICON
from database.database import restaurants, get_all_user_ids
from aiogram import Bot

def pick_restaurant_keyboard() -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    for restaurant in restaurants:
        kb_builder.row(
            InlineKeyboardButton(text=restaurant, callback_data=f"{restaurant}")
        )
    kb_builder.adjust(2)
    kb_builder.row(InlineKeyboardButton(text="Назад", callback_data="last_button_restaurant"))
    
    return kb_builder.as_markup()

def application_writing_complete() -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    
    kb_builder.row(
        InlineKeyboardButton(text="Продолжить", callback_data="completed_writing_application"),
        InlineKeyboardButton(text="Отменить", callback_data="cancelled_writing_application")
    )
    
    return kb_builder.as_markup()

def pick_application_by_mechanic(id: int) -> InlineKeyboardMarkup:
    kb_builder = InlineKeyboardBuilder()
    
    kb_builder.row(
        InlineKeyboardButton(text="Откликнуться", callback_data=f"picking_application_{id}"),
        InlineKeyboardButton(text="Пропустить", callback_data=f"skip_pending_application_{id}")
    )
    
    return kb_builder.as_markup()

def admin_panel_menu_keyboard() -> InlineKeyboardMarkup:
    
    kb_builder = InlineKeyboardBuilder()
    
    kb_builder.row(
        InlineKeyboardButton(text="📑 Статистика", callback_data="statistics_admin_button"),
        InlineKeyboardButton(text="💻 Excel", callback_data="excel_menu_button"),
        # InlineKeyboardButton(text="👷🏼‍♀️ История заявок", callback_data="history_admin_button"),
        InlineKeyboardButton(text="👷🏼 Список участников", callback_data="users_admin_button"),
    )
    kb_builder.adjust(2)
    kb_builder.row(InlineKeyboardButton(text="Назад", callback_data="back_to_menu_from_admin_panel"))

    return kb_builder.as_markup()

def statistics_panel_admin_keyboard() -> InlineKeyboardMarkup:
    
    kb_builder = InlineKeyboardBuilder()
    
    kb_builder.row(
        InlineKeyboardButton(text="🔢 Статистика по заявкам", callback_data="statistics_applications_overall"),
        InlineKeyboardButton(text="🥇 Топ техников", callback_data="top_of_mechanics_admin_button")
    )
    kb_builder.adjust(2)
    kb_builder.row(InlineKeyboardButton(text="Назад", callback_data="statistics_admin_panel_back_button"))

    return kb_builder.as_markup()

def back_to_statistics_menu_button_keyboard() -> InlineKeyboardMarkup:
    
    kb_builder = InlineKeyboardBuilder()
    
    kb_builder.row(
        InlineKeyboardButton(text="Назад", callback_data="statistics_admin_panel_back_button"),
    )

    return kb_builder.as_markup()

def excel_section_keyboard() -> InlineKeyboardMarkup:
    
    kb_builder = InlineKeyboardBuilder()
    
    kb_builder.row(
        InlineKeyboardButton(text="Назад", callback_data="back_from_excel_section_to_admin_panel"),
        InlineKeyboardButton(text="Сформировать файл Excel", callback_data="hard_update_excel_tables"),
    )

    return kb_builder.as_markup()

def topic_message_keyboard():

    kb_builder = InlineKeyboardBuilder()
    
    kb_builder.row(
        InlineKeyboardButton(text="Оформить заявку", url="tg://resolve?domain=dasasjkdaskdkaebot")
    )
    return kb_builder.as_markup()
    

def users_buttons_picker():
    
    kb_builder = InlineKeyboardBuilder()
    
    kb_builder.row(
        InlineKeyboardButton(text="Админы", callback_data="pick_admins"),
        InlineKeyboardButton(text="Менеджеры", callback_data="pick_managers"),
        InlineKeyboardButton(text="Техники", callback_data="pick_mechanics"),
        InlineKeyboardButton(text="Заблокированные", callback_data="pick_banned"),
    )
    
    kb_builder.adjust(2)
    kb_builder.row(InlineKeyboardButton(text="Назад", callback_data="statistics_admin_panel_back_button"))

    return kb_builder.as_markup()

_user_names_cache = {}

async def get_user_name(bot: Bot, user_id: int) -> str:
    """
    Получает имя админа по его ID
    
    Args:
        bot: Экземпляр бота
        user_id: ID админа
    
    Returns:
        Строка с именем админа в формате "Имя Фамилия"
    """
    # Проверяем кэш
    if user_id in _user_names_cache:
        return _user_names_cache[user_id]
    
    try:
        # Получаем информацию о пользователе через API Telegram
        user = await bot.get_chat(user_id)
        
        # Формируем полное имя
        if user.last_name:
            user_name = f"{user.first_name} {user.last_name}"
        else:
            user_name = user.first_name
        
        # Сохраняем в кэш
        _user_names_cache[user_id] = user_name
        return user_name
        
    except Exception as e:
        print(f"Ошибка при получении имени админа {user_id}: {e}")
        return f"Админ {user_id}"
    
async def create_admins_keyboard_custom(
    role: str,
    bot: Bot, 
    buttons_per_row: int = 2,
    show_extra_buttons: bool = True
) -> InlineKeyboardMarkup:
    """
    Создает клавиатуру с админами и дополнительными опциями
    
    Args:
        bot: Экземпляр бота
        buttons_per_row: Количество кнопок в строке
        show_extra_buttons: Показывать ли дополнительные кнопки
    
    Returns:
        InlineKeyboardMarkup с кнопками админов
    """
    kb_builder = InlineKeyboardBuilder()
    
    # Получаем список админов
    admins = get_all_user_ids(role=role)
    
    # Создаем кнопки админов
    for user_id in admins:
        user_name = await get_user_name(bot=bot, user_id=user_id)
        kb_builder.button(
            text=f"👤 {user_name}",
            callback_data=f"{role}_select_{user_id}"
        )
    
    # Настраиваем расположение кнопок админов
    if admins:
        kb_builder.adjust(buttons_per_row)
    
    # Добавляем дополнительные кнопки если нужно
    if show_extra_buttons:
        kb_builder.row(
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="close_menu_with_users"
            )
        )
    
    return kb_builder.as_markup()