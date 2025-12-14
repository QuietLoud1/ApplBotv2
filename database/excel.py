# database/excel.py
import sqlite3
import logging
import io
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import xlsxwriter
from PIL import Image
import pytz
import requests
from config.config import Config, load_config
# Конфигурация

config: Config = load_config()

DB_PATH = config.bot.database_path_for_excel
YADISK_TOKEN = config.bot.yadisk_token  # Замените на ваш токен
YADISK_FOLDER = config.bot.yadisk_folder_name
EXCEL_FILENAME_PREFIX = 'applications_export_'
TIMEZONE = pytz.timezone('Europe/Moscow')

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """Создает и возвращает соединение с БД"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_user_name_from_accounts(user_id: str, conn) -> str:
    """Получить полное имя пользователя из таблицы accounts по ID"""
    if not user_id:
        return ""
    
    cur = conn.cursor()
    cur.execute("SELECT first_name, last_name FROM accounts WHERE id = ?", (user_id,))
    result = cur.fetchone()
    
    if result:
        first_name = result['first_name'] or ""
        last_name = result['last_name'] or ""
        return f"{first_name} {last_name}".strip()
    return user_id

def resize_image_to_fit_cell(image_data: bytes, target_width: int = 80, target_height: int = 60) -> bytes:
    """Изменяет размер изображения, чтобы оно вписывалось в ячейку"""
    try:
        image = Image.open(io.BytesIO(image_data))
        image.thumbnail((target_width, target_height), Image.Resampling.LANCZOS)
        img_byte_arr = io.BytesIO()
        image.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    except Exception as e:
        logger.error(f"Ошибка при обработке изображения: {e}")
        return image_data

def format_datetime(date_str: Optional[str]) -> Optional[datetime]:
    """Преобразует строку даты в объект datetime"""
    if not date_str:
        return None
    
    try:
        formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d',
            '%d.%m.%Y %H:%M:%S'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        return None
    except Exception as e:
        logger.error(f"Ошибка при форматировании даты '{date_str}': {e}")
        return None

def generate_filename() -> str:
    """Генерирует имя файла с временной меткой"""
    moscow_time = datetime.now(TIMEZONE)
    timestamp = moscow_time.strftime('%Y%m%d_%H%M%S')
    return f"{EXCEL_FILENAME_PREFIX}{timestamp}.xlsx"

def create_excel_file(applications, filename: str) -> bool:
    """Создает Excel файл с данными заявок"""
    try:
        workbook = xlsxwriter.Workbook(filename)
        worksheet = workbook.add_worksheet('Заявки')
        
        # Определяем стили
        header_format = workbook.add_format({
            'bold': True, 'text_wrap': True, 'valign': 'vcenter', 'align': 'center',
            'bg_color': '#366092', 'font_color': 'white', 'border': 1
        })
        
        date_format = workbook.add_format({
            'num_format': 'dd.mm.yyyy hh:mm', 'align': 'center',
            'valign': 'vcenter', 'border': 1
        })
        
        text_format = workbook.add_format({
            'text_wrap': True, 'valign': 'vcenter', 'align': 'left', 'border': 1
        })
        
        center_format = workbook.add_format({
            'valign': 'vcenter', 'align': 'center', 'border': 1
        })
        
        # Заголовки столбцов
        headers = [
            ('ID', 10), ('Инициатор', 20), ('Описание', 40),
            ('Дата создания', 18), ('Дата принятия', 18),
            ('Дата выполнения', 18), ('Ресторан', 15),
            ('Механик', 20), ('Фото', 15), ('Статус', 15)
        ]
        
        for col, (header, width) in enumerate(headers):
            worksheet.write(0, col, header, header_format)
            worksheet.set_column(col, col, width)
        
        worksheet.set_default_row(60)
        
        # Подключаемся к БД для получения имен пользователей
        conn = get_db_connection()
        
        # Записываем данные
        for row_idx, app in enumerate(applications, start=1):
            # ID
            worksheet.write(row_idx, 0, app['id'], center_format)
            
            # Инициатор
            initiator_name = get_user_name_from_accounts(app['user_created_id'], conn)
            worksheet.write(row_idx, 1, initiator_name, text_format)
            
            # Описание
            worksheet.write(row_idx, 2, app['description'] or '', text_format)
            
            # Даты
            date_created = format_datetime(app['date_created'])
            if date_created:
                worksheet.write_datetime(row_idx, 3, date_created, date_format)
            
            date_accepted = format_datetime(app['date_accepted'])
            if date_accepted:
                worksheet.write_datetime(row_idx, 4, date_accepted, date_format)
            
            date_done = format_datetime(app['date_done'])
            if date_done:
                worksheet.write_datetime(row_idx, 5, date_done, date_format)
            
            # Ресторан
            worksheet.write(row_idx, 6, app['restaurant'] or '', center_format)
            
            # Механик
            mechanic_name = get_user_name_from_accounts(app['mechanic_id'], conn)
            worksheet.write(row_idx, 7, mechanic_name, text_format)
            
            # Фото
            if app['image_data']:
                try:
                    resized_image = resize_image_to_fit_cell(app['image_data'])
                    image_stream = io.BytesIO(resized_image)
                    worksheet.insert_image(row_idx, 8, f'image_{app["id"]}.png', {
                        'image_data': image_stream, 'x_offset': 5, 'y_offset': 5,
                        'x_scale': 0.9, 'y_scale': 0.9, 'object_position': 2
                    })
                    worksheet.set_row(row_idx, 60)
                except Exception as e:
                    logger.error(f"Ошибка при вставке изображения: {e}")
                    worksheet.write(row_idx, 8, 'Фото доступно', center_format)
            else:
                worksheet.write(row_idx, 8, 'Нет фото', center_format)
            
            # Статус
            status = "Новая"
            if date_accepted and not date_done:
                status = "В работе"
            elif date_accepted and date_done:
                status = "Завершена"
            
            status_format = workbook.add_format({
                'valign': 'vcenter', 'align': 'center', 'border': 1, 'bold': True
            })
            
            if status == "Новая":
                status_format.set_bg_color('#FFD700')
            elif status == "В работе":
                status_format.set_bg_color('#87CEEB')
            elif status == "Завершена":
                status_format.set_bg_color('#90EE90')
            
            worksheet.write(row_idx, 9, status, status_format)
        
        conn.close()
        
        # Автофильтр и форматирование
        worksheet.autofilter(0, 0, len(applications), len(headers) - 1)
        worksheet.freeze_panes(1, 0)
        
        # Добавляем статистику
        add_statistics_sheet(workbook, applications)
        
        workbook.close()
        logger.info(f"Excel файл создан: {filename}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка при создании Excel файла: {e}")
        return False

def add_statistics_sheet(workbook, applications):
    """Добавляет лист со статистикой"""
    worksheet = workbook.add_worksheet('Статистика')
    
    # Заголовок
    title_format = workbook.add_format({
        'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter'
    })
    worksheet.merge_range('A1:C1', 'Статистика по заявкам', title_format)
    worksheet.set_row(0, 30)
    
    # Собираем статистику
    total_apps = len(applications)
    status_counts = {'Новая': 0, 'В работе': 0, 'Завершена': 0}
    restaurant_counts = {}
    
    for app in applications:
        # Статусы
        date_accepted = format_datetime(app['date_accepted'])
        date_done = format_datetime(app['date_done'])
        
        if date_accepted and date_done:
            status_counts['Завершена'] += 1
        elif date_accepted and not date_done:
            status_counts['В работе'] += 1
        else:
            status_counts['Новая'] += 1
        
        # Рестораны
        restaurant = app['restaurant'] or 'Не указан'
        restaurant_counts[restaurant] = restaurant_counts.get(restaurant, 0) + 1
    
    # Записываем статистику
    header_format = workbook.add_format({
        'bold': True, 'bg_color': '#4F81BD', 'font_color': 'white',
        'border': 1, 'align': 'center'
    })
    
    data_format = workbook.add_format({'border': 1, 'align': 'center'})
    percent_format = workbook.add_format({
        'num_format': '0.00%', 'border': 1, 'align': 'center'
    })
    
    # Заголовки таблицы
    stats_headers = ['Показатель', 'Значение', 'Процент']
    for col, header in enumerate(stats_headers):
        worksheet.write(2, col, header, header_format)
    
    # Данные
    row = 3
    worksheet.write(row, 0, 'Всего заявок', data_format)
    worksheet.write(row, 1, total_apps, data_format)
    worksheet.write(row, 2, '100%' if total_apps > 0 else '0%', percent_format)
    
    for status, count in status_counts.items():
        row += 1
        percentage = count / total_apps if total_apps > 0 else 0
        worksheet.write(row, 0, f'Заявки: {status}', data_format)
        worksheet.write(row, 1, count, data_format)
        worksheet.write(row, 2, percentage, percent_format)
    
    row += 2
    
    # Статистика по ресторанам
    worksheet.write(row, 0, 'Статистика по ресторанам', header_format)
    worksheet.write(row, 1, 'Количество', header_format)
    worksheet.write(row, 2, 'Процент', header_format)
    
    for restaurant, count in sorted(restaurant_counts.items(), key=lambda x: x[1], reverse=True):
        row += 1
        percentage = count / total_apps if total_apps > 0 else 0
        worksheet.write(row, 0, restaurant, data_format)
        worksheet.write(row, 1, count, data_format)
        worksheet.write(row, 2, percentage, percent_format)
    
    # Настройка колонок
    worksheet.set_column('A:A', 25)
    worksheet.set_column('B:B', 15)
    worksheet.set_column('C:C', 15)
    
    # Диаграмма
    chart = workbook.add_chart({'type': 'pie'})
    chart.add_series({
        'name': 'Статусы заявок',
        'categories': f'=Статистика!$A$4:$A${3 + len(status_counts)}',
        'values': f'=Статистика!$B$4:$B${3 + len(status_counts)}',
        'data_labels': {'percentage': True, 'category': True}
    })
    chart.set_title({'name': 'Распределение заявок по статусам'})
    chart.set_style(10)
    worksheet.insert_chart('F2', chart)

def check_yadisk_folder() -> bool:
    """Проверяет существование папки на Яндекс.Диске"""
    if not YADISK_TOKEN:
        logger.error("Токен Яндекс.Диска не установлен")
        return False
    
    try:
        headers = {'Authorization': f'OAuth {YADISK_TOKEN}'}
        response = requests.get(
            'https://cloud-api.yandex.net/v1/disk/resources',
            params={'path': YADISK_FOLDER},
            headers=headers
        )
        
        if response.status_code == 200:
            logger.info(f"Папка {YADISK_FOLDER} существует на Яндекс.Диске")
            return True
        elif response.status_code == 404:
            logger.info(f"Папка {YADISK_FOLDER} не существует, создаем...")
            return create_yadisk_folder()
        else:
            logger.error(f"Ошибка при проверке папки: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка подключения к Яндекс.Диску: {e}")
        return False

def create_yadisk_folder() -> bool:
    """Создает папку на Яндекс.Диске"""
    try:
        headers = {'Authorization': f'OAuth {YADISK_TOKEN}'}
        response = requests.put(
            'https://cloud-api.yandex.net/v1/disk/resources',
            params={'path': YADISK_FOLDER},
            headers=headers
        )
        
        if response.status_code in [201, 409]:  # 201 - создана, 409 - уже существует
            logger.info(f"Папка {YADISK_FOLDER} создана на Яндекс.Диске")
            return True
        else:
            logger.error(f"Ошибка при создании папки: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"Ошибка при создании папки: {e}")
        return False

def upload_to_yadisk(filename: str) -> Optional[str]:
    """Загружает файл на Яндекс.Диск и возвращает публичную ссылку"""
    if not YADISK_TOKEN:
        logger.error("Токен Яндекс.Диска не установлен")
        return None
    
    if not check_yadisk_folder():
        logger.error("Не удалось проверить/создать папку на Яндекс.Диске")
        return None
    
    try:
        # Получаем URL для загрузки
        headers = {'Authorization': f'OAuth {YADISK_TOKEN}'}
        upload_params = {
            'path': f'{YADISK_FOLDER.rstrip("/")}/{os.path.basename(filename)}',
            'overwrite': 'true'
        }
        
        response = requests.get(
            'https://cloud-api.yandex.net/v1/disk/resources/upload',
            params=upload_params,
            headers=headers
        )
        
        if response.status_code != 200:
            logger.error(f"Ошибка получения URL для загрузки: {response.status_code} - {response.text}")
            return None
        
        upload_url = response.json()['href']
        
        # Загружаем файл
        with open(filename, 'rb') as f:
            upload_response = requests.put(upload_url, files={'file': f})
        
        if upload_response.status_code != 201:
            logger.error(f"Ошибка загрузки файла: {upload_response.status_code} - {upload_response.text}")
            return None
        
        logger.info(f"Файл успешно загружен на Яндекс.Диск: {filename}")
        
        # Получаем публичную ссылку
        publish_params = {'path': upload_params['path']}
        publish_response = requests.put(
            'https://cloud-api.yandex.net/v1/disk/resources/publish',
            params=publish_params,
            headers=headers
        )
        
        if publish_response.status_code != 200:
            logger.warning(f"Не удалось опубликовать файл: {publish_response.status_code}")
            return None
        
        # Получаем информацию о файле с публичной ссылкой
        info_response = requests.get(
            'https://cloud-api.yandex.net/v1/disk/resources',
            params={'path': upload_params['path']},
            headers=headers
        )
        
        if info_response.status_code == 200:
            file_info = info_response.json()
            public_url = file_info.get('public_url')
            if public_url:
                logger.info(f"Публичная ссылка на файл: {public_url}")
                return public_url
        
        logger.info("Файл загружен, но публичная ссылка не получена")
        return f"Файл загружен в папку {YADISK_FOLDER}"
        
    except Exception as e:
        logger.error(f"Ошибка при загрузке на Яндекс.Диск: {e}")
        return None

def export_applications_to_excel_and_upload() -> Dict[str, Any]:
    """
    Экспортирует данные из таблицы applications в Excel и загружает на Яндекс.Диск
    
    Returns:
        Dict с результатами операции:
        {
            'success': bool,
            'local_file': str or None,
            'yadisk_url': str or None,
            'message': str
        }
    """
    result = {
        'success': False,
        'local_file': None,
        'yadisk_url': None,
        'message': ''
    }
    
    try:
        # Получаем данные из БД
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                a.id,
                a.user_created_id,
                a.description,
                a.date_created,
                a.date_accepted,
                a.date_done,
                a.restaurant,
                a.mechanic_id,
                a.image_data,
                a.file_id
            FROM applications a
            ORDER BY a.date_created DESC
        """)
        
        applications = cur.fetchall()
        conn.close()
        
        if not applications:
            result['message'] = "Нет данных для экспорта"
            logger.warning(result['message'])
            return result
        
        # Генерируем имя файла
        filename = generate_filename()
        
        # Создаем Excel файл
        if not create_excel_file(applications, filename):
            result['message'] = "Ошибка при создании Excel файла"
            return result
        
        result['local_file'] = filename
        result['message'] = f"Excel файл создан: {filename}"
        
        # Загружаем на Яндекс.Диск
        yadisk_url = upload_to_yadisk(filename)
        
        if yadisk_url:
            result['yadisk_url'] = yadisk_url
            result['message'] += f"\nФайл загружен на Яндекс.Диск: {yadisk_url}"
        else:
            result['message'] += "\nНе удалось загрузить файл на Яндекс.Диск"
        
        result['success'] = True
        return result
        
    except Exception as e:
        error_msg = f"Ошибка при экспорте: {e}"
        logger.error(error_msg)
        result['message'] = error_msg
        return result

