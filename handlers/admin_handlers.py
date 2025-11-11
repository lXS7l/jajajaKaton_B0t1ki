from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, MessageHandler, filters

from utils.helpers import format_datetime, _get_status_text
import asyncio
from datetime import datetime

# Импорты состояний
from handlers.states import (
    WAITING_FOR_ADMIN_CODE, WAITING_FOR_BROADCAST, WAITING_FOR_REPORT_PERIOD,
    ADMIN_VIEW_REQUESTS, ADMIN_VIEW_REQUEST_DETAIL, ADMIN_CHANGE_STATUS,
    ADMIN_REPLY_TO_REQUEST, ADMIN_SELECT_REQUEST
)

async def handle_admin_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает действия из админ-меню"""
    try:
        user = update.effective_user
        db_user = context.bot_data['db'].get_user_by_telegram_id(user.id)

        if not db_user or not db_user['is_admin']:
            await update.message.reply_text("У вас нет прав администратора.")
            return

        text = update.message.text

        # Очищаем флаг from_start_command при переходе между разделами
        if 'from_start_command' in context.user_data:
            del context.user_data['from_start_command']

        if text == "Статистика":
            await admin_statistics(update, context)
        elif text == "Все заявки":
            await admin_view_requests(update, context, 0)
        elif text == "Все пользователи":
            await admin_all_users(update, context)
        elif text == "Выгрузка отчета":
            await export_report(update, context)
        elif text == "Рассылка":
            await broadcast_message(update, context)
        elif text == "Главное меню":
            await show_admin_menu(update, context)
        elif text == "К списку заявок":
            # Если пришли из команды /start, возвращаем в главное меню
            if context.user_data.get('from_start_command'):
                await show_admin_menu(update, context)
            else:
                await admin_view_requests(update, context, context.user_data.get('current_page', 0))
        else:
            await update.message.reply_text("Неизвестная команда.")

    except Exception as e:
        print(f"Ошибка в обработчике админ-действий: {e}")
        await update.message.reply_text("Произошла ошибка.")

async def admin_return_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Возвращает в главное меню администратора и завершает текущий ConversationHandler"""
    # Очищаем флаг from_start_command
    if 'from_start_command' in context.user_data:
        del context.user_data['from_start_command']

    await show_admin_menu(update, context)
    return ConversationHandler.END

