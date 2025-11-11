from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, filters
from handlers.states import (
    WAITING_FOR_TEXT, WAITING_FOR_LOCATION, SELECTING_REQUEST,
    WAITING_FOR_ADMIN_CODE, WAITING_FOR_BROADCAST, WAITING_FOR_REPORT_PERIOD,
    ADMIN_VIEW_REQUESTS, ADMIN_VIEW_REQUEST_DETAIL, ADMIN_CHANGE_STATUS,
    ADMIN_REPLY_TO_REQUEST, ADMIN_SELECT_REQUEST
)

# Импорты обработчиков пользователя
from handlers.user_handlers import (
    submit_request, receive_request_text, receive_location, skip_location,
    cancel_submit, request_details, show_selected_request, handle_navigation,
    cancel_request_selection
)

# Импорты обработчиков администратора - ВСЕ необходимые функции
from handlers.admin_handlers import (
    admin_command, verify_admin_code, cancel_admin, export_report,
    generate_report, broadcast_message, confirm_broadcast, send_broadcast,
    admin_view_requests, admin_handle_pagination, admin_view_request_detail,
    admin_change_status, admin_save_status, admin_reply_to_request,
    admin_choose_comment_type, admin_save_reply, admin_search_request,
    admin_handle_search, admin_statistics, show_admin_menu  # ДОБАВЛЕНО!
)

def get_conversation_handlers():
    # ConversationHandler для админ-аутентификации
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

    # ConversationHandler для админ-панели (управление заявками)
    admin_requests_conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex('^Все заявки$'),
                           lambda update, context: admin_view_requests(update, context, 0)),
            MessageHandler(filters.Regex('^Поиск по номеру$'), admin_search_request)
        ],
        states={
            ADMIN_VIEW_REQUESTS: [
                MessageHandler(filters.Regex('^(Назад|Вперед|Все заявки)$'), admin_handle_pagination),
                MessageHandler(filters.Regex('^Поиск по номеру$'), admin_search_request),
                MessageHandler(filters.Regex('^Статистика$'), admin_statistics),  # ЭТА СТРОКА ВЫЗЫВАЛА ОШИБКУ
                MessageHandler(filters.Regex('^Главное меню$'),
                               lambda update, context: show_admin_menu(update, context)),
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_view_request_detail)
            ],
            ADMIN_VIEW_REQUEST_DETAIL: [
                MessageHandler(filters.Regex('^Изменить статус$'), admin_change_status),
                MessageHandler(filters.Regex('^Ответить на заявку$'), admin_reply_to_request),
                MessageHandler(filters.Regex('^К списку заявок$'),
                               lambda update, context: admin_view_requests(update, context,
                                                                           context.user_data.get('current_page',
                                                                                                 0))),
                MessageHandler(filters.Regex('^Главное меню$'),
                               lambda update, context: show_admin_menu(update, context))
            ],
            ADMIN_CHANGE_STATUS: [
                MessageHandler(filters.Regex('^(Новая|В обработке|Завершена|Отклонена)$'),
                               admin_save_status),
                MessageHandler(filters.Regex('^К деталям заявки$'), admin_view_request_detail),
                MessageHandler(filters.Regex('^Главное меню$'),
                               lambda update, context: show_admin_menu(update, context))
            ],
            ADMIN_REPLY_TO_REQUEST: [
                MessageHandler(filters.Regex('^(Публичный комментарий|Приватный комментарий)$'),
                               admin_choose_comment_type),
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_save_reply)
            ],
            ADMIN_SELECT_REQUEST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_handle_search),
                MessageHandler(filters.Regex('^(Повторить поиск|К списку заявок)$'),
                               lambda update, context: admin_view_requests(update, context, 0))
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel_admin)],
        map_to_parent={
            ConversationHandler.END: SELECTING_REQUEST
        }
    )

    return [
        admin_requests_conv_handler,
        admin_auth_conv_handler,
        request_conv_handler,
        view_requests_conv_handler,
        report_conv_handler,
        broadcast_conv_handler
    ]