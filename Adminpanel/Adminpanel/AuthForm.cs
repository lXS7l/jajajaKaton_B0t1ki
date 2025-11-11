using System;
using System.Windows.Forms;

namespace Adminpanel
{
    public partial class AuthForm : Form
    {
        public bool IsAuthenticated { get; private set; } = false;

        public AuthForm()
        {
            InitializeComponent();
        }

        private void btnLogin_Click(object sender, EventArgs e)
        {
            string code = txtAdminCode.Text.Trim();

            if (string.IsNullOrEmpty(code))
            {
                MessageBox.Show("Введите код администратора", "Ошибка",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                txtAdminCode.Focus();
                return;
            }

            // Показываем индикатор загрузки
            btnLogin.Enabled = false;
            btnLogin.Text = "Проверка...";

            try
            {
                // Проверяем код
                if (DatabaseHelper.VerifyAdminCode(code))
                {
                    IsAuthenticated = true;
                    MessageBox.Show("Авторизация успешна!", "Успех",
                        MessageBoxButtons.OK, MessageBoxIcon.Information);
                    this.DialogResult = DialogResult.OK;
                    this.Close();
                }
                else
                {
                    MessageBox.Show("Неверный код администратора или срок действия истек",
                        "Ошибка авторизации", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    txtAdminCode.Clear();
                    txtAdminCode.Focus();
                }
            }
            finally
            {
                // Восстанавливаем кнопку
                btnLogin.Enabled = true;
                btnLogin.Text = "Войти";
            }
        }

        private void btnCancel_Click(object sender, EventArgs e)
        {
            this.DialogResult = DialogResult.Cancel;
            this.Close();
        }

        private void txtAdminCode_KeyPress(object sender, KeyPressEventArgs e)
        {
            // Разрешаем ввод только букв, цифр и Backspace
            if (!char.IsLetterOrDigit(e.KeyChar) && e.KeyChar != 8)
            {
                e.Handled = true;
            }

            // Enter для быстрой отправки
            if (e.KeyChar == (char)Keys.Enter)
            {
                btnLogin_Click(sender, e);
            }
        }
    }
}
