using Adminpanel;
using System;
using System.Globalization;
using System.Threading;
using System.Windows.Forms;

static class Program
{
    [STAThread]
    static void Main()
    {
        CultureInfo.DefaultThreadCurrentCulture = CultureInfo.InvariantCulture;
        CultureInfo.DefaultThreadCurrentUICulture = CultureInfo.InvariantCulture;
        Thread.CurrentThread.CurrentCulture = CultureInfo.InvariantCulture;
        Thread.CurrentThread.CurrentUICulture = CultureInfo.InvariantCulture;
        WebBrowserHelper.SetBrowserEmulationMode();
        WebBrowserHelper.SetWebBrowserFeatures();

        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);

        Application.EnableVisualStyles();
        Application.SetCompatibleTextRenderingDefault(false);

        // Устанавливаем строку подключения
        string connectionString = GetConnectionString();

        string botToken = "8003763924:AAGjCZnLTyzklBANnTccwzz9TJmo4lskSDc";
        DatabaseHelper.SetBotToken(botToken);

        // Тестируем подключение
        if (!DatabaseHelper.TestConnection())
        {
            MessageBox.Show("Не удалось подключиться к базе данных.\nПроверьте настройки подключения.",
                "Ошибка подключения", MessageBoxButtons.OK, MessageBoxIcon.Error);
            return;
        }

        // Показываем форму авторизации
        using (var authForm = new AuthForm())
        {
            if (authForm.ShowDialog() == DialogResult.OK && authForm.IsAuthenticated)
            {
                Application.Run(new AuthForm());
            }
        }
    }

    static string GetConnectionString()
    {
        // Ваша строка подключения к БД
        return "Data Source=localhost;Initial Catalog=EmergencyBot112;Integrated Security=True;";
    }
}