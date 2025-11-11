using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.Data;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows.Forms;

namespace Adminpanel
{
    public partial class AuthForm : Form
    {
        public bool IsAuthenticated { get; private set; } = false;

        private void AutoForm_Paint(object sender, PaintEventArgs e) // Цвет
        {
            Graphics g = e.Graphics;
            Rectangle rect = new Rectangle(0, 0, this.Width, this.Height);

            Color startColor = ColorTranslator.FromHtml("#03624C"); // тёмно-зел
            Color endColor = ColorTranslator.FromHtml("#93DF70");   // лайм

            using (LinearGradientBrush brush = new LinearGradientBrush(rect, startColor, endColor, 45f))
            {
                g.FillRectangle(brush, rect);
            }
        }

        public AuthForm()
        {
            InitializeComponent();
            this.Shown += AuthForm_Shown;
        }

        private void AuthForm_Shown(object sender, EventArgs e)
        {
            txtAdminCode.Focus();
        }

        private async void btnLogin_Click(object sender, EventArgs e)
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
            btnCancel.Enabled = false;
            btnLogin.Text = "Проверка...";
            UseWaitCursor = true;

            try
            {
                // Проверяем код асинхронно
                bool isValid = await Task.Run(() => DatabaseHelper.VerifyAdminCode(code));

                if (isValid)
                {
                    IsAuthenticated = true;
                    MessageBox.Show("Авторизация успешна!", "Успех",
                        MessageBoxButtons.OK, MessageBoxIcon.Information);
                    RequestsListForm form = new RequestsListForm();
                    this.Hide();
                    form.ShowDialog();
                    this.Close();
                }
                else
                {
                    MessageBox.Show("Неверный код администратора или срок действия истек",
                        "Ошибка авторизации", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    txtAdminCode.SelectAll();
                    txtAdminCode.Focus();
                }
            }
            finally
            {
                // Восстанавливаем элементы управления
                btnLogin.Enabled = true;
                btnCancel.Enabled = true;
                btnLogin.Text = "Войти";
                UseWaitCursor = false;
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
