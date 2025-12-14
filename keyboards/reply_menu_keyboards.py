from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from lexicon.lexicon import LEXICON
def create_manager_keyboard():
    kb_builder = ReplyKeyboardBuilder()
    kb_builder.row(
        KeyboardButton(text=LEXICON["send_request"], callback_data="send_request"),
        KeyboardButton(text=LEXICON["reauthorize"], callback_data="reauthorize")
    )
    kb_builder.adjust(3)
    return kb_builder.as_markup(resize_keyboard=True)

def create_admin_keyboard():
    kb_builder = ReplyKeyboardBuilder()
    kb_builder.row(
        KeyboardButton(text=LEXICON["send_request"], callback_data="send_request"),
        KeyboardButton(text=LEXICON["view_claimed_requests"], callback_data="view_claimed_requests"),
        KeyboardButton(text=LEXICON["view_waiting_requests"], callback_data="view_waiting_requests"),
        KeyboardButton(text=LEXICON["admin_panel"], callback_data="admin_panel_button"),
        KeyboardButton(text=LEXICON["reauthorize"], callback_data="reauthorize"),
    )
    kb_builder.adjust(3)
    return kb_builder.as_markup(resize_keyboard=True)

def create_mechanic_keyboard():
    kb_builder = ReplyKeyboardBuilder()
    kb_builder.row(
        KeyboardButton(text=LEXICON["view_claimed_requests"], callback_data="view_claimed_requests"),
        KeyboardButton(text=LEXICON["view_waiting_requests"], callback_data="view_waiting_requests"),
        # KeyboardButton(text=LEXICON["pick_my_restaurants"], callback_data="pick_my_restaurants"),
        KeyboardButton(text=LEXICON["reauthorize"], callback_data="reauthorize")
    )
    kb_builder.adjust(3)
    return kb_builder.as_markup(resize_keyboard=True)