using System;
using System.Collections.Generic;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Linq;
using System.Windows.Forms;

namespace Adminpanel
{
    public partial class RequestsListForm : Form
    {
        private List<Request> _allRequests;
        private List<Request> _filteredRequests;

        private void panelFilters_Paint(object sender, PaintEventArgs e)
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

        private void buttonOpenMap_Click(object sender, EventArgs e)
        {
            var mapForm = new MapForm();
            mapForm.ShowDialog();
        }

        public RequestsListForm()
        {
            InitializeComponent();
            LoadStatusFilter();
            SetDefaultDateFilter();
            LoadRequests();
            ApplyCustomColors();
        }

        private void ApplyCustomColors()
        {

            Color customColor = ColorTranslator.FromHtml("#c0c0c0");

            textBoxSearch.BackColor = customColor;
            dateTimePickerFrom.CalendarMonthBackground = customColor;
            dateTimePickerTo.CalendarMonthBackground = customColor;
            comboBoxStatus.BackColor = customColor;
            buttonApplyFilter.BackColor = customColor;
            buttonResetFilter.BackColor = customColor;
            buttonRefresh.BackColor = customColor;
            textBoxSearch.BorderStyle = BorderStyle.None;
            comboBoxStatus.FlatStyle = FlatStyle.Flat;
            //dateTimePickerFrom.FlatStyle = FlatStyle.Flat;
            //dateTimePickerTo.FlatStyle = FlatStyle.Flat;
            buttonApplyFilter.FlatStyle = FlatStyle.Flat;
            buttonApplyFilter.FlatAppearance.BorderSize = 0;
            buttonResetFilter.FlatStyle = FlatStyle.Flat;
            buttonResetFilter.FlatAppearance.BorderSize = 0;
            buttonRefresh.FlatStyle = FlatStyle.Flat;
            buttonRefresh.FlatAppearance.BorderSize = 0;
        }

        private void buttonOpenGallery_Click(object sender, EventArgs e)
        {
            var galleryForm = new GalleryForm();
            galleryForm.ShowDialog();
        }

        private void LoadStatusFilter()
        {
            comboBoxStatus.Items.Clear();
            comboBoxStatus.Items.AddRange(new object[] { "Все", "Новые", "В обработке", "Завершенные", "Отклоненные", "Отмененные" });
            comboBoxStatus.SelectedIndex = 0;
        }

        private void SetDefaultDateFilter()
        {
            dateTimePickerFrom.Value = DateTime.Now.AddDays(-3);
            dateTimePickerTo.Value = DateTime.Now;
        }

