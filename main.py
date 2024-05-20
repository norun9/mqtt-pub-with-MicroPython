import time
from umqtt.robust import MQTTClient
from bmp180_scd41 import bmp180_read_data
import network
import uasyncio as asyncio

TEMP_TOPIC = "i483/sensors/s2410014/BMP180/temperature"
PRESSURE_TOPIC = "i483/sensors/s2410014/BMP180/air_pressure"
SSID = 'JAISTALL'
SSID_PASSWORD = ''


def sub(topic, msg):
    print(f'Received message {msg.decode()} on topic {topic}')


async def connect_to_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    print(f"MAC: {wlan.config('mac').hex()}")
    if not wlan.isconnected():
        print(f"Connecting to network {SSID}...")
        wlan.connect(SSID, SSID_PASSWORD)
        for _ in range(30):  # attempt wifi connection for 30seconds
            if wlan.isconnected():
                break
            print(".", end="")
            await asyncio.sleep(1)
    if wlan.isconnected():
        print("\nConnected to WiFi")
        print(f"network config: {wlan.ifconfig()}")
    else:
        print("\nFailed to connect to WiFi")
        raise


async def net_setup() -> MQTTClient:
    await connect_to_wifi()
    mqtt_client = MQTTClient(client_id="test", server="150.65.230.59")
    mqtt_client.set_callback(sub)

    try:
        mqtt_client.connect()
        print("Connected to MQTT Broker")
    except Exception as e:
        print(f"Failed to connect to MQTT Broker: {e}")
        raise

    try:
        mqtt_client.subscribe(TEMP_TOPIC)
        mqtt_client.subscribe(PRESSURE_TOPIC)
    except Exception as e:
        print(f"Failed to subscribe to topics: {e}")
        raise
    return mqtt_client


async def publish_sensor_data(client):
    try:
        while True:
            # Read temperature and pressure from BMP180
            temperature, air_pressure = bmp180_read_data()
            # scd41_data = scd41_read_data()
            # Publish the sensor data to MQTT Broker
            try:
                client.publish(TEMP_TOPIC, str(temperature))
                client.publish(PRESSURE_TOPIC, str(air_pressure))
                print(f"Published temperature {temperature} to {TEMP_TOPIC}")
                print(f"Published pressure {air_pressure} to {PRESSURE_TOPIC}")
            except Exception as e:
                print(f"Failed to publish MQTT message: {e}")
                raise

            # Wait before sending next reading
            await asyncio.sleep(1)  # Adjust delay as needed
    except asyncio.CancelledError:
        print("Publish task cancelled")
        client.disconnect()


async def poll_mqtt(client):
    try:
        while True:
            client.check_msg()
            await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        print("MQTT poll task cancelled")
        client.disconnect()


async def main():
    client = await net_setup()
    publish_task = asyncio.create_task(publish_sensor_data(client))
    poll_task = asyncio.create_task(poll_mqtt(client))

    try:
        await asyncio.gather(publish_task, poll_task)
    except KeyboardInterrupt:
        publish_task.cancel()
        poll_task.cancel()
        await asyncio.gather(publish_task, poll_task, return_exceptions=True)
        print("Disconnected from MQTT Broker")
        client.disconnect()


async def all_tasks():
    await main()

asyncio.run(all_tasks())