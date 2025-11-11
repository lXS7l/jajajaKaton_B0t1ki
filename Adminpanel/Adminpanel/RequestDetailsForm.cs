using System;
using System.Diagnostics;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.IO;
using System.Net;
using System.Windows.Forms;

namespace Adminpanel
{
    public partial class RequestDetailsForm : Form
    {
        private Request _request;

        public RequestDetailsForm(Request request)
        {
            InitializeComponent();
            _request = request;
            LoadRequestDetails();
            ApplyCustomColors();
        }

        private void RequestsDetailsForm_Paint(object sender, PaintEventArgs e) // Цвет
        {
            Graphics g = e.Graphics;
            Rectangle rect = new Rectangle(0, 0, this.Width, this.Height);

            Color startColor = ColorTranslator.FromHtml("#5CA87C"); // Светлый-Темный
            Color endColor = ColorTranslator.FromHtml("#288760");   // Тёмный(непрям)

            using (LinearGradientBrush brush = new LinearGradientBrush(rect, startColor, endColor, 45f))
            {
                g.FillRectangle(brush, rect);
            }
        }

        private void ApplyCustomColors()
        {

            Color customColor = ColorTranslator.FromHtml("#c7c7c7");

            textBoxRequestNumber.BackColor = customColor;
            textBoxStatus.BackColor = customColor;
            textBoxCreatedAt.BackColor = customColor;
            textBoxUser.BackColor = customColor;
            textBoxDescription.BackColor = customColor;
            textBoxCoordinates.BackColor = customColor;
            textBoxRequestNumber.BorderStyle = BorderStyle.None;
            textBoxStatus.BorderStyle = BorderStyle.None;
            textBoxCreatedAt.BorderStyle = BorderStyle.None;
            textBoxUser.BorderStyle = BorderStyle.None;
            textBoxCoordinates.BorderStyle = BorderStyle.None;
            linkLabelMap.BackColor = customColor;
            linkLabelBot.BackColor = customColor;
        }

