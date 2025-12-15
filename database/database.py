import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from config.config import Config,load_config


config = load_config()
# Конфигурация БД
DB_PATH = config.bot.database_path_for_excel  # укажите путь к вашей БД
restaurants = ["Duo", "Tartarbar","Азия", "Харвест", "Общая заявка","Реборн", "Француз","Перемена"]
dict_of_topics = {
    "Duo" : "71", "Tartarbar" : "73", "Азия" : "22", "Харвест" : "3", "Общая заявка" : "3", "Реборн" : "77", "Француз" : "80", "Перемена" : "82"
}

@contextmanager
def get_db_connection():
    """Контекстный менеджер для автоматического управления соединением с БД"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
    try:
        yield conn
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def init_db():
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Создание таблицы accounts
        cur.execute("""
            CREATE TABLE IF NOT EXISTS accounts(
                id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                applications_done INTEGER,
                username TEXT,
                first_name TEXT,
                last_name TEXT
            )
        """)
        
        # Создание таблицы applications (если нужна)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS applications(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_created_id TEXT,
                description TEXT,
                date_created DATETIME DEFAULT CURRENT_TIMESTAMP,
                date_accepted DATETIME,
                date_done DATETIME,
                restaurant TEXT,
                mechanic_id TEXT,
                image_data BLOB,
                file_id TEXT
            )
        """)
        
        conn.commit()
        logging.getLogger(__name__).info("База данных инициализирована")

def get_top_mechanics_with_stats():
    """
    Получает топ-5 механиков по количеству выполненных заявок
    
    Returns:
        list: Список словарей с данными о механике или None для пустых позиций
    """
    with get_db_connection() as connection:
        cursor = connection.cursor()
        
        cursor.execute("""
            SELECT id, applications_done 
            FROM accounts 
            WHERE role = 'mechanic' 
            ORDER BY applications_done DESC 
            LIMIT 5
        """)
        
        mechanics = cursor.fetchall()
        result = []
        
        for mechanic in mechanics:
            result.append({
                'user_id': mechanic[0],
                'applications_done': mechanic[1]
            })
        
        # Добавляем None для пустых позиций
        while len(result) < 5:
            result.append(None)
        
        cursor.close()
        return result


def add_user_role(user_id, role):
    """
    Добавляет или обновляет роль пользователя в БД
    
    Args:
        user_id: ID пользователя Telegram
        role: Роль пользователя (например, "client", "mechanic", "admin")
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        # Используем INSERT OR REPLACE для обновления существующей записи
        cur.execute(
            "INSERT OR REPLACE INTO accounts (id, role) VALUES (?, ?)",
            (str(user_id), role)
        )
        conn.commit()

def get_user_role(user_id):
    """
    Получает роль пользователя из БД
    
    Args:
        user_id: ID пользователя Telegram
        
    Returns:
        str: Роль пользователя или "default", если пользователь не найден
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        cur.execute("SELECT role FROM accounts WHERE id = ?", (str(user_id),))
        result = cur.fetchone()
        
        if result:
            return result['role']
        else:
            # Если пользователь не найден, создаем запись с ролью по умолчанию
            cur.execute(
                "INSERT INTO accounts (id, role) VALUES (?, ?)",
                (str(user_id), "default")
            )
            conn.commit()
            return "default"

def get_all_users():
    """
    Получает всех пользователей из БД
    
    Returns:
        list: Список всех пользователей
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM accounts")
        return [dict(row) for row in cur.fetchall()]

def get_mechanic_ids():
    """
    Получает ID всех пользователей с ролью 'mechanic' из БД
    
    Returns:
        list: Список id пользователей механиков
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM accounts WHERE role = 'mechanic'")
        
        # Создаем список из ID
        mechanic_ids = [row['id'] for row in cur.fetchall()]
        return mechanic_ids
    
def get_admin_ids():
    """
    Получает ID всех пользователей с ролью 'mechanic' из БД
    
    Returns:
        list: Список id пользователей механиков
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("SELECT id FROM accounts WHERE role = 'admin'")
        
        # Создаем список из ID
        admin_ids = [row['id'] for row in cur.fetchall()]
        return admin_ids

def get_all_user_ids(role: str):
    """
    Получает ID всех пользователей с ролью 'mechanic' из БД
    
    Returns:
        list: Список id пользователей механиков
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT id FROM accounts WHERE role = '{role}'")
        
        # Создаем список из ID
        manager_ids = [row['id'] for row in cur.fetchall()]
        return manager_ids

def delete_user(user_id):
    """
    Удаляет пользователя из БД
    
    Args:
        user_id: ID пользователя Telegram
    """
    with get_db_connection() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM accounts WHERE id = ?", (str(user_id),))
        conn.commit()
        
