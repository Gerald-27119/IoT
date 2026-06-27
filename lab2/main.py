import network
import time
import machine
import ubinascii
from machine import Pin, time_pulse_us
import dht
import ujson
from umqtt.simple import MQTTClient

WIFI_SSID = "Wokwi-GUEST"
WIFI_PASSWORD = ""

MQTT_CLIENT_ID = "esp32-" + ubinascii.hexlify(machine.unique_id()).decode()

MQTT_BROKER = "broker.mqttdashboard.com"
MQTT_PORT = 1883
MQTT_USER = ""
MQTT_PASSWORD = ""

MQTT_TOPIC_DHT = "adam/wokwi/dht22"
MQTT_TOPIC_DISTANCE = "adam/wokwi/distance"
MQTT_TOPIC_ALL = "adam/wokwi/all"

dht_sensor = dht.DHT22(Pin(15))

trig = Pin(25, Pin.OUT)
echo = Pin(26, Pin.IN)

def connect_wifi():
    print("Connecting to WiFi:", WIFI_SSID)

    sta_if = network.WLAN(network.STA_IF)
    sta_if.active(True)

    if sta_if.isconnected():
        sta_if.disconnect()
        time.sleep(1)

    sta_if.connect(WIFI_SSID, WIFI_PASSWORD)

    timeout_seconds = 20
    start_time = time.time()

    while not sta_if.isconnected():
        print("WiFi status:", sta_if.status())
        time.sleep(1)

        if time.time() - start_time > timeout_seconds:
            print("WiFi connection timeout")
            print("Final WiFi status:", sta_if.status())
            raise RuntimeError("Could not connect to WiFi")

    print("WiFi connected!")
    print("Network config:", sta_if.ifconfig())


def connect_mqtt():
    print("Connecting to MQTT server...")

    client = MQTTClient(
        client_id=MQTT_CLIENT_ID,
        server=MQTT_BROKER,
        port=MQTT_PORT,
        user=MQTT_USER,
        password=MQTT_PASSWORD
    )

    client.connect()

    print("MQTT connected!")
    print("MQTT client id:", MQTT_CLIENT_ID)

    return client


def read_distance_cm():
    trig.value(0)
    time.sleep_us(2)

    trig.value(1)
    time.sleep_us(10)
    trig.value(0)

    duration_us = time_pulse_us(echo, 1, 30000)

    if duration_us < 0:
        return None

    distance_cm = duration_us * 0.0343 / 2
    return round(distance_cm, 2)


def read_dht22():
    dht_sensor.measure()

    return {
        "temperature": round(dht_sensor.temperature(), 2),
        "humidity": round(dht_sensor.humidity(), 2)
    }

connect_wifi()
client = connect_mqtt()

previous_dht_message = ""
previous_distance_message = ""
previous_all_message = ""

while True:
    print("Reading sensors...")

    try:
        dht_data = read_dht22()
        distance_cm = read_distance_cm()

        dht_message = ujson.dumps({
            "temperature": dht_data["temperature"],
            "humidity": dht_data["humidity"]
        })

        distance_message = ujson.dumps({
            "distanceCm": distance_cm
        })

        all_message = ujson.dumps({
            "temperature": dht_data["temperature"],
            "humidity": dht_data["humidity"],
            "distanceCm": distance_cm
        })

        if dht_message != previous_dht_message:
            print("Publishing DHT22:", dht_message)
            client.publish(MQTT_TOPIC_DHT, dht_message)
            previous_dht_message = dht_message

        if distance_message != previous_distance_message:
            print("Publishing distance:", distance_message)
            client.publish(MQTT_TOPIC_DISTANCE, distance_message)
            previous_distance_message = distance_message

        if all_message != previous_all_message:
            print("Publishing all:", all_message)
            client.publish(MQTT_TOPIC_ALL, all_message)
            previous_all_message = all_message

    except Exception as e:
        print("Error:", e)

    time.sleep(1)