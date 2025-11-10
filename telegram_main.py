import asyncio
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import os
from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv
from DatabaseManager import DatabaseManager

# Загружаем переменные окружения из .env файла
load_dotenv()
WAITING_FOR_TEXT, WAITING_FOR_LOCATION = range(2)

# Получаем токен бота из переменной окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("Не задан BOT_TOKEN в .env файле")

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
    """Обработчик команды /my_requests"""
    await update.message.reply_text(
        "Раздел моих заявок в разработке.\n"
        "Здесь будет список ваших заявок."
    )

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
                    MessageHandler(filters.Regex('Без геолокации$'), skip_location)
                ],
            },
            fallbacks=[CommandHandler('cancel', cancel_submit)],
        )

        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(request_conv_handler)
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