def set_default_role_by_id(account_id: str) -> bool:
    """
    Установить роль "default" аккаунту по ID
    
    Args:
        account_id: ID аккаунта
        
    Returns:
        True если обновление успешно, False в случае ошибки или если аккаунт не найден
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            # Проверяем, существует ли аккаунт
            cur.execute("SELECT id FROM accounts WHERE id = ?", (account_id,))
            if not cur.fetchone():
                logging.getLogger(__name__).warning(f"Аккаунт с ID {account_id} не найден")
                return False
            
            # Обновляем роль на "default"
            cur.execute("""
                UPDATE accounts 
                SET role = 'default'
                WHERE id = ?
            """, (account_id,))
            
            conn.commit()
            
            if cur.rowcount > 0:
                logging.getLogger(__name__).info(f"Аккаунту {account_id} установлена роль 'default'")
                return True
            else:
                logging.getLogger(__name__).warning(f"Не удалось обновить роль аккаунта {account_id}")
                return False
                
    except sqlite3.Error as e:
        logging.getLogger(__name__).error(f"Ошибка при установке роли default: {e}")
        return False

def get_application_by_id(application_id: int) -> Optional[Dict[str, Any]]:
    """
    Получить заявку по ID
    
    Args:
        application_id: ID заявки
        
    Returns:
        Словарь с данными заявки или None, если заявка не найдена
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, user_created_id, description, date_created, 
                       date_accepted, date_done, mechanic_id, image_link
                FROM applications 
                WHERE id = ?
            """, (application_id,))
            
            row = cur.fetchone()
            if row:
                # Преобразуем строку результата в словарь
                columns = ['id', 'user_created_id', 'description', 'date_created', 
                          'date_accepted', 'date_done', 'mechanic_id', 'image_link']
                return dict(zip(columns, row))
            return None
    except sqlite3.Error as e:
        logging.getLogger(__name__).error(f"Ошибка при получении заявки: {e}")
        return None
    
def get_user_created_and_description_by_id(application_id: int) -> Optional[Dict[str, Any]]:
    """
    Получить заявку по ID
    
    Args:
        application_id: ID заявки
        
    Returns:
        Словарь с данными заявки или None, если заявка не найдена
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT user_created_id, description, mechanic_id
                FROM applications 
                WHERE id = ?
            """, (application_id,))
            
            row = cur.fetchone()
            if row:
                # Преобразуем строку результата в словарь
                columns = ['user_created_id', 'description', 'mechanic_id']
                return dict(zip(columns, row))
            return None
    except sqlite3.Error as e:
        logging.getLogger(__name__).error(f"Ошибка при получении заявки: {e}")
        return None


def get_restaurant_by_id(application_id: int) -> Optional[str]:
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT restaurant
                FROM applications 
                WHERE id = ?
            """, (application_id,))
            
            row = cur.fetchone()
            if row:
                restaurant = row[0]  # Извлекаем значение из первой колонки
                return restaurant
            return None
    except sqlite3.Error as e:
        logging.getLogger(__name__).error(f"Ошибка при получении ресторана: {e}")
        return None
    
# 2. Удалить заявку по id
def delete_application(application_id: int) -> bool:
    """
    Удалить заявку по ID
    
    Args:
        application_id: ID заявки для удаления
        
    Returns:
        True если удаление успешно, False в случае ошибки
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM applications WHERE id = ?", (application_id,))
            conn.commit()
            
            # Проверяем, была ли удалена хотя бы одна строка
            if cur.rowcount > 0:
                logging.getLogger(__name__).info(f"Заявка {application_id} удалена")
                return True
            else:
                logging.getLogger(__name__).warning(f"Заявка {application_id} не найдена")
                return False
    except sqlite3.Error as e:
        logging.getLogger(__name__).error(f"Ошибка при удалении заявки: {e}")
        return False

# 3. Добавить заявку в БД
def create_application(
    user_created_id: str, 
    description: str, 
    restaurant: str,
    file_id: str = None, 
    image_data: bytes = None
) -> Optional[int]:
    """
    Создать новую заявку
    
    Args:
        user_created_id: ID пользователя, создавшего заявку
        description: Описание проблемы/задачи
        restaurant: Ресторан
        file_id: ID файла (например, из Telegram)
        image_data: BLOB данные изображения
        
    Returns:
        ID созданной заявки или None в случае ошибки
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO applications (user_created_id, description, restaurant, file_id, image_data)
                VALUES (?, ?, ?, ?, ?)
            """, (user_created_id, description, restaurant, file_id, image_data))
            
            conn.commit()
            application_id = cur.lastrowid
            logging.getLogger(__name__).info(f"Заявка {application_id} создана")
            return application_id
    except sqlite3.Error as e:
        logging.getLogger(__name__).error(f"Ошибка при создании заявки: {e}")
        return None

def accept_application(application_id: int, mechanic_id: str) -> bool:
    """
    Принять заявку механиком
    
    Args:
        application_id: ID заявки
        mechanic_id: ID механика
        
    Returns:
        True если обновление успешно, False в случае ошибки
    """
    try:
        # Проверяем доступна ли заявка
        if not is_application_available(application_id):
            return False
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE applications 
                SET date_accepted = ?, mechanic_id = ?
                WHERE id = ? AND date_accepted IS NULL
            """, (current_time, mechanic_id, application_id))
            
            conn.commit()
            
            if cur.rowcount > 0:
                logging.getLogger(__name__).info(f"Заявка {application_id} принята механиком {mechanic_id}")
                return True
            else:
                return False
    except sqlite3.Error as e:
        logging.getLogger(__name__).error(f"Ошибка при принятии заявки: {e}")
        return False

