import re
import aiohttp
import asyncio
from datetime import datetime
from config.config import Config, load_config
import logging

config: Config = load_config()
logger = logging.getLogger(__name__)

def validate_claim(text: str) -> tuple[bool, str, str, str]:
    allowed_restaurants: set = {"ДУО", "ТАРТАР", "АЗИЯ", "ХАРВЕСТ", "РЕБОРН", "ФРАНЦУЗ", "ОДЖИ", "ПЕРЕМЕНА", "ЛАВРАКИ", "БАМБИНА"}

    text = text.strip()

    # 1) Старый формат со скобками: #заявка (ЛАВРАКИ) текст
    match = re.match(r'^#заявка\s+\(([^)]+)\)\s*(.*)$', text, flags=re.DOTALL)
    if match:
        restaurant = match.group(1).strip()
        task = match.group(2).strip()
    else:
        # 2) Новый формат без скобок: #заявка ЛАВРАКИ текст
        #    Название ресторана — первое слово, всё после — задача
        match = re.match(r'^#заявка\s+(\S+)(?:\s+(.*))?$', text, flags=re.DOTALL)
        if not match:
            return False, "", "", (
                "Заявка не отправлена (неверный формат). Примеры:\n"
                "  #заявка ЛАВРАКИ Текст проблемы\n"
                "  #заявка (ЛАВРАКИ) Текст проблемы"
            )
        restaurant = match.group(1).strip()
        task = (match.group(2) or "").strip()

    if not restaurant:
        return False, "", "", "Название ресторана не может быть пустым"

    if restaurant.upper() not in allowed_restaurants:
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

