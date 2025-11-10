import asyncio
import pyodbc
from typing import Optional, Dict, Any
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import os
from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
from DatabaseManager import DatabaseManager

# Загружаем переменные окружения из .env файла
load_dotenv()
WAITING_FOR_TEXT, WAITING_FOR_LOCATION, SELECTING_REQUEST = range(3)

# Получаем токен бота из переменной окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("Не задан BOT_TOKEN в .env файле")

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

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start - создает пользователя и показывает приветствие"""
    try:
        # Получаем информацию о пользователе
        user = update.effective_user
        message = update.message

        # Создаем/получаем пользователя в базе данных
        user_id = await asyncio.to_thread(
            context.bot_data['db'].create_user,
            telegram_id=user.id,
            username=user.username,
            full_name=user.full_name
        )

        # Приветственное сообщение
        welcome_text = (
            f"Привет,\n"
            "Я бот-помощник 112 - система оперативного реагирования для жителей города.\n\n"
            "<b>Доступные команды:</b>\n"
            "/submit_request - Подать новое обращение\n"
            "/my_requests - Посмотреть мои обращения\n"
            "Чтобы начать, используйте команду /submit_request"
        )

        await message.reply_text(
            welcome_text,
            parse_mode='HTML',
            reply_markup=ReplyKeyboardRemove()
        )

    except Exception as e:
        print(f"Ошибка в команде /start: {e}")
        await update.message.reply_text(
            "Произошла ошибка при запуске. Пожалуйста, попробуйте еще раз."
        )

async def submit_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс создания заявки"""
    try:
        user = update.effective_user

        # Создаем клавиатуру с кнопкой для отправки геолокации
        location_keyboard = KeyboardButton(text="Отправить геолокацию", request_location=True)
        custom_keyboard = [[location_keyboard], ["Без геолокации"]]
        reply_markup = ReplyKeyboardMarkup(custom_keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "<b>Подача обращения</b>\n\n"
            "Опишите вашу проблему подробно:\n"
            "• Что произошло?\n"
            "• Где это случилось?\n"
            "• Когда это произошло?\n\n"
            "Вы также можете прикрепить фото/видео к сообщению.",
            parse_mode='HTML',
            reply_markup=reply_markup
        )

        return WAITING_FOR_TEXT

    except Exception as e:
        print(f"Ошибка в команде /submit_request: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте снова.")
        return ConversationHandler.END

async def receive_request_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получает текст заявки и медиа"""
    try:
        user = update.effective_user
        message = update.message

        # Сохраняем текст заявки
        request_text = message.text or message.caption or "Без описания"
        context.user_data['request_text'] = request_text

        # Сохраняем медиафайлы если есть
        photo_file_id = None
        video_file_id = None

        if message.photo:
            photo_file_id = message.photo[-1].file_id
            context.user_data['photo_file_id'] = photo_file_id

        if message.video:
            video_file_id = message.video.file_id
            context.user_data['video_file_id'] = video_file_id

        # Убираем клавиатуру и запрашиваем геолокацию
        await message.reply_text(
            "Текст заявки принят!\n\n"
            "Теперь отправьте геолокацию места проблемы или нажмите 'Без геолокации'",
            reply_markup=ReplyKeyboardMarkup([[KeyboardButton(text="Отправить геолокацию", request_location=True)],
                                              ["Без геолокации"]], resize_keyboard=True)
        )

        return WAITING_FOR_LOCATION

    except Exception as e:
        print(f"Ошибка при получении текста заявки: {e}")
        await update.message.reply_text("Произошла ошибка. Начните заново с /submit_request")
        return ConversationHandler.END

async def receive_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает получение геолокации"""
    try:
        global db_instance
        user = update.effective_user
        message = update.message

        # Получаем координаты
        latitude = message.location.latitude
        longitude = message.location.longitude

        # Создаем заявку в БД
        db_user = db_instance.get_user_by_telegram_id(user.id)
        if not db_user:
            # Создаем пользователя если не существует
            user_id = db_instance.create_user(
                telegram_id=user.id,
                username=user.username,
                full_name=user.full_name
            )
            db_user = db_instance.get_user_by_telegram_id(user.id)

        request_info = db_instance.create_request(
            user_id=db_user['id'],
            request_text=context.user_data.get('request_text', 'Без описания'),
            photo_url=context.user_data.get('photo_file_id'),
            video_url=context.user_data.get('video_file_id'),
            latitude=latitude,
            longitude=longitude
        )

        # Обрабатываем дату создания (может быть строкой или datetime)
        created_at = request_info['created_at']
        if isinstance(created_at, str):
            # Если это строка, преобразуем в datetime
            from datetime import datetime
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

        # Форматируем дату для отображения
        formatted_date = created_at.strftime('%d.%m.%Y %H:%M')

        # Очищаем временные данные
        context.user_data.clear()

        await message.reply_text(
            f"<b>Заявка принята!</b>\n\n"
            f"Номер заявки: <code>{request_info['request_number']}</code>\n"
            f"Дата создания: {formatted_date}\n"
            f"С геолокацией: Да\n\n"
            f"Статус заявки можно отслеживать через /my_requests",
            parse_mode='HTML',
            reply_markup=ReplyKeyboardRemove()
        )

        print(f"Создана заявка {request_info['request_number']} для пользователя {user.id}")
        return ConversationHandler.END

    except Exception as e:
        print(f"Ошибка при получении геолокации: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте снова.")
        return ConversationHandler.END

