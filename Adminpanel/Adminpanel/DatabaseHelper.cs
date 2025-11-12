using System;
using System.Collections.Generic;
using System.Data.SqlClient;
using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;
using System.Text.Json;

namespace Adminpanel
{
    internal class DatabaseHelper
    {
        private static string _connectionString = @"Data Source=DESKTOP-33V95C9\SQLEXPRESS;Initial Catalog=bot_pomoshchnik;Integrated Security=true;";

        private static string _botToken;

        public static List<Request> GetRequestsWithCoordinates(string statusFilter = null, DateTime? startDate = null,
                                                      DateTime? endDate = null, string searchText = null)
        {
            var requests = new List<Request>();

            try
            {
                using (var connection = new SqlConnection(_connectionString))
                {
                    connection.Open();

                    string query = @"
                SELECT 
                    r.id, r.request_number, r.request_text, r.status, 
                    r.created_at, r.latitude, r.longitude,
                    r.photo_url, r.video_url,
                    u.full_name as user_full_name
                FROM requests r
                LEFT JOIN users u ON r.user_id = u.id
                WHERE r.latitude IS NOT NULL AND r.longitude IS NOT NULL";

                    var parameters = new List<SqlParameter>();

                    if (!string.IsNullOrEmpty(statusFilter) && statusFilter != "Все")
                    {
                        query += " AND r.status = @status";
                        parameters.Add(new SqlParameter("@status", statusFilter));
                    }

                    if (startDate.HasValue)
                    {
                        query += " AND r.created_at >= @startDate";
                        parameters.Add(new SqlParameter("@startDate", startDate.Value));
                    }

                    if (endDate.HasValue)
                    {
                        query += " AND r.created_at <= @endDate";
                        parameters.Add(new SqlParameter("@endDate", endDate.Value.AddDays(1).AddSeconds(-1)));
                    }

                    if (!string.IsNullOrEmpty(searchText))
                    {
                        query += " AND r.request_text LIKE @searchText";
                        parameters.Add(new SqlParameter("@searchText", $"%{searchText}%"));
                    }

                    query += " ORDER BY r.created_at DESC";

                    using (var command = new SqlCommand(query, connection))
                    {
                        command.Parameters.AddRange(parameters.ToArray());

                        using (var reader = command.ExecuteReader())
                        {
                            while (reader.Read())
                            {
                                var request = new Request
                                {
                                    Id = reader.GetInt32(0),
                                    RequestNumber = reader.GetString(1),
                                    RequestText = reader.IsDBNull(2) ? "" : reader.GetString(2),
                                    Status = reader.GetString(3),
                                    CreatedAt = reader.GetDateTime(4),
                                    // Гарантируем корректное чтение double значений
                                    Latitude = reader.IsDBNull(5) ? (double?)null : Convert.ToDouble(reader[5]),
                                    Longitude = reader.IsDBNull(6) ? (double?)null : Convert.ToDouble(reader[6]),
                                    PhotoUrl = reader.IsDBNull(7) ? null : reader.GetString(7),
                                    VideoUrl = reader.IsDBNull(8) ? null : reader.GetString(8),
                                    UserFullName = reader.IsDBNull(9) ? null : reader.GetString(9)
                                };

                                requests.Add(request);
                            }
                        }
                    }
                }

                return requests;
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Ошибка при загрузке заявок с координатами: {ex.Message}", "Ошибка",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
                return new List<Request>();
            }
        }

        public static List<Request> GetRequestsWithPhotos(string statusFilter = null, DateTime? startDate = null,
                                                  DateTime? endDate = null, string searchText = null)
        {
            var requests = new List<Request>();

            try
            {
                using (var connection = new SqlConnection(_connectionString))
                {
                    connection.Open();

                    string query = @"
                SELECT 
                    r.id, r.request_number, r.request_text, r.status, 
                    r.created_at, r.latitude, r.longitude,
                    r.photo_url, r.video_url,
                    u.full_name as user_full_name
                FROM requests r
                LEFT JOIN users u ON r.user_id = u.id
                WHERE r.photo_url IS NOT NULL AND r.photo_url != ''";

                    var parameters = new List<SqlParameter>();

                    // Фильтр по статусу
                    if (!string.IsNullOrEmpty(statusFilter) && statusFilter != "Все")
                    {
                        query += " AND r.status = @status";
                        parameters.Add(new SqlParameter("@status", statusFilter));
                    }

                    // Фильтр по дате начала
                    if (startDate.HasValue)
                    {
                        query += " AND r.created_at >= @startDate";
                        parameters.Add(new SqlParameter("@startDate", startDate.Value));
                    }

                    // Фильтр по дате окончания
                    if (endDate.HasValue)
                    {
                        query += " AND r.created_at <= @endDate";
                        parameters.Add(new SqlParameter("@endDate", endDate.Value.AddDays(1).AddSeconds(-1)));
                    }

                    // Поиск по тексту
                    if (!string.IsNullOrEmpty(searchText))
                    {
                        query += " AND r.request_text LIKE @searchText";
                        parameters.Add(new SqlParameter("@searchText", $"%{searchText}%"));
                    }

                    query += " ORDER BY r.created_at DESC";

                    using (var command = new SqlCommand(query, connection))
                    {
                        command.Parameters.AddRange(parameters.ToArray());

                        using (var reader = command.ExecuteReader())
                        {
                            while (reader.Read())
                            {
                                var request = new Request
                                {
                                    Id = reader.GetInt32(0),
                                    RequestNumber = reader.GetString(1),
                                    RequestText = reader.IsDBNull(2) ? "" : reader.GetString(2),
                                    Status = reader.GetString(3),
                                    CreatedAt = reader.GetDateTime(4),
                                    Latitude = reader.IsDBNull(5) ? (double?)null : reader.GetDouble(5),
                                    Longitude = reader.IsDBNull(6) ? (double?)null : reader.GetDouble(6),
                                    PhotoUrl = reader.IsDBNull(7) ? null : reader.GetString(7),
                                    VideoUrl = reader.IsDBNull(8) ? null : reader.GetString(8),
                                    UserFullName = reader.IsDBNull(9) ? null : reader.GetString(9)
                                };

                                requests.Add(request);
                            }
                        }
                    }
                }

                return requests;
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Ошибка при загрузке заявок с фото: {ex.Message}", "Ошибка",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
                return new List<Request>();
            }
        }

