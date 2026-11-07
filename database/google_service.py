import re
import aiohttp
import asyncio
from datetime import datetime
from config.config import Config, load_config
import logging

config: Config = load_config()
logger = logging.getLogger(__name__)

def validate_claim(text: str) -> tuple[bool, str, str, str]:

    allowed_restaurants: set = {"ДУО", "ТАРТАР", "АЗИЯ", "ХАРВЕСТ", "РЕКОЛЬТЕ", "ФРАНЦУЗ", "ОДЖИ", "ПЕРЕМЕНА", "ЛАВРАКИ"}
    """
    Проверяет, соответствует ли текст заявки требуемому формату.
    
    Аргументы:
        text: строка с текстом заявки.
        allowed_restaurants: множество допустимых названий ресторанов.
    
    Возвращает:
        Кортеж (is_valid, restaurant, task, error_message):
            is_valid: bool – успешна ли проверка.
            restaurant: str – извлечённое название ресторана (пустая строка при ошибке).
            task: str – извлечённый текст задачи (пустая строка при ошибке).
            error_message: str – описание ошибки (пустая строка, если is_valid=True).
    """
    # Регулярное выражение: #заявка, затем пробелы, (название), пробелы, текст задачи
    pattern = r'^#заявка\s+\(([^)]+)\)\s*(.*)$'
    match = re.match(pattern, text.strip(), flags=re.DOTALL)
    
    if not match:
        return False, "", "", "Неверный формат. Должно быть: #заявка (НАЗВАНИЕ) текст проблемы"
    
    restaurant = match.group(1).strip()
    task = match.group(2).strip()
    
    if not restaurant:
        return False, "", "", "Название ресторана не может быть пустым"
    
    if restaurant not in allowed_restaurants:
        return False, "", "", f"Ресторан '{restaurant}' не найден в списке допустимых"
    
    if not task:
        return False, "", "", "Текст проблемы не может быть пустым"
    
    return True, restaurant, task, ""


async def save_claim(id: int, restaurant: str, task: str, file_id: str):
    url = "https://script.google.com/macros/s/AKfycbzidNYut90GiQBZhB1XLAWKYX5DrtSSP0nVIvN5uSWW7lqnAgRrBAVaj13KqEt-So1W/exec"
    current_datetime = datetime.now().strftime("%d/%m/%Y")

    payload = {
        "restaurant": restaurant,
        "task": task,
        "date": current_datetime,
        "photo_file_id": file_id,
        "bot_token": config.bot.token,
        "id": id
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            result = await resp.json()
            logger.info(f"📬 Ответ от Apps Script: {result}")
            return result
        
async def change_application_status(restaurant: str, application_id: int, new_status: str) -> dict:
    """
    Изменяет статус заявки в Google Sheets.
    
    Аргументы:
        restaurant: название ресторана (как в таблице)
        application_id: ID заявки (ищется в столбце J)
        new_status: новое значение для столбца I (статус)
    
    Возвращает:
        dict с полями success (bool) и возможно error/result
    """
    url = "https://script.google.com/macros/s/AKfycbzidNYut90GiQBZhB1XLAWKYX5DrtSSP0nVIvN5uSWW7lqnAgRrBAVaj13KqEt-So1W/exec"
    
    payload = {
        "action": "update_status",
        "restaurant": restaurant,
        "id": application_id,   # теперь передаём ID
        "new_status": new_status
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            result = await resp.json()
            logger.info(f"📬 Ответ от Apps Script (изменение статуса): {result}")
            return result

