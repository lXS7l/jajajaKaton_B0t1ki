import asyncio
import os
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv
from DatabaseManager import DatabaseManager

# Загружаем переменные окружения из .env файла
load_dotenv()

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


async def submit_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /submit_request"""
    await update.message.reply_text(
        "Раздел подачи заявки в разработке.\n"
        "Здесь будет форма для заполнения заявки."
    )


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


def main() -> None:
    """Основная функция запуска бота"""
    # Создаем приложение и передаем ему токен
    application = Application.builder().token(BOT_TOKEN).build()

    # Создаем экземпляр базы данных
    db = DatabaseManager()
    db.connect()

    try:
        # Создаем приложение бота
        application = Application.builder().token(BOT_TOKEN).build()

        # Сохраняем экземпляр БД в bot_data для доступа из обработчиков
        application.bot_data['db'] = db

        # Добавляем обработчики команд
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("submit_request", submit_request))
        application.add_handler(CommandHandler("my_requests", my_requests))

        # Запускаем бота
        print("Бот запущен...")
        application.run_polling()
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
    finally:
        db.disconnect()


if __name__ == "__main__":
    main()
