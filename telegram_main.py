import asyncio
import pyodbc
from typing import Optional, Dict, Any
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler, \
    CallbackQueryHandler
import os
from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, \
    InlineKeyboardMarkup
from dotenv import load_dotenv
from DatabaseManager import DatabaseManager
from datetime import datetime

# Загружаем переменные окружения из .env файла
load_dotenv()
(WAITING_FOR_TEXT, WAITING_FOR_LOCATION, SELECTING_REQUEST, WAITING_FOR_ADMIN_CODE,
 WAITING_FOR_BROADCAST, WAITING_FOR_REPORT_PERIOD) = range(6)

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
    """Показывает детали выбранной заявки с кнопкой отмены"""
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

        # Извлекаем номер заявки из текста кнопки
        request_number = None
        request_data = None
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

        # Сохраняем данные заявки в context для использования в callback
        context.user_data['current_request'] = request_data

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
            detail_text += "📷 <b>Прикреплено фото</b>\n"
        if request_data['video_url']:
            detail_text += "🎥 <b>Прикреплено видео</b>\n"

        # Добавляем информацию о геолокации
        if request_data['latitude'] and request_data['longitude']:
            lat = request_data['latitude']
            lon = request_data['longitude']
            detail_text += f"<b>Координаты:</b> {lat:.6f}, {lon:.6f}\n"
            detail_text += f"<a href='https://yandex.ru/maps/?ll={lon},{lat}&z=19'>Открыть на карте</a>\n"

        # Создаем инлайн-клавиатуру с кнопкой отмены (только для заявок со статусом new или in_progress)
        reply_markup = None
        if request_data['status'] in ['new', 'in_progress']:
            keyboard = [
                [InlineKeyboardButton("Отменить заявку", callback_data=f"cancel_{request_data['id']}")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            detail_text += "\n\nВы можете отменить эту заявку, если она еще не обработана:"

        # Кнопки для навигации (обычная клавиатура)
        nav_keyboard = [
            ["Посмотреть другую заявку"],
            ["Главное меню"]
        ]
        nav_reply_markup = ReplyKeyboardMarkup(nav_keyboard, resize_keyboard=True)

        # Отправляем сообщение с деталями и инлайн-кнопкой (если есть)
        if reply_markup:
            await update.message.reply_text(
                detail_text,
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                detail_text,
                parse_mode='HTML'
            )

        # Отправляем навигационные кнопки отдельным сообщением
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=nav_reply_markup
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

async def handle_inline_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает нажатия на инлайн-кнопки"""
    query = update.callback_query
    await query.answer()

    # Извлекаем данные из callback_data
    callback_data = query.data

    if callback_data.startswith("cancel_"):
        request_id = int(callback_data.split("_")[1])
        await cancel_request_callback(query, context, request_id)

async def cancel_request_callback(query, context, request_id):
    """Обрабатывает отмену заявки через инлайн-кнопку"""
    try:
        global db_instance
        user = query.from_user

        # Получаем пользователя из БД
        db_user = db_instance.get_user_by_telegram_id(user.id)
        if not db_user:
            await query.edit_message_text("Ошибка: пользователь не найден.")
            return

        # Пытаемся отменить заявку
        success = db_instance.cancel_request(request_id, db_user['id'])

        if success:
            # Обновляем сообщение - убираем кнопку и меняем статус
            message_text = query.message.text
            # Заменяем статус в тексте сообщения
            new_message_text = message_text.replace(
                "<b>Статус:</b> Новая",
                "<b>Статус:</b> Отменена"
            ).replace(
                "<b>Статус:</b> В обработке",
                "<b>Статус:</b> Отменена"
            )

            # Убираем предложение отменить заявку
            new_message_text = new_message_text.split("\n\nВы можете отменить эту заявку")[0]

            await query.edit_message_text(
                new_message_text + "\n\n<b>Заявка успешно отменена!</b>",
                parse_mode='HTML'
            )

            print(f"Пользователь {user.id} отменил заявку {request_id}")
        else:
            await query.answer("Не удалось отменить заявку. Возможно, она уже обработана.", show_alert=True)

    except Exception as e:
        print(f"Ошибка при отмене заявки через callback: {e}")
        await query.answer("Произошла ошибка при отмене заявки.", show_alert=True)

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /admin - запрашивает код администратора"""
    try:
        user = update.effective_user

        # Проверяем, не является ли пользователь уже администратором
        db_user = db_instance.get_user_by_telegram_id(user.id)
        if db_user and db_user['is_admin']:
            await show_admin_menu(update, context)
            return ConversationHandler.END

        await update.message.reply_text(
            "<b>Вход в админ-панель</b>\n\n"
            "Введите секретный код администратора:",
            parse_mode='HTML',
            reply_markup=ReplyKeyboardRemove()
        )

        return WAITING_FOR_ADMIN_CODE

    except Exception as e:
        print(f"Ошибка в команде /admin: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте снова.")
        return ConversationHandler.END

async def verify_admin_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Проверяет введенный код администратора"""
    try:
        user = update.effective_user
        code = update.message.text

        # Получаем пользователя из БД
        db_user = db_instance.get_user_by_telegram_id(user.id)
        if not db_user:
            await update.message.reply_text("Пользователь не найден в базе данных.")
            return ConversationHandler.END

        # ПЕРЕДАЕМ TELEGRAM_ID, а не внутренний ID!
        success = db_instance.verify_admin_code(code, user.id)

        if success:
            await update.message.reply_text(
                "<b>Код принят! Теперь вы администратор.</b>",
                parse_mode='HTML'
            )
            await show_admin_menu(update, context)
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "<b>Неверный код</b>\n\n"
                "Попробуйте еще раз или введите /cancel для отмены:",
                parse_mode='HTML'
            )
            return WAITING_FOR_ADMIN_CODE

    except Exception as e:
        print(f"Ошибка при проверке кода администратора: {e}")
        await update.message.reply_text("Произошла ошибка. Попробуйте снова.")
        return ConversationHandler.END

async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает меню администратора"""
    keyboard = [
        ["Статистика", "Все заявки"],
        ["Все пользователи", "Выгрузка отчета"],
        ["Рассылка", "Главное меню"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "<b>Админ-панель</b>\n\n"
        "Выберите действие:",
        parse_mode='HTML',
        reply_markup=reply_markup
    )

async def admin_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает статистику для администратора"""
    try:
        # Проверяем права администратора
        user = update.effective_user
        db_user = db_instance.get_user_by_telegram_id(user.id)

        if not db_user or not db_user['is_admin']:
            await update.message.reply_text("У вас нет прав администратора.")
            return

        # Получаем статистику
        all_requests = db_instance.get_all_requests()
        all_users = db_instance.get_all_users()

        # Считаем заявки по статусам
        status_count = {
            'new': 0,
            'in_progress': 0,
            'completed': 0,
            'rejected': 0,
            'cancelled': 0
        }

        for request in all_requests:
            status_count[request['status']] = status_count.get(request['status'], 0) + 1

        # Формируем сообщение
        stats_text = (
            "<b>Статистика системы</b>\n\n"
            f"<b>Всего пользователей:</b> {len(all_users)}\n"
            f"<b>Всего заявок:</b> {len(all_requests)}\n\n"
            f"<b>По статусам:</b>\n"
            f"• Новые: {status_count['new']}\n"
            f"• В обработке: {status_count['in_progress']}\n"
            f"• Завершены: {status_count['completed']}\n"
            f"• Отклонены: {status_count['rejected']}\n"
            f"• Отменены: {status_count['cancelled']}\n\n"
            f"<b>Администраторов:</b> {sum(1 for user in all_users if user['is_admin'])}"
        )

        await update.message.reply_text(stats_text, parse_mode='HTML')

    except Exception as e:
        print(f"Ошибка при показе статистики: {e}")
        await update.message.reply_text("Ошибка при получении статистики.")

async def admin_all_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает все заявки для администратора"""
    try:
        # Проверяем права администратора
        user = update.effective_user
        db_user = db_instance.get_user_by_telegram_id(user.id)

        if not db_user or not db_user['is_admin']:
            await update.message.reply_text("У вас нет прав администратора.")
            return

        # Получаем заявки
        requests = db_instance.get_all_requests(limit=20)  # Ограничиваем для удобства

        if not requests:
            await update.message.reply_text("Заявок пока нет.")
            return

        # Формируем сообщение
        requests_text = "<b>Последние заявки</b>\n\n"

        for i, req in enumerate(requests[:10], 1):  # Показываем первые 10
            user_info = req['user_full_name'] or req['user_username'] or 'Аноним'
            created_date = format_datetime(req['created_at'])

            requests_text += (
                f"{i}. <code>{req['request_number']}</code>\n"
                f"   {user_info}\n"
                f"   {created_date}\n"
                f"   {_get_status_text(req['status'])}\n"
                f"   {req['request_text'][:50]}...\n\n"
            )

        if len(requests) > 10:
            requests_text += f"\n... и еще {len(requests) - 10} заявок"

        await update.message.reply_text(requests_text, parse_mode='HTML')

    except Exception as e:
        print(f"Ошибка при показе всех заявок: {e}")
        await update.message.reply_text("Ошибка при получении заявок.")

async def admin_all_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает всех пользователей для администратора"""
    try:
        # Проверяем права администратора
        user = update.effective_user
        db_user = db_instance.get_user_by_telegram_id(user.id)

        if not db_user or not db_user['is_admin']:
            await update.message.reply_text("У вас нет прав администратора.")
            return

        # Получаем пользователей
        users = db_instance.get_all_users()

        if not users:
            await update.message.reply_text("Пользователей пока нет.")
            return

        # Формируем сообщение
        users_text = "👥 <b>Все пользователи</b>\n\n"

        for i, user_data in enumerate(users[:10], 1):  # Показываем первые 10
            user_name = user_data['full_name'] or user_data['username'] or 'Аноним'
            created_date = format_datetime(user_data['created_at'])
            admin_status = "Админ" if user_data['is_admin'] else "Пользователь"

            users_text += (
                f"{i}. {user_name}\n"
                f"   {admin_status}\n"
                f"   {created_date}\n"
                f"   ID: {user_data['telegram_id']}\n\n"
            )

        if len(users) > 10:
            users_text += f"\n... и еще {len(users) - 10} пользователей"

        await update.message.reply_text(users_text, parse_mode='HTML')

    except Exception as e:
        print(f"Ошибка при показе пользователей: {e}")
        await update.message.reply_text("Ошибка при получении пользователей.")

async def export_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс выгрузки отчета"""
    try:
        # Проверяем права администратора
        user = update.effective_user
        db_user = db_instance.get_user_by_telegram_id(user.id)

        if not db_user or not db_user['is_admin']:
            await update.message.reply_text("У вас нет прав администратора.")
            return ConversationHandler.END

        keyboard = [
            ["За сегодня", "За неделю"],
            ["За месяц", "За все время"],
            ["Отмена"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "<b>Выгрузка отчета</b>\n\n"
            "Выберите период для выгрузки:",
            parse_mode='HTML',
            reply_markup=reply_markup
        )

        return WAITING_FOR_REPORT_PERIOD

    except Exception as e:
        print(f"Ошибка в команде выгрузки отчета: {e}")
        await update.message.reply_text("Ошибка при выгрузке отчета.")
        return ConversationHandler.END

async def generate_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Генерирует и отправляет отчет"""
    try:
        period_text = update.message.text
        days = None

        if period_text == "За сегодня":
            days = 1
        elif period_text == "За неделю":
            days = 7
        elif period_text == "За месяц":
            days = 30
        elif period_text == "За все время":
            days = None
        else:
            await update.message.reply_text("Неверный период. Попробуйте снова.")
            return WAITING_FOR_REPORT_PERIOD

        # Получаем данные для отчета
        requests = db_instance.get_all_requests(days=days)

        # Создаем CSV отчет
        import csv
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                         suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['Номер заявки', 'Статус', 'Текст заявки', 'Пользователь',
                             'Телефон', 'Дата создания', 'Координаты'])

            for req in requests:
                user_name = req['user_full_name'] or req['user_username'] or 'Аноним'
                coords = f"{req['latitude']}, {req['longitude']}" if req['latitude'] else "Нет"
                created_date = format_datetime(req['created_at'])

                writer.writerow([
                    req['request_number'],
                    _get_status_text(req['status']),
                    req['request_text'],
                    user_name,
                    req['user_phone_number'] or 'Не указан',
                    created_date,
                    coords
                ])

            temp_path = f.name

        # Отправляем файл
        with open(temp_path, 'rb') as file:
            await update.message.reply_document(
                document=file,
                filename=f"report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                caption=f"Отчет за {period_text.lower()}\n"
                        f"Всего заявок: {len(requests)}"
            )

        # Удаляем временный файл
        os.unlink(temp_path)

        await update.message.reply_text(
            "Отчет успешно выгружен!",
            reply_markup=ReplyKeyboardRemove()
        )

        return ConversationHandler.END

    except Exception as e:
        print(f"Ошибка при генерации отчета: {e}")
        await update.message.reply_text("Ошибка при генерации отчета.")
        return ConversationHandler.END

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс массовой рассылки"""
    try:
        # Проверяем права администратора
        user = update.effective_user
        db_user = db_instance.get_user_by_telegram_id(user.id)

        if not db_user or not db_user['is_admin']:
            await update.message.reply_text("У вас нет прав администратора.")
            return ConversationHandler.END

        await update.message.reply_text(
            "<b>Массовая рассылка</b>\n\n"
            "Введите сообщение для рассылки всем пользователям:",
            parse_mode='HTML',
            reply_markup=ReplyKeyboardMarkup([["Отмена"]], resize_keyboard=True)
        )

        return WAITING_FOR_BROADCAST

    except Exception as e:
        print(f"Ошибка в команде рассылки: {e}")
        await update.message.reply_text("Ошибка при запуске рассылки.")
        return ConversationHandler.END

async def confirm_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Подтверждает и отправляет рассылку"""
    try:
        message_text = update.message.text

        # Сохраняем текст рассылки для подтверждения
        context.user_data['broadcast_text'] = message_text

        keyboard = [["Отправить", "Отмена"]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "<b>Предпросмотр рассылки</b>\n\n"
            f"{message_text}\n\n"
            "Отправить это сообщение всем пользователям?",
            parse_mode='HTML',
            reply_markup=reply_markup
        )

        return WAITING_FOR_BROADCAST

    except Exception as e:
        print(f"Ошибка при подтверждении рассылки: {e}")
        await update.message.reply_text("Ошибка при подготовке рассылки.")
        return ConversationHandler.END

async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выполняет рассылку сообщения"""
    try:
        choice = update.message.text

        if choice == "Отмена":
            await update.message.reply_text(
                "Рассылка отменена.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        # Получаем всех пользователей
        users = db_instance.get_all_users()
        message_text = context.user_data.get('broadcast_text', '')

        if not message_text:
            await update.message.reply_text("Текст рассылки не найден.")
            return ConversationHandler.END

        # Отправляем сообщение всем пользователям
        success_count = 0
        fail_count = 0

        await update.message.reply_text(f"🔄 Начинаем рассылку для {len(users)} пользователей...")

        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user['telegram_id'],
                    text=f"<b>Важное сообщение</b>\n\n{message_text}",
                    parse_mode='HTML'
                )
                success_count += 1
                # Небольшая задержка чтобы не превысить лимиты Telegram
                await asyncio.sleep(0.1)

            except Exception as e:
                print(f"Не удалось отправить сообщение пользователю {user['telegram_id']}: {e}")
                fail_count += 1

        # Очищаем временные данные
        context.user_data.clear()

        await update.message.reply_text(
            f"<b>Рассылка завершена!</b>\n\n"
            f"• Успешно отправлено: {success_count}\n"
            f"• Не удалось отправить: {fail_count}",
            parse_mode='HTML',
            reply_markup=ReplyKeyboardRemove()
        )

        return ConversationHandler.END

    except Exception as e:
        print(f"Ошибка при отправке рассылки: {e}")
        await update.message.reply_text("Ошибка при отправке рассылки.")
        return ConversationHandler.END

async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отменяет административные действия"""
    context.user_data.clear()
    await update.message.reply_text(
        "Действие отменено.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END

async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает действия из админ-меню"""
    try:
        user = update.effective_user
        db_user = db_instance.get_user_by_telegram_id(user.id)

        if not db_user or not db_user['is_admin']:
            await update.message.reply_text("У вас нет прав администратора.")
            return

        text = update.message.text
        if text == "Статистика":
            await admin_statistics(update, context)
        elif text == "Все заявки":
            await admin_all_requests(update, context)
        elif text == "Все пользователи":
            await admin_all_users(update, context)
        elif text == "Выгрузка отчета":
            await export_report(update, context)
        elif text == "Рассылка":
            await broadcast_message(update, context)
        elif text == "Главное меню":
            await update.message.reply_text(
                "Возвращаемся в главное меню.",
                reply_markup=ReplyKeyboardRemove()
            )
        else:
            await update.message.reply_text("Неизвестная команда.")

    except Exception as e:
        print(f"Ошибка в обработчике админ-действий: {e}")
        await update.message.reply_text("Произошла ошибка.")

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

        # ConversationHandler для админ-аутентификации - ДОЛЖЕН БЫТЬ ПЕРВЫМ!
        admin_auth_conv_handler = ConversationHandler(
            entry_points=[CommandHandler('admin', admin_command)],
            states={
                WAITING_FOR_ADMIN_CODE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, verify_admin_code)
                ],
            },
            fallbacks=[CommandHandler('cancel', cancel_admin)],
        )

        # ConversationHandler для подачи заявки
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

        # ConversationHandler для просмотра заявок
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

        # ConversationHandler для выгрузки отчета
        report_conv_handler = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex('^Выгрузка отчета$'), export_report)],
            states={
                WAITING_FOR_REPORT_PERIOD: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, generate_report)
                ],
            },
            fallbacks=[CommandHandler('cancel', cancel_admin)],
        )

        # ConversationHandler для рассылки
        broadcast_conv_handler = ConversationHandler(
            entry_points=[MessageHandler(filters.Regex('^Рассылка$'), broadcast_message)],
            states={
                WAITING_FOR_BROADCAST: [
                    MessageHandler(filters.Regex('^(Отправить|Отмена)$'), send_broadcast),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_broadcast)
                ],
            },
            fallbacks=[CommandHandler('cancel', cancel_admin)],
        )

        # 1. ConversationHandler
        application.add_handler(admin_auth_conv_handler)
        application.add_handler(request_conv_handler)
        application.add_handler(view_requests_conv_handler)
        application.add_handler(report_conv_handler)
        application.add_handler(broadcast_conv_handler)

        # 2. CommandHandler
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("my_requests", my_requests))

        # 3. Обработчик инлайн-кнопок
        application.add_handler(CallbackQueryHandler(handle_inline_button))

        # 4. Обработчик для админ-меню (должен быть до общего обработчика)
        application.add_handler(MessageHandler(
            filters.Regex(
                '^(Статистика|Все заявки|Все пользователи|Выгрузка отчета|Рассылка|Главное меню)$'),
            handle_admin_actions
        ))

        # 5. Обработчик для любых других сообщений - ДОЛЖЕН БЫТЬ ПОСЛЕДНИМ
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_other_messages))

        # Запускаем бота
        print("Бот запущен...")
        application.run_polling()

    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
    finally:
        if db_instance:
            db_instance.disconnect()

async def handle_other_messages(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик любых текстовых сообщений кроме команд"""
    await update.message.reply_text(
        "Введите команду:\n"
        "/start, /submit_request, /my_requests"
    )

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
