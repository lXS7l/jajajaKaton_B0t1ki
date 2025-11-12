using System;
using System.Collections.Generic;
using System.Windows.Forms;
using System.Runtime.InteropServices;

namespace Adminpanel
{
    [ComVisible(true)]
    public partial class MapForm : Form
    {
        private List<Request> _requests;
        private string _yandexMapsApiKey = "08b9b5cd-dcf6-43fd-a3e8-a0945f872261";

        public MapForm()
        {
            InitializeComponent();
            LoadRequests();
            //InitializeMap();
            InitializeAsync();
        }

        private async void InitializeAsync()
        {
            await webView21.EnsureCoreWebView2Async(null);

            // Создаем и регистрируем объект для скриптинга
            var scriptObject = new ScriptCallbackObject(this);
            webView21.CoreWebView2.AddHostObjectToScript("external", scriptObject);

            InitializeMap();
        }

        private void LoadRequests()
        {
            _requests = DatabaseHelper.GetRequestsWithCoordinates();
        }

        private async void InitializeMap()
        {
            if (_requests.Count == 0)
            {
                MessageBox.Show("Нет заявок с координатами для отображения на карте", "Информация",
                    MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            // Инициализация WebView2
            await webView21.EnsureCoreWebView2Async(null);

            string htmlContent = GenerateMapHtml();
            webView21.NavigateToString(htmlContent);
        }


        private string GenerateMapHtml()
        {
            var places = new List<string>();

            foreach (var request in _requests)
            {
                if (request.HasLocation)
                {
                    string placemark = $@"
                    {{
                        id: {request.Id},
                        coords: [{request.LatitudeString}, {request.LongitudeString}],
                        number: '{EscapeJavaScriptString(request.RequestNumber)}',
                        text: '{EscapeJavaScriptString(request.ShortDescription)}',
                        status: '{EscapeJavaScriptString(request.StatusText)}',
                        date: '{EscapeJavaScriptString(request.FormattedDate)}'
                    }}";
                    places.Add(placemark);
                }
            }

            string placesArray = "[" + string.Join(",", places) + "]";

            return $@"
<!DOCTYPE html>
<html>
<head>
    <meta charset='utf-8' />
    <title>Яндекс Карта - Заявки</title>
    <script src='https://api-maps.yandex.ru/2.1/?apikey={_yandexMapsApiKey}&lang=ru_RU' type='text/javascript'></script>
    <style>
        body, html, #map {{
            width: 100%;
            height: 100%;
            margin: 0;
            padding: 0;
        }}
    </style>
</head>
<body>
    <div id='map'></div>
<script type='text/javascript'>
    async function callCSharpMethod(requestId) {{
        try {{
            // Получаем ссылку на зарегистрированный объект
            const external = window.chrome.webview.hostObjects.external;
            // Вызываем метод асинхронно (await преобразует результат в Promise)
            await external.ShowRequestDetails(requestId);
        }} catch (error) {{
            console.error('Ошибка вызова C# метода:', error);
        }}
    }}
</script>
    <script type='text/javascript'>
        ymaps.ready(initMap);

        function initMap() {{
            var map = new ymaps.Map('map', {{
                center: [55.751244, 37.618423], // Москва по умолчанию
                zoom: 10
            }});

            var places = {placesArray};

            // Создаем коллекцию меток
            var objectManager = new ymaps.ObjectManager({{
                clusterize: true,
                gridSize: 32,
                clusterDisableClickZoom: true
            }});

            // Настройки внешнего вида кластеров
            objectManager.clusters.options.set({{
                preset: 'islands#invertedVioletClusterIcons',
                clusterDisableClickZoom: true
            }});

            // Настройки внешнего вида меток
            objectManager.objects.options.set({{
                preset: 'islands#blueDotIcon',
                openBalloonOnClick: true
            }});

            // Добавляем объекты на карту
            objectManager.add(places.map(function(place) {{
                return {{
                    type: 'Feature',
                    id: place.id,
                    geometry: {{
                        type: 'Point',
                        coordinates: place.coords
                    }},
                    properties: {{
                        balloonContentHeader: '<b>Заявка №' + place.number + '</b>',
                        balloonContentBody: 
                            '<p><b>Статус:</b> ' + place.status + '</p>' +
                            '<p><b>Дата:</b> ' + place.date + '</p>' +
                            '<p><b>Описание:</b> ' + place.text + '</p>' +
                            '<p><button onclick=""callCSharpMethod(' + place.id + ')"">Подробнее</button></p>',
                        clusterCaption: 'Заявка №' + place.number
                    }}
                }};
            }}));

            map.geoObjects.add(objectManager);

            // Устанавливаем границы карты чтобы показать все метки
            if (places.length > 0) {{
                map.setBounds(objectManager.getBounds(), {{ checkZoomRange: true }});
            }}

            // Обработчик клика по метке
            objectManager.objects.events.add('click', function (e) {{
                var objectId = e.get('objectId');
                var coords = e.get('coords');
                map.panTo(coords, {{ flying: true }});
            }});
        }}

        function showRequestDetails(requestId) {{
            window.external.ShowRequestDetails(requestId);
        }}
    </script>
</body>
</html>";
        }

        private string EscapeJavaScriptString(string input)
        {
            if (string.IsNullOrEmpty(input)) return "";
            return input.Replace("'", "\\'").Replace("\"", "\\\"").Replace("\r", "").Replace("\n", " ");
        }

        public void ShowRequestDetails(int requestId)
        {
            var request = _requests.Find(r => r.Id == requestId);
            if (request != null)
            {
                var detailsForm = new RequestDetailsForm(request);
                detailsForm.ShowDialog();
            }
        }
    }
    [ComVisible(true)]
    [ClassInterface(ClassInterfaceType.AutoDual)]
    public class ScriptCallbackObject
    {
        private MapForm _form;

        public ScriptCallbackObject(MapForm form)
        {
            _form = form;
        }

        public void ShowRequestDetails(int requestId)
        {
            _form.ShowRequestDetails(requestId);
        }
    }
}