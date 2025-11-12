# Бот-помощник 112 - Система оперативного реагирования

Современная система для приема и обработки городских заявок от жителей с двумя интерфейсами: Telegram-бот для граждан и desktop-приложение для операторов.

## Возможности

### Для жителей (Telegram-бот)
- **Подача заявок** - текст, фото, видео, геолокация
- **Отслеживание статусов** - история обращений
- **Мгновенные уведомления** - смена статусов, комментарии
- **Отмена заявок** - для незавершенных обращений

### Для операторов (2 интерфейса)

#### Telegram (базовый)
- **Просмотр заявок** - списком с пагинацией
- **Управление статусами** - новая/в обработке/завершена
- **Комментарии** - публичные и приватные
- **Статистика** - общая по системе

#### Desktop-приложение (расширенный)
- **Интерактивная карта** - кластеризация заявок на Яндекс Картах
- **Визуальная галерея** - просмотр всех фото с пагинацией
- **Расширенная фильтрация** - по статусу, дате, тексту
- **Детальная аналитика** - фильтры и поиск
- **Интеграция с ботом** - глубокие ссылки на заявки

## Технологический стек

**Backend & Бот:**
- Python 3.8+
- python-telegram-bot 20.0+
- pyodbc - подключение к SQL Server
- python-dotenv - управление конфигурацией

**Desktop-приложение:**
- C# .NET Framework 4.7.2
- WinForms - графический интерфейс
- WebView2 - интеграция Яндекс.Карт
- System.Data.SqlClient - работа с БД

**База данных:**
- Microsoft SQL Server
- Единая схема для обоих приложений

## Установка и настройка

### Предварительные требования
- SQL Server (Express или выше)
- Python 3.8+ 
- .NET Framework 4.7.2+
- Microsoft Edge WebView2 Runtime

### 1. Настройка базы данных
- Создайте базу данных 'bot_pomoshchnik'
- Выполните запросы для создания таблиц
```sql
CREATE TABLE users (
    id INT IDENTITY(1,1) PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    username NVARCHAR(100),
    full_name NVARCHAR(100),
    phone_number NVARCHAR(20),
    is_admin BIT DEFAULT 0,
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE()
);

CREATE TABLE requests (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL,
    request_text NVARCHAR(2000) NOT NULL,
    photo_url NVARCHAR(500),
    video_url NVARCHAR(500),
    latitude FLOAT,
    longitude FLOAT,
    status NVARCHAR(50) DEFAULT 'new',
    request_number NVARCHAR(50) UNIQUE NOT NULL,
    created_at DATETIME2 DEFAULT GETDATE(),
    updated_at DATETIME2 DEFAULT GETDATE(),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE request_comments (
    id INT IDENTITY(1,1) PRIMARY KEY,
    request_id INT NOT NULL,
    admin_id INT NOT NULL,
    comment_text NVARCHAR(1000) NOT NULL,
    is_public BIT DEFAULT 1,
    created_at DATETIME2 DEFAULT GETDATE(),
    FOREIGN KEY (request_id) REFERENCES requests(id) ON DELETE CASCADE,
    FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE NO ACTION
);

CREATE TABLE broadcasts (
    id INT IDENTITY(1,1) PRIMARY KEY,
    admin_id INT NOT NULL,
    message_text NVARCHAR(2000) NOT NULL,
    sent_at DATETIME2 DEFAULT GETDATE(),
    recipients_count INT DEFAULT 0,
    FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE NO ACTION
);

CREATE TABLE admin_codes (
    id INT IDENTITY(1,1) PRIMARY KEY,
    code_hash NVARCHAR(128) NOT NULL,
    code_salt NVARCHAR(32) NOT NULL,
    is_active BIT DEFAULT 1,
    created_at DATETIME2 DEFAULT GETDATE(),
    created_by INT,
    expires_at DATETIME2,
    usage_count INT DEFAULT 0,
    max_usage INT DEFAULT 0,
    description NVARCHAR(255),
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX IX_admin_codes_code_hash ON admin_codes(code_hash);
CREATE INDEX IX_admin_codes_is_active ON admin_codes(is_active);
CREATE INDEX IX_admin_codes_expires_at ON admin_codes(expires_at);
```

### 2. Установка и запуск бота
- Клонируйте репозиторий
- Установите необхоимые зависимости Python
- Настройте переменные окружения (Отредактируйте .env файл):
```
BOT_TOKEN=<Токен_бота>
DB_SERVER=<Адрес_сервера>
DB_NAME=bot_pomoshchnik
DB_USERNAME=<Имя_пользователя>    # опционально
DB_PASSWORD=<Пароль_пользователя> # опционально
```

### 3. Запуск desktop-приложения
Через Visual Studio
- Откройте Adminpanel.sln
- Проверьте зависимости
- Проверьте строку подключения в DatabaseHelper.cs
- Впишите токен бота в файле Program.cs
- Запустите сборку

## Аутентификация администратора
### Секретные коды:
- Хранятся в БД хешированными с солью
- Ограничение по времени и количеству использований
- Единая система для бота и desktop-приложения
## Основные сущности базы данных
- users - Пользователи системы
- requests - Заявки от жителей
- request_comments - Комментарии к заявкам
- admin_codes - Коды доступа администраторов
## Сценарии использования
### Житель подает заявку:
- Находит бота в Telegram
- Использует /start -> /submit_request
- Описывает проблему, прикрепляет медиа
- Получает номер заявки для отслеживания
### Оператор обрабатывает заявку:
- /admin + код доступа
- Просмотр заявок, смена статусов, комментарии
## API интеграции
### Telegram Bot API:
- Прием сообщений и медиа
- Отправка уведомлений
- Работа с файлами через direct URL
- Яндекс Карты API:
- Отображение кластеров заявок
- Интерактивные метки с подписями
## Мониторинг и аналитика
### Встроенные отчеты:
- Статистика по статусам заявок
- Выгрузка в CSV за периоды
- Количество пользователей и активность
### Визуализация:
- Карта проблемных точек города
- Галерея фотодоказательств
- Фильтры по времени и типу проблем

## Команда разработки
### Роли в проекте:
- Менеджер проекта - стратегия, планирование, презентация
- Разработчик - серверная часть, архитектура, интеграции
- Дизайнер - UX/CUI, интерфейсы, пользовательские сценарии

# Лицензия
Проект разработан в рамках хакатона. Для использования в муниципальных целях требуется доработка и тестирование.