def complete_application(application_id: int) -> bool:
    """
    Отметить заявку как выполненную
    
    Args:
        application_id: ID заявки
        
    Returns:
        True если обновление успешно, False в случае ошибки
    """
    try:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE applications 
                SET date_done = ?
                WHERE id = ? AND date_done IS NULL
            """, (current_time, application_id))
            
            conn.commit()
            
            if cur.rowcount > 0:
                logging.getLogger(__name__).info(f"Заявка {application_id} отмечена как выполненная")
                return True
            else:
                # Проверяем, существует ли заявка
                cur.execute("SELECT id FROM applications WHERE id = ?", (application_id,))
                if cur.fetchone():
                    logging.getLogger(__name__).warning(f"Заявка {application_id} уже выполнена или не найдена")
                else:
                    logging.getLogger(__name__).warning(f"Заявка {application_id} не найдена")
                return False
    except sqlite3.Error as e:
        logging.getLogger(__name__).error(f"Ошибка при выполнении заявки: {e}")
        return False

def detach_application(application_id: int) -> bool:
    """
    Открепить заявку от механика (сбросить mechanic_id и date_accepted)
    
    Args:
        application_id: ID заявки
        
    Returns:
        True если обновление успешно, False в случае ошибки
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE applications 
                SET mechanic_id = NULL, date_accepted = NULL
                WHERE id = ? AND date_done IS NULL
            """, (application_id,))
            
            conn.commit()
            
            if cur.rowcount > 0:
                logging.getLogger(__name__).info(f"Заявка {application_id} откреплена от механика")
                return True
            else:
                # Проверяем, существует ли заявка
                cur.execute("SELECT id FROM applications WHERE id = ?", (application_id,))
                if cur.fetchone():
                    logging.getLogger(__name__).warning(f"Заявка {application_id} уже выполнена или не найдена")
                else:
                    logging.getLogger(__name__).warning(f"Заявка {application_id} не найдена")
                return False
    except sqlite3.Error as e:
        logging.getLogger(__name__).error(f"Ошибка при откреплении заявки: {e}")
        return False

def is_application_completed(application_id: int) -> Optional[bool]:
    """
    Проверить, выполнена ли заявка
    
    Args:
        application_id: ID заявки
        
    Returns:
        True если заявка выполнена, False если не выполнена, 
        None если заявка не найдена или произошла ошибка
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT date_done 
                FROM applications 
                WHERE id = ?
            """, (application_id,))
            
            row = cur.fetchone()
            if row:
                date_done = row[0]
                return date_done is not None
            else:
                logging.getLogger(__name__).warning(f"Заявка {application_id} не найдена")
                return None
    except sqlite3.Error as e:
        logging.getLogger(__name__).error(f"Ошибка при проверке статуса заявки: {e}")
        return None

def get_applications_by_user(user_id: str) -> List[Dict[str, Any]]:
    """
    Получить все заявки пользователя
    
    Args:
        user_id: ID пользователя
        
    Returns:
        Список заявок пользователя
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, user_created_id, description, restaurant, date_created, 
                       date_accepted, date_done, mechanic_id, file_id
                FROM applications 
                WHERE user_created_id = ?
                ORDER BY date_created DESC
            """, (user_id,))
            
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logging.getLogger(__name__).error(f"Ошибка при получении заявок пользователя: {e}")
        return []

def get_pending_applications() -> List[Dict[str, Any]]:
    """
    Получить все не принятые заявки (ожидающие механика)
    
    Returns:
        Список заявок без механика
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, user_created_id, description, restaurant, date_created, 
                       date_accepted, date_done, mechanic_id, file_id
                FROM applications 
                WHERE mechanic_id IS NULL
                ORDER BY date_created ASC
            """)
            
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logging.getLogger(__name__).error(f"Ошибка при получении ожидающих заявок: {e}")
        return []

def get_mechanic_applications(mechanic_id: str, only_active: bool = False) -> List[Dict[str, Any]]:
    """
    Получить заявки, принятые механиком
    
    Args:
        mechanic_id: ID механика
        only_active: Если True, возвращает только невыполненные заявки
        
    Returns:
        Список заявок механика
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            
            query = """
                SELECT id, user_created_id, description, restaurant, date_created, 
                       date_accepted, date_done, mechanic_id, file_id
                FROM applications 
                WHERE mechanic_id = ?
            """
            
            params = [mechanic_id]
            
            if only_active:
                query += " AND (date_done IS NULL OR date_done = '')"
            
            query += " ORDER BY date_accepted DESC"
            
            cur.execute(query, params)
            
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logging.getLogger(__name__).error(f"Ошибка при получении заявок механика: {e}")
        return []

