import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем токен бота из переменной окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("Не задан BOT_TOKEN в .env файле")

# Обработчики команд
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start"""
    await update.message.reply_text(
        "Привет! Я бот-помощник. Вот доступные команды:\n"
        "/start - показать приветствие\n"
        "/submit_request - подать заявку\n"
        "/my_requests - посмотреть мои заявки"
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

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("submit_request", submit_request))
    application.add_handler(CommandHandler("my_requests", my_requests))

    # Добавляем обработчик для любых текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_other_messages))
    # Запускаем бота
    application.run_polling()


if __name__ == "__main__":
    main()