        private void LoadRequestDetails()
        {
            try
            {
                // Основная информация
                textBoxRequestNumber.Text = _request.RequestNumber;
                textBoxStatus.Text = _request.StatusText;
                textBoxCreatedAt.Text = _request.FormattedDate;
                textBoxUser.Text = _request.UserDisplayName;

                // Описание
                textBoxDescription.Text = _request.RequestText;
                textBoxDescription.SelectionStart = 0;
                textBoxDescription.ScrollToCaret();

                // Местоположение
                if (_request.HasLocation)
                {
                    textBoxCoordinates.Text = $"{_request.Latitude:F6}, {_request.Longitude:F6}";
                    linkLabelMap.Visible = true;
                }
                else
                {
                    textBoxCoordinates.Text = "Не указано";
                    linkLabelMap.Visible = false;
                }

                // Медиафайлы
                labelPhoto.Visible = _request.HasPhoto;
                labelVideo.Visible = _request.HasVideo;

                if (_request.HasPhoto)
                {
                    LoadPhotoAsync(_request.PhotoUrl);
                }

                if (_request.HasVideo)
                {
                    LoadVideoInfo(_request.VideoUrl);
                }

                // Ссылка на бота
                linkLabelBot.Links.Clear();
                linkLabelBot.Links.Add(0, linkLabelBot.Text.Length);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Ошибка при загрузке деталей заявки: {ex.Message}", "Ошибка",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private async void LoadPhotoAsync(string photoUrlOrId)
        {
            try
            {
                // Показываем сообщение о загрузке
                CreateLoadingPlaceholder("Загрузка фото...");

                // Получаем прямой URL файла
                string directUrl = await DatabaseHelper.GetTelegramFileUrlAsync(photoUrlOrId);

                if (string.IsNullOrEmpty(directUrl))
                {
                    CreateInfoPlaceholder("Фото недоступно");
                    return;
                }

                // Загружаем изображение
                using (var webClient = new WebClient())
                {
                    byte[] imageData = await webClient.DownloadDataTaskAsync(directUrl);
                    using (var stream = new MemoryStream(imageData))
                    {
                        var image = Image.FromStream(stream);
                        pictureBoxPhoto.Image = image;
                        pictureBoxPhoto.SizeMode = PictureBoxSizeMode.Zoom;
                    }
                }
            }
            catch (WebException webEx)
            {
                CreateErrorPlaceholder("Ошибка загрузки фото");
                MessageBox.Show($"Не удалось загрузить фото: {webEx.Message}", "Ошибка",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
            catch (Exception ex)
            {
                CreateErrorPlaceholder("Ошибка загрузки");
                MessageBox.Show($"Ошибка при загрузке фото: {ex.Message}", "Ошибка",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        private void LoadVideoInfo(string videoUrl)
        {
            // Для видео просто показываем информацию
            labelVideo.Text = "Видео: доступно в боте";
            if (!string.IsNullOrEmpty(videoUrl))
            {
                labelVideo.Text += $" (файл найден)";
            }
        }

        private void CreateLoadingPlaceholder(string text)
        {
            pictureBoxPhoto.Image = null;
            pictureBoxPhoto.BackColor = Color.LightGray;
            pictureBoxPhoto.BorderStyle = BorderStyle.FixedSingle;

            var bmp = new Bitmap(pictureBoxPhoto.Width, pictureBoxPhoto.Height);
            using (Graphics g = Graphics.FromImage(bmp))
            using (Font font = new Font("Arial", 10))
            using (Brush brush = new SolidBrush(Color.Black))
            {
                g.Clear(Color.LightGray);
                SizeF textSize = g.MeasureString(text, font);
                g.DrawString(text, font, brush,
                    (pictureBoxPhoto.Width - textSize.Width) / 2,
                    (pictureBoxPhoto.Height - textSize.Height) / 2);
            }

            pictureBoxPhoto.Image = bmp;
        }

        private void CreateInfoPlaceholder(string text)
        {
            var bmp = new Bitmap(pictureBoxPhoto.Width, pictureBoxPhoto.Height);
            using (Graphics g = Graphics.FromImage(bmp))
            using (Font font = new Font("Arial", 9))
            using (Brush brush = new SolidBrush(Color.DarkBlue))
            {
                g.Clear(Color.LightBlue);
                SizeF textSize = g.MeasureString(text, font);
                g.DrawString(text, font, brush,
                    (pictureBoxPhoto.Width - textSize.Width) / 2,
                    (pictureBoxPhoto.Height - textSize.Height) / 2);
            }

            pictureBoxPhoto.Image = bmp;
        }

        private void CreateErrorPlaceholder(string text)
        {
            var bmp = new Bitmap(pictureBoxPhoto.Width, pictureBoxPhoto.Height);
            using (Graphics g = Graphics.FromImage(bmp))
            using (Font font = new Font("Arial", 9))
            using (Brush brush = new SolidBrush(Color.DarkRed))
            {
                g.Clear(Color.LightCoral);
                SizeF textSize = g.MeasureString(text, font);
                g.DrawString(text, font, brush,
                    (pictureBoxPhoto.Width - textSize.Width) / 2,
                    (pictureBoxPhoto.Height - textSize.Height) / 2);
            }

            pictureBoxPhoto.Image = bmp;
        }

        private void linkLabelMap_LinkClicked(object sender, LinkLabelLinkClickedEventArgs e)
        {
            if (_request.HasLocation)
            {
                string url = $"https://yandex.ru/maps/?ll={_request.LongitudeString},{_request.LatitudeString}&z=19";
                Process.Start(new ProcessStartInfo
                {
                    FileName = url,
                    UseShellExecute = true
                });
            }
        }

        private void linkLabelBot_LinkClicked(object sender, LinkLabelLinkClickedEventArgs e)
        {
            string url = $"https://t.me/BOT_pomoshchnick_BOT?start={_request.RequestNumber}";
            Process.Start(new ProcessStartInfo
            {
                FileName = url,
                UseShellExecute = true
            });
        }

        private void buttonClose_Click(object sender, EventArgs e)
        {
            this.Close();
        }

        private void buttonCopyNumber_Click(object sender, EventArgs e)
        {
            Clipboard.SetText(_request.RequestNumber);
            MessageBox.Show("Номер заявки скопирован в буфер обмена", "Успех",
                MessageBoxButtons.OK, MessageBoxIcon.Information);
        }

        // Очистка ресурсов при закрытии формы
        protected override void OnFormClosed(FormClosedEventArgs e)
        {
            pictureBoxPhoto.Image?.Dispose();
            base.OnFormClosed(e);
        }
    }
}