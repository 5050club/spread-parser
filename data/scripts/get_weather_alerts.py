import requests

alerts_url = 'https://api.weather.gov/alerts/active'

lon=-81.37
lat=30.24

payload = {
    'status': 'actual',
    'message_type': 'alert',
    'point': f'{round(lat, 4)},{round(lon, 4)}'
}

headers = {
    'User-Agent': '(jbnation.com, jbyroads@gmail.com)'
}

alerts = requests.get(alerts_url, payload, headers=headers)

print(alerts.json())