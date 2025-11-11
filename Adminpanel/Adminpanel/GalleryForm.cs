using System;
using System.Collections.Generic;
using System.Drawing;
using System.Windows.Forms;
using System.Linq;
using System.Threading.Tasks;

namespace Adminpanel
{
    public partial class GalleryForm : Form
    {
        private List<Request> _requestsWithPhotos;
        private int _currentPage = 0;
        private int _pageSize = 6; // 6 фото на странице
        private int _totalPages = 0;
        private List<PictureBox> _pictureBoxes = new List<PictureBox>();
        private List<Label> _labels = new List<Label>();
        private int _itemsPerRow = 3; // Будет меняться в зависимости от размера экрана

        public GalleryForm()
        {
            InitializeComponent();
            CalculateItemsPerRow();
            LoadRequestsWithPhotos();
            UpdateNavigationButtons();

            // Подписываемся на событие изменения размера формы
            this.Resize += GalleryForm_Resize;
        }

        private void GalleryForm_Resize(object sender, EventArgs e)
        {
            // Пересчитываем количество элементов в строке при изменении размера формы
            CalculateItemsPerRow();
            // Перерисовываем галерею с новыми размерами
            DisplayPage(_currentPage);
        }

        private void CalculateItemsPerRow()
        {
            // Определяем количество элементов в строке в зависимости от ширины формы
            int formWidth = this.ClientSize.Width;

            if (formWidth >= 1200)
                _itemsPerRow = 4;
            else if (formWidth >= 900)
                _itemsPerRow = 3;
            else if (formWidth >= 600)
                _itemsPerRow = 2;
            else
                _itemsPerRow = 1;

            // Пересчитываем размер страницы
            _pageSize = _itemsPerRow * 2; // 2 строки
        }

