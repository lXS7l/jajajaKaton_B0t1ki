using System;
using System.Windows.Forms;
using Microsoft.Win32;

namespace Adminpanel
{
    public static class WebBrowserHelper
    {
        public static void SetBrowserEmulationMode()
        {
            var appName = System.IO.Path.GetFileName(System.Diagnostics.Process.GetCurrentProcess().MainModule.FileName);

            uint mode = 11001; // IE11 edge mode

            try
            {
                using (var key = Registry.CurrentUser.CreateSubKey(
                    @"Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_BROWSER_EMULATION",
                    RegistryKeyPermissionCheck.ReadWriteSubTree))
                {
                    key.SetValue(appName, (int)mode, RegistryValueKind.DWord);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Не удалось установить режим эмуляции браузера: {ex.Message}",
                    "Предупреждение", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        public static void SetWebBrowserFeatures()
        {
            // Устанавливаем DOCTYPE для принудительного использования стандартного режима
            var appName = System.IO.Path.GetFileName(System.Diagnostics.Process.GetCurrentProcess().MainModule.FileName);

            try
            {
                using (var key = Registry.CurrentUser.CreateSubKey(
                    @"Software\Microsoft\Internet Explorer\Main\FeatureControl\FEATURE_BROWSER_EMULATION",
                    RegistryKeyPermissionCheck.ReadWriteSubTree))
                {
                    if (key.GetValue(appName) == null)
                    {
                        key.SetValue(appName, 11001, RegistryValueKind.DWord);
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Ошибка настройки WebBrowser: {ex.Message}");
            }
        }
    }
}