        private void LoadRequests()
        {
            try
            {
                Cursor = Cursors.WaitCursor;

                // Получаем параметры фильтрации
                string statusFilter = GetStatusFilter();
                DateTime startDate = dateTimePickerFrom.Value.Date;
                DateTime endDate = dateTimePickerTo.Value.Date;
                string searchText = textBoxSearch.Text.Trim();

                // Загружаем данные
                _allRequests = DatabaseHelper.GetRequests(statusFilter, startDate, endDate, searchText);
                ApplySorting();
                for (int i = 0; i < dataGridViewRequests.ColumnCount; i++)
                {
                    dataGridViewRequests.Columns[i].Visible = dataGridViewRequests.Columns[i].HeaderText.StartsWith(" ");
                }
                labelResultsCount.Text = $"Найдено: {_filteredRequests.Count} заявок";
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Ошибка при загрузке заявок: {ex.Message}", "Ошибка",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            finally
            {
                Cursor = Cursors.Default;
            }
        }

        private string GetStatusFilter()
        {
            string selectedStatus = comboBoxStatus.SelectedItem?.ToString();

            switch (selectedStatus)
            {
                case "Все":
                    return null;
                case "Новые":
                    return "new";
                case "В обработке":
                    return "in_progress";
                case "Завершенные":
                    return "completed";
                case "Отклоненные":
                    return "rejected";
                case "Отмененные":
                    return "cancelled";
                default:
                    return null;
            }
        }

        private void ApplySorting()
        {
            if (_allRequests == null) return;

            var sortColumn = dataGridViewRequests.SortedColumn;
            var sortDirection = dataGridViewRequests.SortOrder;

            IEnumerable<Request> sortedRequests = _allRequests;

            if (sortColumn != null && sortDirection != SortOrder.None)
            {
                switch (sortColumn.Name)
                {
                    case "ColumnDescription":
                        if (sortDirection == SortOrder.Ascending)
                            sortedRequests = sortedRequests.OrderBy(r => r.RequestText);
                        else
                            sortedRequests = sortedRequests.OrderByDescending(r => r.RequestText);
                        break;
                    case "ColumnDate":
                        if (sortDirection == SortOrder.Ascending)
                            sortedRequests = sortedRequests.OrderBy(r => r.CreatedAt);
                        else
                            sortedRequests = sortedRequests.OrderByDescending(r => r.CreatedAt);
                        break;
                    case "ColumnStatus":
                        if (sortDirection == SortOrder.Ascending)
                            sortedRequests = sortedRequests.OrderBy(r => r.StatusText);
                        else
                            sortedRequests = sortedRequests.OrderByDescending(r => r.StatusText);
                        break;
                    case "ColumnLocation":
                        if (sortDirection == SortOrder.Ascending)
                            sortedRequests = sortedRequests.OrderBy(r => r.LocationText);
                        else
                            sortedRequests = sortedRequests.OrderByDescending(r => r.LocationText);
                        break;
                    case "ColumnUser":
                        if (sortDirection == SortOrder.Ascending)
                            sortedRequests = sortedRequests.OrderBy(r => r.UserDisplayName);
                        else
                            sortedRequests = sortedRequests.OrderByDescending(r => r.UserDisplayName);
                        break;
                }
            }
            else
            {
                // Сортировка по умолчанию - по дате (новые сверху)
                sortedRequests = sortedRequests.OrderByDescending(r => r.CreatedAt);
            }

            _filteredRequests = sortedRequests.ToList();
            dataGridViewRequests.DataSource = _filteredRequests;

            // Обновляем номера строк
            UpdateRowNumbers();
        }

        private void UpdateRowNumbers()
        {
            foreach (DataGridViewRow row in dataGridViewRequests.Rows)
            {
                row.HeaderCell.Value = (row.Index + 1).ToString();
            }
            dataGridViewRequests.AutoResizeRowHeadersWidth(DataGridViewRowHeadersWidthSizeMode.AutoSizeToAllHeaders);
        }

        private void buttonApplyFilter_Click(object sender, EventArgs e)
        {
            LoadRequests();
        }

        private void buttonResetFilter_Click(object sender, EventArgs e)
        {
            comboBoxStatus.SelectedIndex = 0;
            SetDefaultDateFilter();
            textBoxSearch.Clear();
            LoadRequests();
        }

        private void textBoxSearch_KeyPress(object sender, KeyPressEventArgs e)
        {
            if (e.KeyChar == (char)Keys.Enter)
            {
                LoadRequests();
                e.Handled = true;
            }
        }

        private void dataGridViewRequests_ColumnHeaderMouseClick(object sender, DataGridViewCellMouseEventArgs e)
        {
            ApplySorting();
        }

        private void dataGridViewRequests_CellDoubleClick(object sender, DataGridViewCellEventArgs e)
        {
            if (e.RowIndex >= 0 && e.RowIndex < _filteredRequests.Count)
            {
                var selectedRequest = _filteredRequests[e.RowIndex];
                OpenRequestDetails(selectedRequest);
            }
        }

        private void OpenRequestDetails(Request request)
        {
            RequestDetailsForm detailsForm = new RequestDetailsForm(request);
            detailsForm.ShowDialog();
        }

        private void buttonRefresh_Click(object sender, EventArgs e)
        {
            LoadRequests();
        }

        private void dateTimePickerFrom_ValueChanged(object sender, EventArgs e)
        {
            if (dateTimePickerFrom.Value > dateTimePickerTo.Value)
            {
                dateTimePickerTo.Value = dateTimePickerFrom.Value;
            }
        }

        private void dateTimePickerTo_ValueChanged(object sender, EventArgs e)
        {
            if (dateTimePickerTo.Value < dateTimePickerFrom.Value)
            {
                dateTimePickerFrom.Value = dateTimePickerTo.Value;
            }
        }
    }
}