async def admin_view_requests(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0) -> int:
    """Показывает заявки с пагинацией"""
    try:
        user = update.effective_user
        db_user = context.bot_data['db'].get_user_by_telegram_id(user.id)

        if not db_user or not db_user['is_admin']:
            await update.message.reply_text("У вас нет прав администратора.")
            return ConversationHandler.END

        # Получаем все заявки
        all_requests = context.bot_data['db'].get_all_requests()

        if not all_requests:
            await update.message.reply_text(
                "Заявок пока нет.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END

        # Сохраняем заявки в context для использования в других функциях
        context.user_data['all_requests'] = all_requests
        context.user_data['current_page'] = page

        items_per_page = 10
        total_pages = (len(all_requests) + items_per_page - 1) // items_per_page

        # Получаем заявки для текущей страницы
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        page_requests = all_requests[start_idx:end_idx]

        # Создаем клавиатуру с заявками и навигацией
        keyboard = []

        # Добавляем заявки текущей страницы
        for i, req in enumerate(page_requests, start_idx + 1):
            short_text = req['request_text'][:30] + "..." if len(req['request_text']) > 30 else req['request_text']
            button_text = f"{i}. {req['request_number']} - {_get_status_text(req['status'])}"
            keyboard.append([button_text])

        # Добавляем навигацию
        nav_buttons = []
        if page > 0:
            nav_buttons.append("Назад")
        if page < total_pages - 1:
            nav_buttons.append("Вперед")

        if nav_buttons:
            keyboard.append(nav_buttons)

        keyboard.append(["Поиск по номеру", "Статистика"])
        keyboard.append(["Главное меню"])

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        # Формируем сообщение
        message_text = (
            f"<b>Заявки (страница {page + 1}/{total_pages})</b>\n\n"
            f"Всего заявок: {len(all_requests)}\n"
            f"Показано: {len(page_requests)}\n\n"
            "Выберите заявку для просмотра деталей:"
        )

        if update.callback_query:
            await update.callback_query.edit_message_text(message_text, parse_mode='HTML', reply_markup=reply_markup)
        else:
            await update.message.reply_text(message_text, parse_mode='HTML', reply_markup=reply_markup)

        return ADMIN_VIEW_REQUESTS

    except Exception as e:
        print(f"Ошибка при показе заявок с пагинацией: {e}")
        await update.message.reply_text("Ошибка при загрузке заявок.")
        return ConversationHandler.END

async def admin_handle_pagination(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает навигацию по страницам"""
    try:
        text = update.message.text
        current_page = context.user_data.get('current_page', 0)

        if text == "Назад":
            new_page = current_page - 1
        elif text == "Вперед":
            new_page = current_page + 1
        else:
            return await admin_view_requests(update, context, current_page)

        # Сохраняем текущую страницу
        context.user_data['current_page'] = new_page

        return await admin_view_requests(update, context, new_page)

    except Exception as e:
        print(f"Ошибка при пагинации: {e}")
        return await admin_view_requests(update, context, 0)

async def admin_view_request_detail(update: Update, context: ContextTypes.DEFAULT_TYPE, from_comment: bool = False) -> int:
    """Показывает детали выбранной заявки"""
    try:
        if from_comment:
            # Просто показываем детали, не обрабатывая ввод
            selected_request = context.user_data.get('selected_request')
        else:
            user = update.effective_user
            text = update.message.text

            # Проверяем, не является ли это командой навигации
            if text in ["Назад", "Вперед", "Все заявки", "Поиск по номеру", "Статистика", "Главное меню"]:
                return ADMIN_VIEW_REQUESTS

            # Извлекаем номер заявки из текста (формат: "1. 20240101-0001 - Новая")
            request_number = None
            if '. ' in text and ' - ' in text:
                try:
                    # Более надежное извлечение номера заявки
                    parts = text.split('. ', 1)
                    if len(parts) > 1:
                        request_info = parts[1]  # "20240101-0001 - Новая"
                        request_number = request_info.split(' - ')[0]  # "20240101-0001"
                except Exception as e:
                    request_number = text.strip()
            else:
                # Если это прямой ввод номера заявки
                request_number = text.strip()

            # Ищем заявку в кэше
            all_requests = context.user_data.get('all_requests', [])
            selected_request = None

            # Поиск по номеру заявки в кэше
            for req in all_requests:
                if req['request_number'] == request_number:
                    selected_request = req
                    break

            if not selected_request:
                # Если не нашли в кэше, ищем в БД
                cursor = context.bot_data['db'].connection.cursor()
                cursor.execute("""
                    SELECT 
                        r.id, r.request_number, r.request_text, r.status, 
                        r.photo_url, r.video_url, r.latitude, r.longitude,
                        r.created_at, r.updated_at,
                        u.full_name, u.username, u.phone_number
                    FROM requests r
                    LEFT JOIN users u ON r.user_id = u.id
                    WHERE r.request_number = ?
                """, request_number)

                row = cursor.fetchone()
                if row:
                    selected_request = {
                        'id': row[0],
                        'request_number': row[1],
                        'request_text': row[2],
                        'status': row[3],
                        'photo_url': row[4],
                        'video_url': row[5],
                        'latitude': row[6],
                        'longitude': row[7],
                        'created_at': row[8],
                        'updated_at': row[9],
                        'user_full_name': row[10],
                        'user_username': row[11],
                        'user_phone_number': row[12]
                    }

            if not selected_request:
                await update.message.reply_text(
                    f"Заявка '{request_number}' не найдена.",
                    reply_markup=ReplyKeyboardRemove()
                )
                return await admin_view_requests(update, context, context.user_data.get('current_page', 0))

        # ВАЖНО: Сохраняем выбранную заявку в context
        context.user_data['selected_request'] = selected_request

        # Получаем комментарии к заявке
        comments = context.bot_data['db'].get_request_comments(selected_request['id'])

        # Форматируем даты
        created_date = format_datetime(selected_request['created_at'])
        updated_date = format_datetime(selected_request['updated_at'])

        # Информация о пользователе
        user_info = selected_request.get('user_full_name') or selected_request.get('user_username') or 'Аноним'
        phone_info = selected_request.get('user_phone_number') or 'Не указан'

        # Формируем сообщение с деталями
        detail_text = (
            f"<b>Заявка {selected_request['request_number']}</b>\n\n"
            f"<b>Пользователь:</b> {user_info}\n"
            f"<b>Телефон:</b> {phone_info}\n"
            f"<b>️Статус:</b> {_get_status_text(selected_request['status'])}\n"
            f"<b>Создана:</b> {created_date}\n"
            f"<b>Обновлена:</b> {updated_date}\n\n"
            f"<b>Описание:</b>\n{selected_request['request_text']}\n\n"
        )

        # Добавляем комментарии если есть
        if comments:
            detail_text += "<b>Комментарии:</b>\n"
            for i, comment in enumerate(comments, 1):
                comment_date = format_datetime(comment['created_at'])
                admin_name = comment['admin_name'] or 'Администратор'
                detail_text += f"{i}. {comment_date} - {admin_name}:\n"
                detail_text += f"   {comment['comment_text']}\n\n"
        else:
            detail_text += "<b>Комментарии:</b> нет\n\n"

        # Добавляем информацию о медиа
        if selected_request['photo_url']:
            detail_text += "<b>Прикреплено фото</b>\n"
        if selected_request['video_url']:
            detail_text += "<b>Прикреплено видео</b>\n"

        # Добавляем информацию о геолокации
        if selected_request['latitude'] and selected_request['longitude']:
            lat = selected_request['latitude']
            lon = selected_request['longitude']
            detail_text += f"<b>Координаты:</b> {lat:.6f}, {lon:.6f}\n"
            detail_text += f"<a href='https://yandex.ru/maps/?ll={lon},{lat}&z=19'>Открыть на карте</a>\n"

        # Создаем клавиатуру с действиями
        keyboard = [
            ["Изменить статус", "Ответить на заявку"],
            ["К списку заявок", "Главное меню"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(detail_text, parse_mode='HTML', reply_markup=reply_markup)

        # Если есть фото, отправляем его
        if selected_request['photo_url']:
            try:
                await update.message.reply_photo(
                    photo=selected_request['photo_url'],
                    caption=f"Фото к заявке {selected_request['request_number']}"
                )
            except Exception as e:
                print(f"Не удалось отправить фото: {e}")

        return ADMIN_VIEW_REQUEST_DETAIL

    except Exception as e:
        print(f"Ошибка при показе деталей заявки: {e}")
        await update.message.reply_text("Ошибка при загрузке деталей заявки.")
        return await admin_view_requests(update, context, context.user_data.get('current_page', 0))

async def admin_change_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает доступные статусы для изменения"""
    try:
        if not _ensure_selected_request(context):
            await update.message.reply_text("Заявка не выбрана.")
            return await admin_view_requests(update, context, 0)

        selected_request = context.user_data['selected_request']

        keyboard = [
            ["Новая", "В обработке"],
            ["Завершена", "Отклонена"],
            ["К деталям заявки", "Главное меню"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            f"<b>Изменение статуса заявки {selected_request['request_number']}</b>\n\n"
            f"Текущий статус: <b>{_get_status_text(selected_request['status'])}</b>\n\n"
            "Выберите новый статус:",
            parse_mode='HTML',
            reply_markup=reply_markup
        )

        return ADMIN_CHANGE_STATUS

    except Exception as e:
        print(f"Ошибка при изменении статуса: {e}")
        await update.message.reply_text("Ошибка при изменении статуса.")
        return ConversationHandler.END

async def admin_save_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохраняет новый статус заявки"""
    try:
        selected_request = context.user_data.get('selected_request')
        if not selected_request:
            await update.message.reply_text("Заявка не выбрана.")
            return await admin_view_requests(update, context, 0)

        status_text = update.message.text
        status_map = {
            "Новая": "new",
            "В обработке": "in_progress",
            "Завершена": "completed",
            "Отклонена": "rejected"
        }

        new_status = status_map.get(status_text)
        if not new_status:
            await update.message.reply_text("Неверный статус.")
            return await admin_change_status(update, context)

        # Обновляем статус в БД
        success = context.bot_data['db'].update_request_status(selected_request['id'], new_status)

        if success:
            await update.message.reply_text(
                f"Статус заявки {selected_request['request_number']} изменен на: {_get_status_text(new_status)}",
                reply_markup=ReplyKeyboardRemove()
            )

            # Обновляем кэш
            selected_request['status'] = new_status

            # Показываем обновленные детали
            context.user_data['selected_request'] = selected_request
            return await admin_view_request_detail(update, context)
        else:
            await update.message.reply_text("Ошибка при сохранении статуса.")
            return await admin_change_status(update, context)

    except Exception as e:
        print(f"Ошибка при сохранении статуса: {e}")
        await update.message.reply_text("Ошибка при сохранении статуса.")
        return ConversationHandler.END

async def admin_reply_to_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс ответа на заявку"""
    try:
        selected_request = context.user_data.get('selected_request')
        if not selected_request:
            # Попробуем получить из других источников
            if 'current_request' in context.user_data:
                selected_request = context.user_data['current_request']
                context.user_data['selected_request'] = selected_request

        if not selected_request:
            await update.message.reply_text("Заявка не выбрана.")
            return await admin_view_requests(update, context, 0)

        # Создаем клавиатуру для выбора типа комментария
        keyboard = [
            ["Публичный комментарий", "Приватный комментарий"],
            ["Отмена"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            f"<b>Ответ на заявку {selected_request['request_number']}</b>\n\n"
            "Выберите тип комментария:\n"
            "• Публичный - виден пользователю\n"
            "• Приватный - виден только администраторам",
            parse_mode='HTML',
            reply_markup=reply_markup
        )

        return ADMIN_REPLY_TO_REQUEST

    except Exception as e:
        print(f"Ошибка при начале ответа на заявку: {e}")
        await update.message.reply_text("Ошибка при начале ответа.")
        return ConversationHandler.END

async def admin_choose_comment_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает выбор типа комментария"""
    try:
        comment_type = update.message.text

        if comment_type == "Отмена":
            return await admin_view_request_detail(update, context)

        # Сохраняем тип комментария в context
        if comment_type == "Публичный комментарий":
            context.user_data['comment_is_public'] = True
        elif comment_type == "Приватный комментарий":
            context.user_data['comment_is_public'] = False
        else:
            await update.message.reply_text("Неверный тип комментария.")
            return await admin_reply_to_request(update, context)

        await update.message.reply_text(
            "Введите текст комментария:",
            reply_markup=ReplyKeyboardMarkup([["Отмена"]], resize_keyboard=True)
        )

        return ADMIN_REPLY_TO_REQUEST

    except Exception as e:
        print(f"Ошибка при выборе типа комментария: {e}")
        await update.message.reply_text("Ошибка при выборе типа комментария.")
        return ConversationHandler.END

async def admin_save_reply(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохраняет ответ на заявку"""
    try:
        selected_request = context.user_data.get('selected_request')
        if not selected_request:
            await update.message.reply_text("Заявка не выбрана.")
            return await admin_view_requests(update, context, 0)

        reply_text = update.message.text

        if reply_text == "Отмена":
            return await admin_view_request_detail(update, context)

        # Получаем информацию об администраторе
        user = update.effective_user
        db_user = context.bot_data['db'].get_user_by_telegram_id(user.id)
        if not db_user:
            await update.message.reply_text("Администратор не найден.")
            return await admin_view_request_detail(update, context)

        # Получаем тип комментария из context
        is_public = context.user_data.get('comment_is_public', True)

        # Сохраняем комментарий в БД
        success = context.bot_data['db'].add_request_comment(
            selected_request['id'],
            db_user['id'],
            reply_text,
            is_public=is_public
        )

        if success:
            comment_type = "публичный" if is_public else "приватный"
            await update.message.reply_text(
                f"{comment_type.capitalize()} комментарий к заявке {selected_request['request_number']} сохранен.",
                reply_markup=ReplyKeyboardRemove()
            )

            # Очищаем временные данные
            if 'comment_is_public' in context.user_data:
                del context.user_data['comment_is_public']

            # Показываем обновленные детали
            return await admin_view_request_detail(update, context)
        else:
            await update.message.reply_text("Ошибка при сохранении комментария.")
            return await admin_reply_to_request(update, context)

    except Exception as e:
        print(f"Ошибка при сохранении комментария: {e}")
        await update.message.reply_text("Ошибка при сохранении комментария.")
        return ConversationHandler.END

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /admin - запрашивает код администратора"""
    try:
        user = update.effective_user

        # Проверяем, не является ли пользователь уже администратором
        db_user = context.bot_data['db'].get_user_by_telegram_id(user.id)
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
        db_user = context.bot_data['db'].get_user_by_telegram_id(user.id)
        if not db_user:
            await update.message.reply_text("Пользователь не найден в базе данных.")
            return ConversationHandler.END

        # ПЕРЕДАЕМ TELEGRAM_ID, а не внутренний ID!
        success = context.bot_data['db'].verify_admin_code(code, user.id)

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
    """Показывает меню администратора с кнопками"""
    try:
        # Очищаем временные данные
        context.user_data.clear()

        keyboard = [
            ["Статистика", "Все заявки"],
            ["Все пользователи", "Выгрузка отчета"],
            ["Рассылка", "Главное меню"]
        ]

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        if update.callback_query:
            await update.callback_query.message.reply_text(
                "<b>Админ-панель</b>\n\n"
                "Выберите действие:",
                parse_mode='HTML',
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "<b>Админ-панель</b>\n\n"
                "Выберите действие:",
                parse_mode='HTML',
                reply_markup=reply_markup
            )

    except Exception as e:
        print(f"Ошибка в show_admin_menu: {e}")
        # Без кнопок
        if update.callback_query:
            await update.callback_query.message.reply_text(
                "<b>Админ-панель</b>",
                parse_mode='HTML'
            )
        else:
            await update.message.reply_text(
                "<b>Админ-панель</b>",
                parse_mode='HTML'
            )

async def admin_statistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает статистику для администратора"""
    try:
        # Проверяем права администратора
        user = update.effective_user
        db_user = context.bot_data['db'].get_user_by_telegram_id(user.id)

        if not db_user or not db_user['is_admin']:
            await update.message.reply_text("У вас нет прав администратора.")
            return

        # Получаем статистику
        all_requests = context.bot_data['db'].get_all_requests()
        all_users = context.bot_data['db'].get_all_users()

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
        db_user = context.bot_data['db'].get_user_by_telegram_id(user.id)

        if not db_user or not db_user['is_admin']:
            await update.message.reply_text("У вас нет прав администратора.")
            return

        # Получаем заявки
        requests = context.bot_data['db'].get_all_requests(limit=20)  # Ограничиваем для удобства

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
        db_user = context.bot_data['db'].get_user_by_telegram_id(user.id)

        if not db_user or not db_user['is_admin']:
            await update.message.reply_text("У вас нет прав администратора.")
            return

        # Получаем пользователей
        users = context.bot_data['db'].get_all_users()

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
        db_user = context.bot_data['db'].get_user_by_telegram_id(user.id)

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
        requests = context.bot_data['db'].get_all_requests(days=days)

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
        db_user = context.bot_data['db'].get_user_by_telegram_id(user.id)

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
        users = context.bot_data['db'].get_all_users()
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

async def admin_search_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс поиска заявки по номеру"""
    try:
        await update.message.reply_text(
            "<b>Поиск заявки по номеру</b>\n\n"
            "Введите номер заявки (например: 20240101-0001):",
            parse_mode='HTML',
            reply_markup=ReplyKeyboardMarkup([["Отмена"]], resize_keyboard=True)
        )

        return ADMIN_SELECT_REQUEST

    except Exception as e:
        print(f"Ошибка при поиске заявки: {e}")
        await update.message.reply_text("Ошибка при поиске.")
        return ConversationHandler.END

async def admin_handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает поиск заявки по номеру"""
    try:
        request_number = update.message.text

        if request_number == "Отмена":
            return await admin_view_requests(update, context, 0)

        # Ищем заявку в БД
        cursor = context.bot_data['db'].connection.cursor()
        cursor.execute("""
            SELECT 
                r.id, r.request_number, r.request_text, r.status, 
                r.photo_url, r.video_url, r.latitude, r.longitude,
                r.created_at, r.updated_at,
                u.full_name, u.username, u.phone_number
            FROM requests r
            LEFT JOIN users u ON r.user_id = u.id
            WHERE r.request_number = ?
        """, request_number)

        row = cursor.fetchone()
        if not row:
            await update.message.reply_text(
                f"Заявка с номером {request_number} не найдена.",
                reply_markup=ReplyKeyboardMarkup([["Повторить поиск", "К списку заявок"]], resize_keyboard=True)
            )
            return ADMIN_SELECT_REQUEST

        selected_request = {
            'id': row[0],
            'request_number': row[1],
            'request_text': row[2],
            'status': row[3],
            'photo_url': row[4],
            'video_url': row[5],
            'latitude': row[6],
            'longitude': row[7],
            'created_at': row[8],
            'updated_at': row[9],
            'user_full_name': row[10],
            'user_username': row[11],
            'user_phone_number': row[12]
        }

        # Сохраняем заявку в context
        context.user_data['selected_request'] = selected_request

        # Показываем детали
        return await admin_view_request_detail(update, context)

    except Exception as e:
        print(f"Ошибка при обработке поиска: {e}")
        await update.message.reply_text("Ошибка при поиске заявки.")
        return ConversationHandler.END

def _ensure_selected_request(context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Проверяет и восстанавливает selected_request если нужно"""
    if 'selected_request' in context.user_data:
        return True

    # Попробуем найти заявку в других местах
    if 'current_request' in context.user_data:
        context.user_data['selected_request'] = context.user_data['current_request']
        return True

    # Попробуем найти в all_requests по current_page
    if 'all_requests' in context.user_data and 'current_page' in context.user_data:
        all_requests = context.user_data['all_requests']
        current_page = context.user_data['current_page']
        items_per_page = 10
        start_idx = current_page * items_per_page

        if start_idx < len(all_requests):
            # Берем первую заявку со страницы
            context.user_data['selected_request'] = all_requests[start_idx]
            return True

    return False

# Регистрация обработчиков для администратора
def register_admin_handlers(application):
    application.add_handler(MessageHandler(
        filters.Regex('^(Статистика|Все заявки|Все пользователи|Выгрузка отчета|Рассылка|Главное меню)$'),
        handle_admin_actions
    ))