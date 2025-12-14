from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from lexicon.lexicon import LEXICON
from database.database import restaurants

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
        InlineKeyboardButton(text="💻 Excel", callback_data="excel_menu_button")
        # InlineKeyboardButton(text="👷🏼‍♀️ История заявок", callback_data="history_admin_button"),
        # InlineKeyboardButton(text="👷🏼 Список участников", callback_data="statistics_admin_button"),
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
        InlineKeyboardButton(text="Перейти в бота", url="tg://resolve?domain=dasasjkdaskdkaebot")
    )
    return kb_builder.as_markup()