async def skip_location(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Пропускает отправку геолокации"""
    try:
        global db_instance
        user = update.effective_user
        message = update.message

        # Создаем заявку в БД без геолокации
        db_user = db_instance.get_user_by_telegram_id(user.id)
        if not db_user:
            # Создаем пользователя если не существует
            user_id = db_instance.create_user(
                telegram_id=user.id,
                username=user.username,
                full_name=user.full_name
            )
            db_user = db_instance.get_user_by_telegram_id(user.id)

        request_info = db_instance.create_request(
            user_id=db_user['id'],
            request_text=context.user_data.get('request_text', 'Без описания'),
            photo_url=context.user_data.get('photo_file_id'),
            video_url=context.user_data.get('video_file_id'),
            latitude=None,
            longitude=None
        )

        # Обрабатываем дату создания (может быть строкой или datetime)
        created_at = request_info['created_at']
        if isinstance(created_at, str):
            # Если это строка, преобразуем в datetime
            from datetime import datetime
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

        # Форматируем дату для отображения
        formatted_date = created_at.strftime('%d.%m.%Y %H:%M')

        # Очищаем временные данные
        context.user_data.clear()

        await message.reply_text(
            f"<b>Заявка принята!</b>\n\n"
            f"Номер заявки: <code>{request_info['request_number']}</code>\n"
            f"Дата создания: {formatted_date}\n"
            f"С геолокацией: Нет\n\n"
            f"Статус заявки можно отслеживать через /my_requests",
            parse_mode='HTML',
            reply_markup=ReplyKeyboardRemove()
        )

        print(f"Создана заявка {request_info['request_number']} для пользователя {user.id} (без геолокации)")
        return ConversationHandler.END

    except Exception as e:
        print(f"Ошибка при создании заявки без геолокации: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте снова.")
        return ConversationHandler.END

async def cancel_submit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет процесс создания заявки"""
    context.user_data.clear()
    await update.message.reply_text(
        "Создание заявки отменено.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def my_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает список заявок пользователя"""
    try:
        global db_instance
        user = update.effective_user

        # Получаем пользователя из БД
        db_user = db_instance.get_user_by_telegram_id(user.id)
        if not db_user:
            await update.message.reply_text(
                "Вы еще не создавали заявок.\n"
                "Используйте /submit_request чтобы создать первую заявку."
            )
            return

        # Получаем заявки пользователя
        user_requests = db_instance.get_user_requests(db_user['id'])

        if not user_requests:
            await update.message.reply_text(
                "У вас пока нет заявок.\n\n"
                "Создайте первую заявку с помощью команды /submit_request"
            )
            return

        # Формируем сообщение со списком заявок
        message_text = "<b>Ваши заявки:</b>\n\n"

        for i, request in enumerate(user_requests, 1):
            # Обрезаем текст заявки для краткости
            short_text = request['request_text']
            if len(short_text) > 50:
                short_text = short_text[:50] + "..."

            # Форматируем дату
            created_date = format_datetime(request['created_at'])

            # Используем <code> для номера заявки вместо <b>
            message_text += (
                f"{i}. <code>{request['request_number']}</code>\n"
                f"   Статус: <b>{_get_status_text(request['status'])}</b>\n"
                f"   Создана: {created_date}\n"
                f"   {short_text}\n\n"
            )

        message_text += (
            f"Всего заявок: <b>{len(user_requests)}</b>\n\n"
            "Для просмотра деталей конкретной заявки используйте:\n"
            "/request_details\n"
        )

        await update.message.reply_text(message_text, parse_mode='HTML')

        # Логируем запрос
        print(f"Пользователь {user.id} запросил список своих заявок. Найдено: {len(user_requests)} заявок")

    except Exception as e:
        print(f"Ошибка в команде /my_requests: {e}")
        await update.message.reply_text(
            "Произошла ошибка при получении списка заявок. Попробуйте позже."
        )

def _get_status_text(status: str) -> str:
    """Возвращает читабельное название статуса"""
    status_texts = {
        'new': 'Новая',
        'in_progress': 'В обработке',
        'completed': 'Завершена',
        'rejected': 'Отклонена'
    }
    return status_texts.get(status, status)

async def handle_other_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик любых текстовых сообщений кроме команд"""
    await update.message.reply_text(
        "Введите команду:\n"
        "/start, /submit_request, /my_requests"
    )

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

async def request_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает клавиатуру с заявками для выбора"""
    try:
        global db_instance
        user = update.effective_user

        # Получаем пользователя из БД
        db_user = db_instance.get_user_by_telegram_id(user.id)
        if not db_user:
            await update.message.reply_text(
                "У вас пока нет заявок.\n"
                "Создайте первую заявку с помощью /submit_request"
            )
            return ConversationHandler.END

        # Получаем заявки пользователя
        user_requests = db_instance.get_user_requests(db_user['id'])

        if not user_requests:
            await update.message.reply_text(
                "У вас пока нет заявок.\n\n"
                "Создайте первую заявку с помощью команды /submit_request"
            )
            return ConversationHandler.END

        # Создаем клавиатуру с кнопками заявок
        keyboard = []
        for n, request in enumerate(user_requests):
            # Форматируем текст кнопки: номер + статус + дата
            created_date = format_datetime(request['created_at'])
            short_date = created_date.split()[0]  # Берем только дату

            button_text = f"{n+1}. {request['request_number']}" #- {_get_status_text(request['status'])} - {short_date}
            # Обрезаем если слишком длинный
            if len(button_text) > 30:
                button_text = button_text[:27] + "..."

            keyboard.append([button_text])

        # Добавляем кнопку отмены
        keyboard.append(["Отмена"])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "<b>Выберите заявку для просмотра:</b>\n\n"
            "Нажмите на кнопку с номером заявки, чтобы увидеть детали",
            parse_mode='HTML',
            reply_markup=reply_markup
        )

        # Сохраняем список заявок в context для использования в следующем шаге
        context.user_data['user_requests'] = user_requests

        return SELECTING_REQUEST

    except Exception as e:
        print(f"Ошибка в команде /request_details: {e}")
        await update.message.reply_text(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

async def show_selected_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает детали выбранной заявки"""
    try:
        user = update.effective_user
        message_text = update.message.text

        # Проверяем отмену
        if message_text == "Отмена":
            await update.message.reply_text(
                "Просмотр заявок отменен.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        # Получаем сохраненные заявки
        user_requests = context.user_data.get('user_requests', [])

        # Извлекаем номер заявки из текста кнопки (первые 13 символов - это формат ГГГГММДД-СССС)
        request_number = None
        for request in user_requests:
            if request['request_number'] in message_text:
                request_number = request['request_number']
                request_data = request
                break

        if not request_number:
            await update.message.reply_text(
                "Заявка не найдена. Пожалуйста, выберите заявку из списка:",
                reply_markup=ReplyKeyboardMarkup(
                    [[req['request_number']] for req in user_requests] + [["Отмена"]],
                    resize_keyboard=True
                )
            )
            return SELECTING_REQUEST

        # Форматируем даты
        created_date = format_datetime(request_data['created_at'])
        updated_date = format_datetime(request_data['updated_at'])

        # Формируем сообщение с деталями
        detail_text = (
            f"<b>Заявка {request_data['request_number']}</b>\n\n"
            f"<b>Статус:</b> {_get_status_text(request_data['status'])}\n"
            f"<b>Создана:</b> {created_date}\n"
            f"<b>Обновлена:</b> {updated_date}\n\n"
            f"<b>Описание:</b>\n{request_data['request_text']}\n\n"
        )

        # Добавляем информацию о медиа
        if request_data['photo_url']:
            detail_text += "<b>Прикреплено фото</b>\n"
        if request_data['video_url']:
            detail_text += "<b>Прикреплено видео</b>\n"

        # Добавляем информацию о геолокации
        if request_data['latitude'] and request_data['longitude']:
            lat = request_data['latitude']
            lon = request_data['longitude']
            detail_text += f"<b>Координаты:</b> {lat:.6f}, {lon:.6f}\n"
            detail_text += f"<a href='https://yandex.ru/maps/?ll={lon},{lat}&z=19'>Открыть на карте</a>\n"

        # Кнопки для навигации
        keyboard = [
            ["Посмотреть другую заявку"],
            ["Главное меню"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            detail_text,
            parse_mode='HTML',
            reply_markup=reply_markup
        )

        # Если есть фото, отправляем его
        if request_data['photo_url']:
            try:
                await update.message.reply_photo(
                    photo=request_data['photo_url'],
                    caption=f"Фото к заявке {request_data['request_number']}"
                )
            except Exception as e:
                print(f"Не удалось отправить фото: {e}")

        # Если есть видео, отправляем информацию о нем
        if request_data['video_url']:
            try:
                await update.message.reply_video(
                    video=request_data['video_url'],
                    caption=f"Видео к заявке {request_data['request_number']}"
                )
            except Exception as e:
                print(f"Не удалось отправить видео: {e}")

        return SELECTING_REQUEST

    except Exception as e:
        print(f"Ошибка при показе деталей заявки: {e}")
        await update.message.reply_text(
            "Произошла ошибка при получении деталей заявки.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

async def handle_navigation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает навигационные кнопки после просмотра заявки"""
    user = update.effective_user
    message_text = update.message.text

    if message_text == "Посмотреть другую заявку":
        # Возвращаем к выбору заявки
        return await request_details(update, context)
    elif message_text == "Главное меню":
        await update.message.reply_text(
            "Возвращаемся в главное меню.",
            reply_markup=ReplyKeyboardRemove()
        )
        return ConversationHandler.END

    return SELECTING_REQUEST

async def cancel_request_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет процесс выбора заявки"""
    await update.message.reply_text(
        "Просмотр заявок отменен.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

def get_request_by_number(self, user_id: int, request_number: str) -> Optional[Dict[str, Any]]:
    """
    Получает заявку по номеру для конкретного пользователя

    Args:
        user_id: ID пользователя
        request_number: Номер заявки

    Returns:
        Данные заявки или None если не найдена
    """
    try:
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT 
                id, request_number, request_text, status, 
                photo_url, video_url, latitude, longitude,
                created_at, updated_at
            FROM requests 
            WHERE user_id = ? AND request_number = ?
        """, user_id, request_number)

        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'request_number': row[1],
                'request_text': row[2],
                'status': row[3],
                'photo_url': row[4],
                'video_url': row[5],
                'latitude': row[6],
                'longitude': row[7],
                'created_at': row[8],
                'updated_at': row[9]
            }
        return None

    except pyodbc.Error as e:
        print(f"Ошибка при получении заявки по номеру: {e}")
        return None

