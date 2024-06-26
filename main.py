from Adafruit_IO import MQTTClient
import requests
import time
from tokens import telegram
from tokens import mqtt_adress
from devices import deviceIds
from devices import devices

setup = []
game_setup = []
request = []
setup_devices = []
feeds = ['device1', 'admin']
connection_requested = []
last_message = False

bot_token = telegram['bot_token']
username = mqtt_adress['username']
io_key = mqtt_adress['io_key']
bot_api = f'https://api.telegram.org/bot{bot_token}/'

def connect_mqtt():
    client = MQTTClient(username, io_key)

    client.on_connect = connected
    client.on_disconnect = disconnected
    client.on_message = message
    client.connect()
    client.loop_background()

def connected(client):
    print('Connected to Adafruit IO!')
    
    # Abonnieren Sie alle Feeds in der Liste
    for feed in feeds:
        print(f'Subscribing to {feed}')
        client.subscribe(feed)

def disconnected(client):
    print('Disconnected from Adafruit IO!')

def message(client, feed_id, payload):
    global last_message
    print(f'Feed {feed_id} received new value: {payload}')
    last_message = (feed_id, payload)
    process_mqtt(feed_id, payload)

def add_user(user_id, device_id):
    devices[user_id] = device_id
    print(devices)

def get_device_id(user_id):
    return devices.get(user_id)

def get_user(device_id):
    return devices.get(device_id, None)

def get_updates(offset=None):
    url = bot_api + 'getUpdates'
    params = {'timeout': 100, 'offset': offset}
    response = requests.get(url, params=params)
    return response.json()

def send_message(chat_id, text):
    """Sendet eine Nachricht an einen bestimmten Chat."""
    url = bot_api + 'sendMessage'
    params = {'chat_id': chat_id, 'text': text}
    requests.get(url, params=params)

def send_mqtt(device_adress, action):
    feed_key = device_adress
    data = {'value': action}
    print(bot_token, username, io_key, feed_key, data)
    mqtt_api = f'https://io.adafruit.com/api/v2/{username}/feeds/{feed_key}/data'
    headers = {
        'X-AIO-Key': io_key,
        'Content-Type': 'application/json'
    }
    response = requests.post(mqtt_api, headers=headers, json=data)
    if response.status_code in [200, 201]:
        print('Daten erfolgreich hinzugefügt')
    else:
        print(f'Fehler bei der Anfrage: Status {response.status_code}, Antwort: {response.text}')
    return response

def process_mqtt(feed, message):
    print('processing')
    if feed in connection_requested:
        print('in da loop')
        print(message)
        print(type(message))
        chat_id = get_user(feed)
        if message == '200':
            print('should work')
            answer = 'your device was registered and connected to your accound succesfully'
        else:
            answer = 'something went wrong :('
        print(chat_id, answer)
        send_message(chat_id, answer)
    print('not the right loop')

def process_messages(text, chat_id):
    print("new message: ", text)
    answer = 'something went wrong'  # Ensure 'answer' is always initialized
    if chat_id in setup:
        if text in deviceIds:
            send_mqtt(text, 'connection requested')
            request.append(text)
            setup_devices.append(text)
            answer = "Thank you! Now press the button on your device so we can finish the setup."
            add_user(chat_id, text)
            connection_requested.append(text)
            setup.remove(chat_id)
        else:
            answer = "There is no device with this id"
    if chat_id in game_setup:
        try:
            interval = int(text)
            action = f'intervall={interval}'
            print(action)
            device_address = get_device_id(chat_id)
            print(device_address)
            send_mqtt(device_address, action)
            game_setup.remove(chat_id)
            answer = "Your game is now set up. Send any /startGame to start."
        except ValueError:
            answer = "Please enter a valid number"

    if '/start' in text:
        answer = "Welcome! Let's register your device. What is your device id?"
        setup.append(chat_id)
    elif 'ping' in text:
        answer = "pong"
    elif '/game' in text:
        answer = "Ok! Let's start a game. How often should the device send a photo. Enter the number of minutes"
        game_setup.append(chat_id)
    send_message(chat_id, answer)

def main():
    offset = None
    while True:
        global last_message
        if last_message:
            feed_id, payload = last_message
            print(f'Handling new message from {feed_id}: {payload}')
            last_message = None
        updates = get_updates(offset)
        print(offset)
        if 'result' in updates:
            for update in updates['result']:
                if 'message' in update:
                    chat_id = update['message']['chat']['id']
                    text = update['message']['text']
                    process_messages(text, chat_id)
                    offset = update['update_id'] + 1
        time.sleep(1)

if __name__ == '__main__':
    print("programm gestartet")
    send_mqtt('admin', 'bot online')
    connect_mqtt()
    listeningforEvent = False
    main()