def export_applications_by_date_range(start_date: str, end_date: str) -> Dict[str, Any]:
    """
    Экспортирует заявки за указанный период дат
    
    Args:
        start_date (str): Начальная дата в формате 'YYYY-MM-DD'
        end_date (str): Конечная дата в формате 'YYYY-MM-DD'
    
    Returns:
        Dict с результатами операции
    """
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT 
                a.id,
                a.user_created_id,
                a.description,
                a.date_created,
                a.date_accepted,
                a.date_done,
                a.restaurant,
                a.mechanic_id,
                a.image_data
            FROM applications a
            WHERE DATE(a.date_created) BETWEEN ? AND ?
            ORDER BY a.date_created DESC
        """, (start_date, end_date))
        
        applications = cur.fetchall()
        conn.close()
        
        if not applications:
            return {
                'success': False,
                'local_file': None,
                'yadisk_url': None,
                'message': f"Нет данных за период с {start_date} по {end_date}"
            }
        
        # Генерируем имя файла с указанием периода
        moscow_time = datetime.now(TIMEZONE)
        timestamp = moscow_time.strftime('%Y%m%d_%H%M%S')
        filename = f"{EXCEL_FILENAME_PREFIX}{start_date}_to_{end_date}_{timestamp}.xlsx"
        
        # Создаем Excel файл
        if not create_excel_file(applications, filename):
            return {
                'success': False,
                'local_file': None,
                'yadisk_url': None,
                'message': "Ошибка при создании Excel файла"
            }
        
        # Загружаем на Яндекс.Диск
        result = {
            'success': True,
            'local_file': filename,
            'yadisk_url': None,
            'message': f"Excel файл создан: {filename}"
        }
        
        yadisk_url = upload_to_yadisk(filename)
        if yadisk_url:
            result['yadisk_url'] = yadisk_url
            result['message'] += f"\nФайл загружен на Яндекс.Диск: {yadisk_url}"
        
        return result
        
    except Exception as e:
        error_msg = f"Ошибка при экспорте за период: {e}"
        logger.error(error_msg)
        return {
            'success': False,
            'local_file': None,
            'yadisk_url': None,
            'message': error_msg
        }

def cleanup_local_files(days_to_keep: int = 7):
    """Удаляет локальные файлы старше указанного количества дней"""
    try:
        current_time = datetime.now(TIMEZONE)
        cutoff_time = current_time - timedelta(days=days_to_keep)
        
        files_deleted = 0
        for filename in os.listdir('.'):
            if filename.startswith(EXCEL_FILENAME_PREFIX) and filename.endswith('.xlsx'):
                file_time = datetime.fromtimestamp(os.path.getctime(filename))
                file_time = TIMEZONE.localize(file_time)
                
                if file_time < cutoff_time:
                    os.remove(filename)
                    files_deleted += 1
                    logger.info(f"Удален старый файл: {filename}")
        
        if files_deleted > 0:
            logger.info(f"Удалено {files_deleted} старых файлов")
            
    except Exception as e:
        logger.error(f"Ошибка при очистке файлов: {e}")

# Пример использования
if __name__ == "__main__":
    print("Тестирование экспорта в Excel с загрузкой на Яндекс.Диск")
    print("=" * 60)
    
    # Проверяем наличие токена
    if not YADISK_TOKEN:
        print("ВНИМАНИЕ: Токен Яндекс.Диска не установлен!")
        print("Установите YADISK_TOKEN в начале файла")
        print("Только создание Excel файла будет работать")
    
    # Экспорт всех заявок
    result = export_applications_to_excel_and_upload()
    
    print("\nРезультат операции:")
    print(f"Успешно: {result['success']}")
    print(f"Локальный файл: {result['local_file']}")
    print(f"Ссылка Яндекс.Диск: {result['yadisk_url']}")
    print(f"Сообщение: {result['message']}")
    
    # Пример экспорта за период
    # today = datetime.now(TIMEZONE).strftime('%Y-%m-%d')
    # week_ago = (datetime.now(TIMEZONE) - timedelta(days=7)).strftime('%Y-%m-%d')
    # result = export_applications_by_date_range(week_ago, today)
    
    # Очистка старых файлов
    cleanup_local_files()