def main() -> None:
    """Основная функция запуска бота"""
    global db_instance

    # Получаем токен бота
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    if not BOT_TOKEN:
        raise ValueError("Не задан BOT_TOKEN в .env файле")

    # Создаем экземпляр базы данных
    db_instance = DatabaseManager()
    db_instance.connect()

    try:
        # Создаем приложение бота
        application = Application.builder().token(BOT_TOKEN).build()

        # Сохраняем экземпляр БД в bot_data для доступа из обработчиков
        application.bot_data['db'] = db_instance

        # Создаем ConversationHandler для подачи заявки
        request_conv_handler = ConversationHandler(
            entry_points=[CommandHandler('submit_request', submit_request)],
            states={
                WAITING_FOR_TEXT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, receive_request_text),
                    MessageHandler(filters.PHOTO | filters.VIDEO, receive_request_text)
                ],
                WAITING_FOR_LOCATION: [
                    MessageHandler(filters.LOCATION, receive_location),
                    MessageHandler(filters.Regex('^Без геолокации$'), skip_location)
                ],
            },
            fallbacks=[CommandHandler('cancel', cancel_submit)],
        )

        # Создаем ConversationHandler для просмотра заявок
        view_requests_conv_handler = ConversationHandler(
            entry_points=[CommandHandler('request_details', request_details)],
            states={
                SELECTING_REQUEST: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND & ~filters.Regex(
                            '^(Посмотреть другую заявку|Главное меню)$'),
                        show_selected_request
                    ),
                    MessageHandler(
                        filters.Regex('^(Посмотреть другую заявку|Главное меню)$'),
                        handle_navigation
                    )
                ],
            },
            fallbacks=[CommandHandler('cancel', cancel_request_selection)],
        )

        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(request_conv_handler)
        application.add_handler(view_requests_conv_handler)
        application.add_handler(CommandHandler("my_requests", my_requests))

        # Обработчик для любых других сообщений
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_other_messages))

        # Запускаем бота
        print("Бот запущен...")
        application.run_polling()

    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
    finally:
        if db_instance:
            db_instance.disconnect()

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

if __name__ == "__main__":
    main()
