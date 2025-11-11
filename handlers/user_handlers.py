from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler
import asyncio

from utils.helpers import format_datetime, _get_status_text
import re
import traceback

from handlers.states import (
    WAITING_FOR_TEXT, WAITING_FOR_LOCATION, SELECTING_REQUEST
)

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

async def handle_start_command_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обрабатывает кнопки, показанные после команды /start с параметром заявки"""
    try:
        user = update.effective_user
        text = update.message.text

        # Проверяем, находимся ли мы в режиме просмотра заявки из /start
        if not context.user_data.get('from_start_command'):
            # Если нет, передаем обработку другим обработчикам
            return

        # Получаем экземпляр БД из context.bot_data
        db = context.bot_data['db']

        # Проверяем права администратора
        db_user = db.get_user_by_telegram_id(user.id)
        if not db_user or not db_user['is_admin']:
            await update.message.reply_text("У вас нет прав администратора.")
            return

        # Проверяем, находимся ли мы в процессе изменения статуса
        if context.user_data.get('changing_status'):
            await admin_save_status_from_start(update, context)
            return

        # Проверяем, находимся ли мы в процессе ответа на заявку
        if context.user_data.get('replying_to_request'):
            await admin_save_reply_from_start(update, context)
            return

        # Получаем текущую заявку из context
        selected_request = context.user_data.get('selected_request')
        if not selected_request:
            await update.message.reply_text("Заявка не найдена в контексте.")
            return

        # Обрабатываем кнопки
        if text == "Изменить статус":
            await admin_change_status_from_start(update, context)
        elif text == "Ответить на заявку":
            await admin_reply_to_request_from_start(update, context)
        elif text == "К списку заявок":
            await admin_view_requests_from_start(update, context)
        elif text == "Главное меню":
            await show_admin_menu_from_start(update, context)
        else:
            await update.message.reply_text("Неизвестная команда.")

    except Exception as e:
        print(f"Ошибка при обработке кнопок из /start: {e}")
        await update.message.reply_text("Произошла ошибка при обработке команды.")

async def admin_change_status_from_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает доступные статусы для изменения из режима /start"""
    try:
        selected_request = context.user_data.get('selected_request')
        if not selected_request:
            await update.message.reply_text("Заявка не выбрана.")
            return

        keyboard = [
            ["Новая", "В обработке"],
            ["Завершена", "Отклонена"],
            ["Назад к заявке", "Главное меню"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            f"<b>Изменение статуса заявки {selected_request['request_number']}</b>\n\n"
            f"Текущий статус: <b>{_get_status_text(selected_request['status'])}</b>\n\n"
            "Выберите новый статус:",
            parse_mode='HTML',
            reply_markup=reply_markup
        )

        # Устанавливаем флаг, что мы в режиме изменения статуса
        context.user_data['changing_status'] = True

    except Exception as e:
        print(f"Ошибка при изменении статуса из /start: {e}")
        await update.message.reply_text("Ошибка при изменении статуса.")

async def admin_save_status_from_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сохраняет новый статус заявки из режима /start"""
    try:
        selected_request = context.user_data.get('selected_request')
        if not selected_request:
            await update.message.reply_text("Заявка не выбрана.")
            return

        status_text = update.message.text

        # Проверяем, не является ли это навигационной кнопкой
        if status_text in ["Назад к заявке", "Главное меню"]:
            # Сбрасываем флаг изменения статуса
            context.user_data['changing_status'] = False

            if status_text == "Назад к заявке":
                await show_request_by_number(update, context, selected_request['request_number'])
            else:
                await show_admin_menu_from_start(update, context)
            return

        status_map = {
            "Новая": "new",
            "В обработке": "in_progress",
            "Завершена": "completed",
            "Отклонена": "rejected"
        }

        new_status = status_map.get(status_text)
        if not new_status:
            await update.message.reply_text("Неверный статус.")
            return

        # Получаем экземпляр БД из context.bot_data
        db = context.bot_data['db']

        # Обновляем статус в БД
        success = db.update_request_status(selected_request['id'], new_status)

        if success:
            # Обновляем кэш
            selected_request['status'] = new_status
            context.user_data['selected_request'] = selected_request

            # Сбрасываем флаг изменения статуса
            context.user_data['changing_status'] = False

            await update.message.reply_text(
                f"Статус заявки {selected_request['request_number']} изменен на: {_get_status_text(new_status)}"
            )

            # Показываем обновленные детали
            await show_request_by_number(update, context, selected_request['request_number'])
        else:
            await update.message.reply_text("Ошибка при сохранении статуса.")

    except Exception as e:
        print(f"Ошибка при сохранении статуса из /start: {e}")
        await update.message.reply_text("Ошибка при сохранении статуса.")

async def admin_reply_to_request_from_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начинает процесс ответа на заявку из режима /start"""
    try:
        selected_request = context.user_data.get('selected_request')
        if not selected_request:
            await update.message.reply_text("Заявка не выбрана.")
            return

        # Создаем клавиатуру для выбора типа комментария
        keyboard = [
            ["Публичный комментарий", "Приватный комментарий"],
            ["Назад к заявке"]
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

        context.user_data['replying_to_request'] = True

    except Exception as e:
        print(f"Ошибка при начале ответа на заявку из /start: {e}")
        await update.message.reply_text("Ошибка при начале ответа.")

async def admin_save_reply_from_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Сохраняет ответ на заявку из режима /start"""
    try:
        selected_request = context.user_data.get('selected_request')
        if not selected_request:
            await update.message.reply_text("Заявка не выбрана.")
            return

        reply_text = update.message.text

        # Проверяем навигационные кнопки
        if reply_text == "Назад к заявке":
            # Сбрасываем флаг ответа на заявку
            context.user_data['replying_to_request'] = False
            await show_request_by_number(update, context, selected_request['request_number'])
            return

        # Проверяем, выбрал ли пользователь тип комментария
        if reply_text in ["Публичный комментарий", "Приватный комментарий"]:
            # Сохраняем тип комментария в context
            context.user_data['comment_is_public'] = (reply_text == "Публичный комментарий")

            await update.message.reply_text(
                "Введите текст комментария:",
                reply_markup=ReplyKeyboardMarkup([["Назад к заявке"]], resize_keyboard=True)
            )
            return

        # Если это текст комментария
        if 'comment_is_public' in context.user_data:
            # Получаем информацию об администраторе
            user = update.effective_user
            db = context.bot_data['db']
            db_user = db.get_user_by_telegram_id(user.id)

            if not db_user:
                await update.message.reply_text("Администратор не найден.")
                # Сбрасываем флаги
                context.user_data['replying_to_request'] = False
                if 'comment_is_public' in context.user_data:
                    del context.user_data['comment_is_public']
                return await show_request_by_number(update, context, selected_request['request_number'])

            # Получаем тип комментария из context
            is_public = context.user_data.get('comment_is_public', True)

            # Сохраняем комментарий в БД
            success = db.add_request_comment(
                selected_request['id'],
                db_user['id'],
                reply_text,
                is_public=is_public
            )

            if success:
                comment_type = "публичный" if is_public else "приватный"
                await update.message.reply_text(
                    f"{comment_type.capitalize()} комментарий к заявке {selected_request['request_number']} сохранен."
                )

                # Очищаем временные данные
                context.user_data['replying_to_request'] = False
                if 'comment_is_public' in context.user_data:
                    del context.user_data['comment_is_public']

                # Показываем обновленные детали
                await show_request_by_number(update, context, selected_request['request_number'])
            else:
                await update.message.reply_text("Ошибка при сохранении комментария.")

    except Exception as e:
        print(f"Ошибка при сохранении комментария из /start: {e}")
        await update.message.reply_text("Ошибка при сохранении комментария.")

async def admin_view_requests_from_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Переходит к просмотру всех заявок из режима /start"""
    try:
        # Очищаем флаг from_start_command
        if 'from_start_command' in context.user_data:
            del context.user_data['from_start_command']

        # Получаем экземпляр БД из context.bot_data
        db = context.bot_data['db']

        # Получаем все заявки
        all_requests = db.get_all_requests()
        context.user_data['all_requests'] = all_requests
        context.user_data['current_page'] = 0

        # Показываем первую страницу заявок
        from handlers import admin_view_requests
        await admin_view_requests(update, context, 0)

    except Exception as e:
        print(f"Ошибка при переходе к списку заявок из /start: {e}")
        await update.message.reply_text("Ошибка при загрузке заявок.")

async def show_admin_menu_from_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Показывает меню администратора из режима /start"""
    try:
        # Очищаем временные данные
        context.user_data.clear()

        keyboard = [
            ["Статистика", "Все заявки"],
            ["Все пользователи", "Выгрузка отчета"],
            ["Рассылка"]
        ]

        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

        await update.message.reply_text(
            "<b>Админ-панель</b>\n\n"
            "Выберите действие:",
            parse_mode='HTML',
            reply_markup=reply_markup
        )

        # Снимаем флаг from_start_command
        if 'from_start_command' in context.user_data:
            del context.user_data['from_start_command']

    except Exception as e:
        print(f"Ошибка в show_admin_menu_from_start: {e}")
        await update.message.reply_text(
            "<b>Админ-панель</b>",
            parse_mode='HTML'
        )

async def start_with_params(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /start с параметрами"""
    try:
        # Получаем параметры
        params = context.args
        user = update.effective_user

        print(f"Пользователь {user.id} ({user.username}) вызвал /start с параметрами: {params}")

        # Получаем экземпляр БД из context.bot_data
        db = context.bot_data['db']

        # Проверяем, есть ли параметры и является ли первый параметр номером заявки
        if params and len(params) > 0:
            request_number = params[0]

            # Проверяем формат номера заявки (например: 20251110-0002)
            if re.match(r'^\d{8}-\d{4}$', request_number):
                print(f"Обнаружен номер заявки в параметрах: {request_number}")

                # Проверяем, является ли пользователь администратором
                db_user = db.get_user_by_telegram_id(user.id)

                if db_user and db_user['is_admin']:
                    # Пользователь администратор - показываем заявку
                    await show_request_by_number(update, context, request_number)
                    return
                else:
                    # Пользователь не администратор
                    await update.message.reply_text(
                        "<b>Для просмотра заявок необходимо быть администратором</b>\n\n"
                        "Введите команду /admin и авторизуйтесь с помощью секретного кода.",
                        parse_mode='HTML',
                        reply_markup=ReplyKeyboardRemove()
                    )
                    return

        # Если параметров нет или это не номер заявки, показываем обычное приветствие
        await start(update, context)

    except Exception as e:
        print(f"Ошибка в команде /start с параметрами: {e}")
        await update.message.reply_text(
            "Произошла ошибка при обработке команды. Пожалуйста, попробуйте еще раз."
        )

async def show_request_by_number(update: Update, context: ContextTypes.DEFAULT_TYPE, request_number: str) -> None:
    """Показывает заявку по номеру для администратора"""
    try:
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
                reply_markup=ReplyKeyboardRemove()
            )
            return

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

        # Сохраняем заявку в context для использования в других функциях
        context.user_data['selected_request'] = selected_request
        context.user_data['from_start_command'] = True  # Флаг, что пришли из команды /start

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

        # Создаем клавиатуру с действиями (такая же, как в админ-панели)
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

        # Если есть видео, отправляем информацию о нем
        if selected_request['video_url']:
            try:
                await update.message.reply_video(
                    video=selected_request['video_url'],
                    caption=f"Видео к заявке {selected_request['request_number']}"
                )
            except Exception as e:
                print(f"Не удалось отправить видео: {e}")

    except Exception as e:
        print(f"Ошибка при показе заявки по номеру: {e}")
        await update.message.reply_text(
            "Ошибка при загрузке заявки.",
            reply_markup=ReplyKeyboardRemove()
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
        user = update.effective_user
        message = update.message

        # Получаем координаты
        latitude = message.location.latitude
        longitude = message.location.longitude

        # Создаем заявку в БД
        db_user = context.bot_data['db'].get_user_by_telegram_id(user.id)
        if not db_user:
            # Создаем пользователя если не существует
            user_id = context.bot_data['db'].create_user(
                telegram_id=user.id,
                username=user.username,
                full_name=user.full_name
            )
            db_user = context.bot_data['db'].get_user_by_telegram_id(user.id)

        request_info = context.bot_data['db'].create_request(
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
        user = update.effective_user
        message = update.message

        # Создаем заявку в БД без геолокации
        db_user = context.bot_data['db'].get_user_by_telegram_id(user.id)
        if not db_user:
            # Создаем пользователя если не существует
            user_id = context.bot_data['db'].create_user(
                telegram_id=user.id,
                username=user.username,
                full_name=user.full_name
            )
            db_user = context.bot_data['db'].get_user_by_telegram_id(user.id)

        request_info = context.bot_data['db'].create_request(
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
        user = update.effective_user

        # Получаем пользователя из БД
        db_user = context.bot_data['db'].get_user_by_telegram_id(user.id)
        if not db_user:
            await update.message.reply_text(
                "Вы еще не создавали заявок.\n"
                "Используйте /submit_request чтобы создать первую заявку.",
                reply_markup=ReplyKeyboardRemove()
            )
            return

        # Получаем заявки пользователя
        user_requests = context.bot_data['db'].get_user_requests(db_user['id'])

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
        user = update.effective_user

        # Получаем пользователя из БД
        db_user = context.bot_data['db'].get_user_by_telegram_id(user.id)
        if not db_user:
            await update.message.reply_text(
                "У вас пока нет заявок.\n"
                "Создайте первую заявку с помощью /submit_request"
            )
            return ConversationHandler.END

        # Получаем заявки пользователя
        user_requests = context.bot_data['db'].get_user_requests(db_user['id'])

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
        user = query.from_user

        # Получаем пользователя из БД
        db_user = context.bot_data['db'].get_user_by_telegram_id(user.id)
        if not db_user:
            await query.edit_message_text("Ошибка: пользователь не найден.")
            return

        # Пытаемся отменить заявку
        success = context.bot_data['db'].cancel_request(request_id, db_user['id'])

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