        private void LoadRequestsWithPhotos()
        {
            try
            {
                Cursor = Cursors.WaitCursor;

                // Получаем все заявки с фото
                _requestsWithPhotos = DatabaseHelper.GetRequestsWithPhotos();

                _totalPages = (int)Math.Ceiling((double)_requestsWithPhotos.Count / _pageSize);

                if (_totalPages == 0)
                {
                    _totalPages = 1; // Чтобы не было деления на ноль
                }

                DisplayPage(_currentPage);
                UpdatePageInfo();
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Ошибка при загрузке заявок с фото: {ex.Message}", "Ошибка",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            finally
            {
                Cursor = Cursors.Default;
            }
        }

        private void DisplayPage(int pageIndex)
        {
            ClearGallery();

            if (!_requestsWithPhotos.Any())
            {
                Label noPhotosLabel = new Label();
                noPhotosLabel.Text = "Нет заявок с фотографиями";
                noPhotosLabel.AutoSize = true;
                noPhotosLabel.Font = new Font("Microsoft Sans Serif", 12F, FontStyle.Bold);
                noPhotosLabel.Location = new Point(350, 200);
                panelGallery.Controls.Add(noPhotosLabel);
                return;
            }

            var startIndex = pageIndex * _pageSize;
            var endIndex = Math.Min(startIndex + _pageSize, _requestsWithPhotos.Count);
            var pageRequests = _requestsWithPhotos.GetRange(startIndex, endIndex - startIndex);

            // Рассчитываем размеры элементов в зависимости от размера панели
            int panelWidth = panelGallery.ClientSize.Width;
            int panelHeight = panelGallery.ClientSize.Height;

            int spacing = 20;
            int availableWidth = panelWidth - (spacing * (_itemsPerRow + 1));
            int pictureSize = availableWidth / _itemsPerRow;
            int labelHeight = 40;

            int x = spacing, y = spacing;

            for (int i = 0; i < pageRequests.Count; i++)
            {
                var request = pageRequests[i];

                // Создаем PictureBox для фото
                var pictureBox = new PictureBox();
                pictureBox.Size = new Size(pictureSize, pictureSize);
                pictureBox.Location = new Point(x, y);
                pictureBox.SizeMode = PictureBoxSizeMode.Zoom;
                pictureBox.BorderStyle = BorderStyle.FixedSingle;
                pictureBox.Cursor = Cursors.Hand;
                pictureBox.Tag = request; // Сохраняем заявку для открытия деталей

                // Загружаем фото
                LoadPhotoForGallery(pictureBox, request.PhotoUrl);

                // Обработчик клика для открытия деталей заявки
                pictureBox.Click += PictureBox_Click;

                // Создаем подпись с номером заявки и датой
                var label = new Label();
                label.Text = $"{request.RequestNumber}\n{request.FormattedDate}";
                label.Size = new Size(pictureSize, labelHeight);
                label.Location = new Point(x, y + pictureSize + 5);
                label.TextAlign = ContentAlignment.TopCenter;
                label.Font = new Font("Microsoft Sans Serif", 8F);
                label.Tag = request;
                label.Cursor = Cursors.Hand;
                label.Click += Label_Click;

                // Добавляем на панель
                panelGallery.Controls.Add(pictureBox);
                panelGallery.Controls.Add(label);

                _pictureBoxes.Add(pictureBox);
                _labels.Add(label);

                // Переход к следующей позиции
                x += pictureSize + spacing;
                if ((i + 1) % _itemsPerRow == 0)
                {
                    x = spacing;
                    y += pictureSize + labelHeight + spacing;
                }
            }
        }

        private async void LoadPhotoForGallery(PictureBox pictureBox, string photoUrl)
        {
            try
            {
                // Создаем заглушку загрузки
                CreateGalleryLoadingPlaceholder(pictureBox, "Загрузка...");

                // Получаем прямой URL файла
                string directUrl = await DatabaseHelper.GetTelegramFileUrlAsync(photoUrl);

                if (string.IsNullOrEmpty(directUrl))
                {
                    CreateGalleryInfoPlaceholder(pictureBox, "Нет фото");
                    return;
                }

                // Загружаем изображение
                using (var webClient = new System.Net.WebClient())
                {
                    byte[] imageData = await webClient.DownloadDataTaskAsync(directUrl);
                    using (var stream = new System.IO.MemoryStream(imageData))
                    {
                        var image = Image.FromStream(stream);
                        pictureBox.Image = image;
                    }
                }
            }
            catch (Exception ex)
            {
                CreateGalleryErrorPlaceholder(pictureBox, "Ошибка");
                Console.WriteLine($"Ошибка загрузки фото в галерее: {ex.Message}");
            }
        }

        private void CreateGalleryLoadingPlaceholder(PictureBox pictureBox, string text)
        {
            var bmp = new Bitmap(pictureBox.Width, pictureBox.Height);
            using (Graphics g = Graphics.FromImage(bmp))
            using (Font font = new Font("Arial", 9))
            using (Brush brush = new SolidBrush(Color.Gray))
            {
                g.Clear(Color.LightGray);
                SizeF textSize = g.MeasureString(text, font);
                g.DrawString(text, font, brush,
                    (pictureBox.Width - textSize.Width) / 2,
                    (pictureBox.Height - textSize.Height) / 2);
            }
            pictureBox.Image = bmp;
        }

        private void CreateGalleryInfoPlaceholder(PictureBox pictureBox, string text)
        {
            var bmp = new Bitmap(pictureBox.Width, pictureBox.Height);
            using (Graphics g = Graphics.FromImage(bmp))
            using (Font font = new Font("Arial", 9))
            using (Brush brush = new SolidBrush(Color.DarkBlue))
            {
                g.Clear(Color.LightBlue);
                SizeF textSize = g.MeasureString(text, font);
                g.DrawString(text, font, brush,
                    (pictureBox.Width - textSize.Width) / 2,
                    (pictureBox.Height - textSize.Height) / 2);
            }
            pictureBox.Image = bmp;
        }

        private void CreateGalleryErrorPlaceholder(PictureBox pictureBox, string text)
        {
            var bmp = new Bitmap(pictureBox.Width, pictureBox.Height);
            using (Graphics g = Graphics.FromImage(bmp))
            using (Font font = new Font("Arial", 9))
            using (Brush brush = new SolidBrush(Color.DarkRed))
            {
                g.Clear(Color.LightCoral);
                SizeF textSize = g.MeasureString(text, font);
                g.DrawString(text, font, brush,
                    (pictureBox.Width - textSize.Width) / 2,
                    (pictureBox.Height - textSize.Height) / 2);
            }
            pictureBox.Image = bmp;
        }

        private void ClearGallery()
        {
            foreach (var pictureBox in _pictureBoxes)
            {
                pictureBox.Image?.Dispose();
                pictureBox.Dispose();
            }

            foreach (var label in _labels)
            {
                label.Dispose();
            }

            _pictureBoxes.Clear();
            _labels.Clear();
            panelGallery.Controls.Clear();
        }

        private void PictureBox_Click(object sender, EventArgs e)
        {
            var pictureBox = sender as PictureBox;
            if (pictureBox?.Tag is Request request)
            {
                OpenRequestDetails(request);
            }
        }

        private void Label_Click(object sender, EventArgs e)
        {
            var label = sender as Label;
            if (label?.Tag is Request request)
            {
                OpenRequestDetails(request);
            }
        }

        private void OpenRequestDetails(Request request)
        {
            var detailsForm = new RequestDetailsForm(request);
            detailsForm.ShowDialog();
        }

        private void UpdatePageInfo()
        {
            labelPageInfo.Text = $"Страница {_currentPage + 1} из {_totalPages}";
        }

        private void UpdateNavigationButtons()
        {
            buttonPrevious.Enabled = _currentPage > 0;
            buttonNext.Enabled = _currentPage < _totalPages - 1;
        }

        private void buttonPrevious_Click(object sender, EventArgs e)
        {
            if (_currentPage > 0)
            {
                _currentPage--;
                DisplayPage(_currentPage);
                UpdatePageInfo();
                UpdateNavigationButtons();
            }
        }

        private void buttonNext_Click(object sender, EventArgs e)
        {
            if (_currentPage < _totalPages - 1)
            {
                _currentPage++;
                DisplayPage(_currentPage);
                UpdatePageInfo();
                UpdateNavigationButtons();
            }
        }

        private void buttonClose_Click(object sender, EventArgs e)
        {
            this.Close();
        }

        protected override void OnFormClosed(FormClosedEventArgs e)
        {
            ClearGallery();
            base.OnFormClosed(e);
        }
    }
}