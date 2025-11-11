using System;
using System.Data.SqlClient;
using System.Security.Cryptography;
using System.Text;
using System.Windows.Forms;

public static class DatabaseHelper
{
    private static string _connectionString = @"Data Source=DESKTOP-33V95C9\SQLEXPRESS;Initial Catalog=bot_pomoshchnik;Integrated Security=true;";

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
}