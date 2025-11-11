from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler
import asyncio
from utils.helpers import format_datetime, _get_status_text

from handlers.states import (
    WAITING_FOR_TEXT, WAITING_FOR_LOCATION, SELECTING_REQUEST
)

# def format_datetime(dt_value):
#     """Универсальная функция для форматирования даты и времени"""
#     from datetime import datetime
#
#     if isinstance(dt_value, str):
#         formats = [
#             '%Y-%m-%d %H:%M:%S.%f',
#             '%Y-%m-%d %H:%M:%S',
#             '%Y-%m-%dT%H:%M:%S.%fZ',
#             '%Y-%m-%dT%H:%M:%SZ',
#             '%Y-%m-%d %H:%M:%S.%f000',
#             '%Y-%m-%d %H:%M:%S.%f',
#         ]
#
#         for fmt in formats:
#             try:
#                 dt_value = datetime.strptime(dt_value, fmt)
#                 break
#             except ValueError:
#                 continue
#         else:
#             return dt_value
#
#     if isinstance(dt_value, datetime):
#         return dt_value.strftime('%d.%m.%Y %H:%M')
#     return str(dt_value)

# Глобальная переменная для базы данных (будет установлена из main)

db_instance = None

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
            "Чтобы начать, используйте команду \n/submit_request"
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
                "Используйте /submit_request чтобы создать первую заявку.",
                reply_markup=ReplyKeyboardRemove()
            )
            return

        # Получаем заявки пользователя
        user_requests = db_instance.get_user_requests(db_user['id'])

        if not user_requests:
            await update.message.reply_text(
                "У вас пока нет заявок.\n\n"
                "Создайте первую заявку с помощью команды /submit_request",
                reply_markup=ReplyKeyboardRemove()
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

        await update.message.reply_text(message_text, parse_mode='HTML', reply_markup=ReplyKeyboardRemove())

        # Логируем запрос
        print(f"Пользователь {user.id} запросил список своих заявок. Найдено: {len(user_requests)} заявок")

    except Exception as e:
        print(f"Ошибка в команде /my_requests: {e}")
        await update.message.reply_text(
            "Произошла ошибка при получении списка заявок. Попробуйте позже."
        )

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

# Регистрация обработчиков для пользователя
def register_user_handlers(application):
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("my_requests", my_requests))
    application.add_handler(CallbackQueryHandler(handle_inline_button))

# Функция для установки экземпляра базы данных
def set_db_instance(db):
    global db_instance
    db_instance = db