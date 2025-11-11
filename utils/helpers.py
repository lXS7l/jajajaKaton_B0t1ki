def format_datetime(dt_value):
    """Универсальная функция для форматирования даты и времени"""
    from datetime import datetime

    if isinstance(dt_value, str):
        # Пробуем разные форматы даты
        formats = [
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%d %H:%M:%S.%f000',
            '%Y-%m-%d %H:%M:%S.%f',
        ]

        for fmt in formats:
            try:
                dt_value = datetime.strptime(dt_value, fmt)
                break
            except ValueError:
                continue
        else:
            # Если не удалось распарсить, возвращаем как есть
            return dt_value

    if isinstance(dt_value, datetime):
        return dt_value.strftime('%d.%m.%Y %H:%M')

    return str(dt_value)

def _get_status_text(status: str) -> str:
    """Возвращает читабельное название статуса"""
    status_texts = {
        'new': 'Новая',
        'in_progress': 'В обработке',
        'completed': 'Завершена',
        'rejected': 'Отклонена',
        'cancelled': 'Отменена'
    }
    return status_texts.get(status, status)

async def download_media(bot, file_id: str, file_type: str = 'photo', save_path: str = None) -> str:
    """
    Скачивает медиафайл и сохраняет его локально

    Args:
        bot: Экземпляр бота
        file_id: ID файла из базы данных
        file_type: Тип файла ('photo', 'video', 'document')
        save_path: Путь для сохранения (если None, сохраняет в временную папку)

    Returns:
        Путь к сохраненному файлу
    """
    try:
        # Получаем информацию о файле
        file = await bot.get_file(file_id)

        # Определяем путь для сохранения
        if save_path is None:
            import tempfile
            import os
            # Создаем временную папку если нужно
            temp_dir = tempfile.gettempdir()
            file_extension = file.file_path.split('.')[-1] if file.file_path else 'jpg'
            save_path = os.path.join(temp_dir, f"telegram_{file_id}.{file_extension}")

        # Скачиваем файл
        await file.download_to_drive(custom_path=save_path)
        print(f"Файл сохранен: {save_path}")
        return save_path

    except Exception as e:
        print(f"Ошибка при скачивании файла: {e}")
        return None

async def get_media_url(bot, file_id: str, file_type: str = 'photo') -> str:
    """
    Получает прямую ссылку на медиафайл через Telegram Bot API

    Args:
        bot: Экземпляр бота
        file_id: ID файла из базы данных
        file_type: Тип файла ('photo', 'video', 'document')

    Returns:
        Прямая ссылка для скачивания файла
    """
    try:
        # Получаем информацию о файле
        file = await bot.get_file(file_id)

        # Формируем прямую ссылку для скачивания
        file_url = f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
        return file_url

    except Exception as e:
        print(f"Ошибка при получении ссылки на файл: {e}")
        return None

async def handle_other_messages(update, context) -> None:
    """Обработчик любых текстовых сообщений кроме команд"""
    await update.message.reply_text(
        "Введите команду:\n"
        "/start, /submit_request, /my_requests"
    )