import os
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler

# Импорты из наших модулей
from utils.database import DatabaseManager
from handlers.user_handlers import (
    start_with_params, my_requests, handle_inline_button,
    handle_start_command_buttons
)
from handlers.admin_handlers import (
    handle_admin_actions
)
from handlers.conversation_handlers import get_conversation_handlers
from utils.helpers import handle_other_messages

load_dotenv()

def main() -> None:
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

        # СНАЧАЛА добавляем ConversationHandler
        for conv_handler in get_conversation_handlers():
            application.add_handler(conv_handler)

        # ПОТОМ добавляем обычные обработчики команд
        application.add_handler(CommandHandler("start", start_with_params))
        application.add_handler(CommandHandler("my_requests", my_requests))
        application.add_handler(CallbackQueryHandler(handle_inline_button))

        # Обработчик для админ-меню (должен быть ПОСЛЕ ConversationHandler)
        application.add_handler(MessageHandler(
            filters.Regex('^(Статистика|Все заявки|Все пользователи|Выгрузка отчета|Рассылка|Главное меню)$'),
            handle_admin_actions
        ))

        # ОБНОВЛЕННЫЙ ОБРАБОТЧИК: для всех сообщений в режиме /start с параметром
        # Этот обработчик должен проверять флаг from_start_command в context.user_data
        application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_start_command_buttons
        ))

        # Обработчик для любых других сообщений (должен быть ПОСЛЕДНИМ)
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_other_messages))

        # Запускаем бота
        print("Бот запущен...")
        application.run_polling()

    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")
    finally:
        if db_instance:
            db_instance.disconnect()

if __name__ == "__main__":
    main()