        public static void SetBotToken(string botToken)
        {
            _botToken = botToken;
        }

        public static async Task<string> GetTelegramFileUrlAsync(string fileId)
        {
            if (string.IsNullOrEmpty(fileId) || string.IsNullOrEmpty(_botToken))
                return null;

            try
            {
                // Если это уже прямой URL, возвращаем как есть
                if (fileId.StartsWith("http://") || fileId.StartsWith("https://"))
                    return fileId;

                // Получаем информацию о файле через Telegram API
                string getFileUrl = $"https://api.telegram.org/bot{_botToken}/getFile?file_id={fileId}";

                using (var webClient = new WebClient())
                {
                    string response = await webClient.DownloadStringTaskAsync(getFileUrl);

                    // Парсим JSON ответ
                    var result = JsonSerializer.Deserialize<TelegramFileResponse>(response);

                    if (result.ok && result.result != null)
                    {
                        string filePath = result.result.file_path;
                        return $"https://api.telegram.org/file/bot{_botToken}/{filePath}";
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Ошибка при получении URL файла: {ex.Message}");
            }

            return null;
        }

        // Классы для десериализации JSON ответа от Telegram
        private class TelegramFileResponse
        {
            public bool ok { get; set; }
            public FileResult result { get; set; }
        }

        private class FileResult
        {
            public string file_id { get; set; }
            public string file_unique_id { get; set; }
            public int file_size { get; set; }
            public string file_path { get; set; }
        }

        public static bool VerifyAdminCode(string inputCode)
        {

            if (string.IsNullOrEmpty(_connectionString))
            {
                MessageBox.Show("Строка подключения не установлена", "Ошибка",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
                return false;
            }

            SqlConnection connection = null;
            SqlTransaction transaction = null;

            try
            {
                connection = new SqlConnection(_connectionString);
                connection.Open();
                transaction = connection.BeginTransaction();

                // Получаем активные коды
                string query = @"
                SELECT id, code_hash, code_salt, is_active, expires_at, usage_count, max_usage
                FROM admin_codes 
                WHERE is_active = 1 
                AND (expires_at IS NULL OR expires_at > GETDATE())";

                using (var command = new SqlCommand(query, connection, transaction))
                using (var reader = command.ExecuteReader())
                {
                    while (reader.Read())
                    {
                        int codeId = reader.GetInt32(0);
                        string storedHash = reader.GetString(1);
                        string salt = reader.GetString(2);
                        bool isActive = reader.GetBoolean(3);
                        DateTime? expiresAt = reader.IsDBNull(4) ? null : (DateTime?)reader.GetDateTime(4);
                        int usageCount = reader.GetInt32(5);
                        int maxUsage = reader.GetInt32(6);

                        // Проверяем код
                        string inputHash = HashCode(inputCode, salt);
                        if (inputHash == storedHash)
                        {
                            // Проверяем лимит использований
                            if (maxUsage > 0 && usageCount >= maxUsage)
                            {
                                // Деактивируем код
                                DeactivateAdminCode(codeId, connection, transaction);
                                continue;
                            }

                            reader.Close(); // Закрываем reader перед выполнением update

                            // Увеличиваем счетчик использований
                            UpdateUsageCount(codeId, connection, transaction);
                            transaction.Commit();

                            return true;
                        }
                    }
                }

                transaction?.Commit();
                return false;
            }
            catch (SqlException sqlEx)
            {
                transaction?.Rollback();
                MessageBox.Show($"Ошибка базы данных: {sqlEx.Message}\nПроверьте строку подключения и доступность сервера.",
                    "Ошибка подключения", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return false;
            }
            catch (Exception ex)
            {
                transaction?.Rollback();
                MessageBox.Show($"Ошибка при проверке кода: {ex.Message}", "Ошибка",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
                return false;
            }
            finally
            {
                connection?.Close();
            }
        }

        private static string HashCode(string code, string salt)
        {
            try
            {
                using (SHA256 sha256 = SHA256.Create())
                {
                    byte[] bytes = Encoding.UTF8.GetBytes(code + salt);
                    byte[] hash = sha256.ComputeHash(bytes);
                    return BitConverter.ToString(hash).Replace("-", "").ToLower();
                }
            }
            catch (Exception ex)
            {
                throw new Exception($"Ошибка хэширования: {ex.Message}");
            }
        }

        private static void UpdateUsageCount(int codeId, SqlConnection connection, SqlTransaction transaction)
        {
            string query = "UPDATE admin_codes SET usage_count = usage_count + 1 WHERE id = @codeId";
            using (var command = new SqlCommand(query, connection, transaction))
            {
                command.Parameters.AddWithValue("@codeId", codeId);
                command.ExecuteNonQuery();
            }
        }

        private static void DeactivateAdminCode(int codeId, SqlConnection connection, SqlTransaction transaction)
        {
            string query = "UPDATE admin_codes SET is_active = 0 WHERE id = @codeId";
            using (var command = new SqlCommand(query, connection, transaction))
            {
                command.Parameters.AddWithValue("@codeId", codeId);
                command.ExecuteNonQuery();
            }
        }

        // Метод для тестирования подключения
        public static bool TestConnection()
        {
            if (string.IsNullOrEmpty(_connectionString))
                return false;

            try
            {
                using (var connection = new SqlConnection(_connectionString))
                {
                    connection.Open();
                    return true;
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Ошибка подключения к базе: {ex.Message}", "Ошибка",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
                return false;
            }
        }
        public static List<Request> GetRequests(string statusFilter = null, DateTime? startDate = null,
                                              DateTime? endDate = null, string searchText = null)
        {
            var requests = new List<Request>();

            try
            {
                using (var connection = new SqlConnection(_connectionString))
                {
                    connection.Open();

                    string query = @"
                        SELECT 
                            r.id, r.request_number, r.request_text, r.status, 
                            r.created_at, r.latitude, r.longitude,
                            r.photo_url, r.video_url,
                            u.full_name as user_full_name
                        FROM requests r
                        LEFT JOIN users u ON r.user_id = u.id
                        WHERE 1=1";

                    var parameters = new List<SqlParameter>();

                    // Фильтр по статусу
                    if (!string.IsNullOrEmpty(statusFilter) && statusFilter != "Все")
                    {
                        query += " AND r.status = @status";
                        parameters.Add(new SqlParameter("@status", statusFilter));
                    }

                    // Фильтр по дате начала
                    if (startDate.HasValue)
                    {
                        query += " AND r.created_at >= @startDate";
                        parameters.Add(new SqlParameter("@startDate", startDate.Value));
                    }

                    // Фильтр по дате окончания
                    if (endDate.HasValue)
                    {
                        query += " AND r.created_at <= @endDate";
                        parameters.Add(new SqlParameter("@endDate", endDate.Value.AddDays(1).AddSeconds(-1)));
                    }

                    // Поиск по тексту
                    if (!string.IsNullOrEmpty(searchText))
                    {
                        query += " AND r.request_text LIKE @searchText";
                        parameters.Add(new SqlParameter("@searchText", $"%{searchText}%"));
                    }

                    query += " ORDER BY r.created_at DESC";

                    using (var command = new SqlCommand(query, connection))
                    {
                        command.Parameters.AddRange(parameters.ToArray());

                        using (var reader = command.ExecuteReader())
                        {
                            while (reader.Read())
                            {
                                var request = new Request
                                {
                                    Id = reader.GetInt32(0),
                                    RequestNumber = reader.GetString(1),
                                    RequestText = reader.IsDBNull(2) ? "" : reader.GetString(2),
                                    Status = reader.GetString(3),
                                    CreatedAt = reader.GetDateTime(4),
                                    Latitude = reader.IsDBNull(5) ? (double?)null : reader.GetDouble(5),
                                    Longitude = reader.IsDBNull(6) ? (double?)null : reader.GetDouble(6),
                                    PhotoUrl = reader.IsDBNull(7) ? null : reader.GetString(7),
                                    VideoUrl = reader.IsDBNull(8) ? null : reader.GetString(8),
                                    UserFullName = reader.IsDBNull(9) ? null : reader.GetString(9)
                                };

                                requests.Add(request);
                            }
                        }
                    }
                }

                return requests;
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Ошибка при загрузке заявок: {ex.Message}", "Ошибка",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
                return new List<Request>();
            }
        }

        public static List<string> GetStatusList()
        {
            return new List<string>
            {
                "Все", "new", "in_progress", "completed", "rejected", "cancelled"
            };
        }
    }
}
