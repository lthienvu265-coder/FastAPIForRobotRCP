import asyncio
import json
import paho.mqtt.client as mqtt
from typing import Any
from unitree_webrtc_connect.constants import RTC_TOPIC, WebRTCConnectionMethod
from unitree_webrtc_connect.webrtc_driver import UnitreeWebRTCConnection

# =========================================
# Configuration
# =========================================
THINGSBOARD_HOST = "demo.thingsboard.io"
PUBLISH_INTERVAL = 3

# List of ThingsBoard devices (each with its own access token)
DEVICES = [
    {"id": 1, "token": "ACCESS_TOKEN_1", "ip": "192.168.100.101"}, # Temperature and Power Voltage 
    {"id": 2, "token": "ACCESS_TOKEN_2", "ip": "192.168.100.101"}, # Foot Force 
    {"id": 3, "token": "ACCESS_TOKEN_3", "ip": "192.168.100.101"}, # BMS State
    {"id": 4, "token": "ACCESS_TOKEN_4", "ip": "192.168.100.101"}  # Roll Pitch Yaw State
    # Add more as needed
]

# =========================================
# Helper to create MQTT client
# =========================================
def create_mqtt_client(token):
    client = mqtt.Client()
    client.username_pw_set(token)
    client.connect(THINGSBOARD_HOST, 1883, 60)
    client.loop_start()
    return client

# =========================================
# Unitree + ThingsBoard connection
# =========================================
async def get_lowstate(conn: UnitreeWebRTCConnection):
    """Wait for one LOW_STATE message via WebRTC."""
    loop = asyncio.get_running_loop()
    future: asyncio.Future[Any] = loop.create_future()

    def lowstate_callback(message):
        if not future.done():
            future.set_result(message["data"])

    conn.datachannel.pub_sub.subscribe(RTC_TOPIC["LOW_STATE"], lowstate_callback)

    try:
        current_message = await asyncio.wait_for(future, timeout=5.0)
        return {"status": "ok", "data": current_message}
    except asyncio.TimeoutError:
        return {"status": "timeout", "message": "No message received within 5 seconds"}

# =========================================
# Main loop for a single robot/device pair
# =========================================
async def handle_robot(device_info):
    conn = UnitreeWebRTCConnection(WebRTCConnectionMethod.LocalSTA, ip=device_info["ip"])
    client = create_mqtt_client(device_info["token"])

    await conn.connect()

    try:
        while True:
            lowstate_data = await get_lowstate(conn)
            if device_info["id"] == 1:
                client.publish("v1/devices/me/telemetry", json.dumps(lowstate_data["data"]), qos=1)
            elif device_info["id"] == 2:
                if "foot_force" in lowstate_data["data"] and isinstance(lowstate_data["data"]["foot_force"], list):
                    lowstate_data["data"]["foot_force"] = {
                        "front_left":  lowstate_data["data"]["foot_force"][0] if len(lowstate_data["data"]["foot_force"]) > 0 else 0,
                        "front_right": lowstate_data["data"]["foot_force"][1] if len(lowstate_data["data"]["foot_force"]) > 1 else 0,
                        "rear_left":   lowstate_data["data"]["foot_force"][2] if len(lowstate_data["data"]["foot_force"]) > 2 else 0,
                        "rear_right":  lowstate_data["data"]["foot_force"][3] if len(lowstate_data["data"]["foot_force"]) > 3 else 0,
                    }
                client.publish("v1/devices/me/telemetry", json.dumps(lowstate_data["data"]["foot_force"]), qos=1)
            elif device_info["id"] == 3:
                client.publish("v1/devices/me/telemetry", json.dumps(lowstate_data["data"]["bms_state"]), qos=1)
            elif device_info["id"] == 4:
                if "rpy" in lowstate_data["data"]["imu_state"] and isinstance(lowstate_data["data"]["imu_state"]["rpy"], list):
                    lowstate_data["data"]["imu_state"]["rpy"] = {
                        "roll":  lowstate_data["data"]["imu_state"]["rpy"][0] if len(lowstate_data["data"]["imu_state"]["rpy"]) > 0 else 0,
                        "pitch": lowstate_data["data"]["imu_state"]["rpy"][1] if len(lowstate_data["data"]["imu_state"]["rpy"]) > 1 else 0,
                        "yarm":   lowstate_data["data"]["imu_state"]["rpy"][2] if len(lowstate_data["data"]["imu_state"]["rpy"]) > 2 else 0
                    }
                client.publish("v1/devices/me/telemetry", json.dumps(lowstate_data["data"]["imu_state"]["rpy"]), qos=1)
            await asyncio.sleep(PUBLISH_INTERVAL)
    except KeyboardInterrupt:
        print(f"\n🛑 Stopped.")
    finally:
        client.loop_stop()
        client.disconnect()
        await conn.close()

# =========================================
# Main entry point
# =========================================
async def main():
    tasks = [handle_robot(device) for device in DEVICES]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