def is_application_available(application_id: int) -> Optional[bool]:
    """
    Проверить, свободна ли заявка (не принята ли уже кем-то)
    
    Args:
        application_id: ID заявки
        
    Returns:
        True - если заявка свободна (date_accepted пустое)
        False - если заявка уже принята (date_accepted не пустое)
        None - если заявка не найдена или произошла ошибка
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT date_accepted 
                FROM applications 
                WHERE id = ?
            """, (application_id,))
            
            row = cur.fetchone()
            if row:
                date_accepted = row[0]
                # Если date_accepted NULL или пустая строка, значит заявка свободна
                return date_accepted is None or date_accepted == ''
            else:
                logging.getLogger(__name__).warning(f"Заявка {application_id} не найдена")
                return None
    except sqlite3.Error as e:
        logging.getLogger(__name__).error(f"Ошибка при проверке доступности заявки: {e}")
        return None
    
def get_applications_in_work() -> List[Dict[str, Any]]:
    """
    Получить все заявки в работе (есть date_accepted, но нет date_done)
    
    Returns:
        Список заявок в работе
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, user_created_id, description, restaurant, date_created, 
                       date_accepted, date_done, mechanic_id, file_id, image_data
                FROM applications 
                WHERE date_accepted IS NOT NULL 
                AND (date_done IS NULL OR date_done = '')
                ORDER BY date_accepted ASC
            """)
            
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logging.getLogger(__name__).error(f"Ошибка при получении заявок в работе: {e}")
        return []

def get_all_pending_applications() -> List[Dict[str, Any]]:
    """
    Получить все непринятые заявки (нет date_accepted)
    
    Returns:
        Список непринятых заявок
    """
    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT id, user_created_id, description, restaurant, date_created, 
                       date_accepted, date_done, mechanic_id, file_id, image_data
                FROM applications 
                WHERE date_accepted IS NULL
                ORDER BY date_created ASC
            """)
            
            rows = cur.fetchall()
            return [dict(row) for row in rows]
    except sqlite3.Error as e:
        logging.getLogger(__name__).error(f"Ошибка при получении непринятых заявок: {e}")
        return []

def update_application_mechanic(application_id: int, mechanic_id: str) -> bool:
    """
    Обновить механика заявки и проставить дату выполнения
    
    Args:
        application_id: ID заявки
        mechanic_id: ID механика
        
    Returns:
        True если обновление успешно
    """
    try:
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE applications 
                SET date_done = ?, mechanic_id = ?
                WHERE id = ?
            """, (current_time, mechanic_id, application_id))
            
            conn.commit()
            
            if cur.rowcount > 0:
                logging.getLogger(__name__).info(f"Заявка {application_id} обновлена механиком {mechanic_id}")
                return True
            else:
                return False
    except sqlite3.Error as e:
        logging.getLogger(__name__).error(f"Ошибка при обновлении заявки: {e}")
        return False
    
def update_user_info(user_id: int, username: str = None, 
                     first_name: str = None, last_name: str = None):
    """Обновляет информацию о пользователе в базе данных"""
    updates = []
    params = []
    
    if username:
        updates.append("username = ?")
        params.append(username)
    
    if first_name:
        updates.append("first_name = ?")
        params.append(first_name)
    
    if last_name:
        updates.append("last_name = ?")
        params.append(last_name)
    
    if not updates:
        return
    
    params.append(str(user_id))
    
    with get_db_connection() as conn:
        cur = conn.cursor()
        query = f"UPDATE accounts SET {', '.join(updates)} WHERE id = ?"
        cur.execute(query, params)
        conn.commit()