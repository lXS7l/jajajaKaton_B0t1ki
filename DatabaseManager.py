import os
import pyodbc
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Загружаем переменные окружения
load_dotenv()

class DatabaseManager:
    def __init__(self):
        self.connection_string = self._get_connection_string()
        self.connection = None

    def _get_connection_string(self) -> str:
        """Формирует правильную строку подключения к SQL Server"""
        server = os.getenv('DB_SERVER', 'localhost')
        database = os.getenv('DB_NAME', 'EmergencyBot112')
        username = os.getenv('DB_USERNAME', '')
        password = os.getenv('DB_PASSWORD', '')

        # Строка подключения для SQL Server
        if username and password:
            return (
                f"DRIVER={{SQL Server}};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"UID={username};"
                f"PWD={password};"
                f"Trusted_Connection=no;"
            )
        else:
            return (
                f"DRIVER={{SQL Server}};"
                f"SERVER={server};"
                f"DATABASE={database};"
                f"Trusted_Connection=yes;"
            )

    def connect(self):
        """Устанавливает соединение с базой данных"""
        try:
            self.connection = pyodbc.connect(self.connection_string)
        except pyodbc.Error as e:
            print(f"Ошибка подключения к базе данных: {e}")
            raise

    def disconnect(self):
        """Закрывает соединение с базой данных"""
        if self.connection:
            self.connection.close()

    def _hash_code(self, code: str, salt: str) -> str:
        """Хэширует код с использованием соли"""
        return hashlib.sha256(f"{code}{salt}".encode()).hexdigest()

    def create_admin_code(self, code: str, created_by: int = None,
                          expires_days: int = None, max_usage: int = 0,
                          description: str = None) -> int:
        """
        Создает новый код администратора
        """
        try:
            salt = secrets.token_hex(16)
            code_hash = self._hash_code(code, salt)

            expires_at = None
            if expires_days:
                expires_at = datetime.now() + timedelta(days=expires_days)

            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO admin_codes (code_hash, code_salt, created_by, expires_at, max_usage, description)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, ?, ?, ?)
            """, code_hash, salt, created_by, expires_at, max_usage, description)

            code_id = cursor.fetchone()[0]
            self.connection.commit()
            print(f"Создан код администратора с ID: {code_id}")
            return code_id

        except pyodbc.Error as e:
            print(f"Ошибка при создании кода администратора: {e}")
            self.connection.rollback()
            raise

    def verify_admin_code(self, input_code: str, user_id: int) -> bool:
        """
        Проверяет код администратора и выдает права при успехе
        """
        try:
            cursor = self.connection.cursor()

            # Получаем активные коды
            cursor.execute("""
                SELECT id, code_hash, code_salt, is_active, expires_at, usage_count, max_usage
                FROM admin_codes 
                WHERE is_active = 1 
                AND (expires_at IS NULL OR expires_at > GETDATE())
            """)

            valid_code_found = False
            code_id = None

            for row in cursor.fetchall():
                code_id, stored_hash, salt, is_active, expires_at, usage_count, max_usage = row

                # Проверяем код
                input_hash = self._hash_code(input_code, salt)
                if input_hash == stored_hash:
                    # Проверяем лимит использований
                    if max_usage > 0 and usage_count >= max_usage:
                        # Деактивируем код
                        self.deactivate_admin_code(code_id)
                        continue

                    valid_code_found = True
                    break

            if valid_code_found:
                # Увеличиваем счетчик использований
                cursor.execute("""
                    UPDATE admin_codes 
                    SET usage_count = usage_count + 1 
                    WHERE id = ?
                """, code_id)

                # Выдаем права администратора
                cursor.execute("""
                    UPDATE users 
                    SET is_admin = 1 
                    WHERE id = ?
                """, user_id)

                self.connection.commit()
                print(f"Пользователю {user_id} выданы права администратора")
                return True
            else:
                print("Неверный код администратора или срок действия истек")
                return False

        except pyodbc.Error as e:
            print(f"Ошибка при проверке кода администратора: {e}")
            self.connection.rollback()
            return False

    def deactivate_admin_code(self, code_id: int) -> bool:
        """Деактивирует код администратора"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE admin_codes 
                SET is_active = 0 
                WHERE id = ?
            """, code_id)

            self.connection.commit()
            print(f"Код администратора {code_id} деактивирован")
            return True

        except pyodbc.Error as e:
            print(f"Ошибка при деактивации кода администратора: {e}")
            self.connection.rollback()
            return False

    def create_user(self, telegram_id: int, username: str = None,
                    full_name: str = None, phone_number: str = None) -> int:
        """
        Создает нового пользователя или возвращает существующего
        """
        try:
            cursor = self.connection.cursor()

            # Проверяем, существует ли пользователь
            cursor.execute("SELECT id FROM users WHERE telegram_id = ?", telegram_id)

            result = cursor.fetchone()
            if result:
                user_id = result[0]
                print(f"Пользователь {user_id} уже существует")
                return user_id

            # Создаем нового пользователя
            cursor.execute("""
                INSERT INTO users (telegram_id, username, full_name, phone_number)
                OUTPUT INSERTED.id
                VALUES (?, ?, ?, ?)
            """, telegram_id, username, full_name, phone_number)

            user_id = cursor.fetchone()[0]
            self.connection.commit()
            print(f"Создан пользователь с ID: {user_id}")
            return user_id

        except pyodbc.Error as e:
            print(f"Ошибка при создании пользователя: {e}")
            self.connection.rollback()
            raise

    def create_request(self, user_id: int, request_text: str,
                       photo_url: str = None, video_url: str = None,
                       latitude: float = None, longitude: float = None) -> Dict[str, Any]:
        """
        Создает новую заявку
        """
        try:
            # Генерируем номер заявки
            request_number = self._generate_request_number()

            cursor = self.connection.cursor()
            cursor.execute("""
                    INSERT INTO requests (user_id, request_text, photo_url, video_url, latitude, longitude, request_number, status)
                    OUTPUT INSERTED.id, INSERTED.request_number, INSERTED.created_at
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'new')
                """, user_id, request_text, photo_url, video_url, latitude, longitude, request_number)

            request_id, request_number, created_at = cursor.fetchone()
            self.connection.commit()

            print(f"Создана заявка {request_number} с ID: {request_id}")

            return {
                'id': request_id,
                'request_number': request_number,
                'created_at': created_at,
                'status': 'new'
            }

        except pyodbc.Error as e:
            print(f"Ошибка при создании заявки: {e}")
            self.connection.rollback()
            raise

    def _generate_request_number(self) -> str:
        """Генерирует уникальный номер заявки"""
        current_date = datetime.now().strftime("%Y%m%d")

        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM requests 
            WHERE request_number LIKE ? + '-%'
        """, current_date)

        count = cursor.fetchone()[0] + 1
        return f"{current_date}-{count:04d}"

    def is_user_admin(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь администратором"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT is_admin FROM users WHERE id = ?", user_id)

            result = cursor.fetchone()
            return result[0] if result else False

        except pyodbc.Error as e:
            print(f"Ошибка при проверке прав администратора: {e}")
            return False

    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Получает информацию о пользователе по Telegram ID"""
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT id, telegram_id, username, full_name, phone_number, is_admin, created_at
                FROM users WHERE telegram_id = ?
            """, telegram_id)

            result = cursor.fetchone()
            if result:
                return {
                    'id': result[0],
                    'telegram_id': result[1],
                    'username': result[2],
                    'full_name': result[3],
                    'phone_number': result[4],
                    'is_admin': bool(result[5]),
                    'created_at': result[6]
                }
            return None

        except pyodbc.Error as e:
            print(f"Ошибка при получении пользователя: {e}")
            return None
