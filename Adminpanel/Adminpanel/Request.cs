using System;
using System.Globalization;

namespace Adminpanel
{
    public class Request
    {
        public int Id { get; set; }
        public string RequestNumber { get; set; }
        public string RequestText { get; set; }
        public string Status { get; set; }
        public DateTime CreatedAt { get; set; }
        public string UserFullName { get; set; }
        public double? Latitude { get; set; }
        public double? Longitude { get; set; }
        public string PhotoUrl { get; set; }
        public string VideoUrl { get; set; }

        public bool HasLocation => Latitude.HasValue && Longitude.HasValue;
        public bool HasPhoto => !string.IsNullOrEmpty(PhotoUrl);
        public bool HasVideo => !string.IsNullOrEmpty(VideoUrl);

        public string ShortDescription
        {
            get
            {
                if (string.IsNullOrEmpty(RequestText))
                    return "Без описания";

                return RequestText.Length > 100
                    ? RequestText.Substring(0, 100) + "..."
                    : RequestText;
            }
        }

        public string FormattedDate => CreatedAt.ToString("dd.MM.yyyy HH:mm");

        public string StatusText
        {
            get
            {
                switch (Status)
                {
                    case "new":
                        return "Новая";
                    case "in_progress":
                        return "В обработке";
                    case "completed":
                        return "Завершена";
                    case "rejected":
                        return "Отклонена";
                    case "cancelled":
                        return "Отменена";
                    default:
                        return Status;
                }
                ;
            }
        }

        // Форматирование координат с ТОЧКОЙ в качестве разделителя
        public string LatitudeString => Latitude?.ToString("F6", CultureInfo.InvariantCulture) ?? "0";
        public string LongitudeString => Longitude?.ToString("F6", CultureInfo.InvariantCulture) ?? "0";

        public string LocationText => HasLocation ? "Есть" : "Нет";
        public string UserDisplayName => string.IsNullOrEmpty(UserFullName) ? "Аноним" : UserFullName;
    }
}