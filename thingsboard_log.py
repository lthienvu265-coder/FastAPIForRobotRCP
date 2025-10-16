import asyncio
import json
import paho.mqtt.client as mqtt
from typing import Any
from unitree_webrtc_connect.constants import RTC_TOPIC, WebRTCConnectionMethod
from unitree_webrtc_connect.webrtc_driver import UnitreeWebRTCConnection

THINGSBOARD_HOST = "demo.thingsboard.io"
ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"
PUBLISH_INTERVAL = 3 

client = mqtt.Client()
client.username_pw_set(ACCESS_TOKEN)
client.connect(THINGSBOARD_HOST, 1883, 60)
client.loop_start()

conn = UnitreeWebRTCConnection(WebRTCConnectionMethod.LocalSTA, ip="192.168.100.101")


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


async def main():
    print("🚀 Connecting to Unitree robot...")
    await conn.connect()

    print("✅ Connected. Sending data to ThingsBoard every 3 seconds... (Ctrl+C to stop)")
    try:
        while True:
            lowstate_data = await get_lowstate(conn)
            client.publish("v1/devices/me/telemetry", json.dumps(lowstate_data["data"]), qos=1)
            print(f"📡 Sent telemetry: {lowstate_data['data']}")
            await asyncio.sleep(PUBLISH_INTERVAL)
    except KeyboardInterrupt:
        print("\n🛑 Stopped by user.")
    finally:
        client.loop_stop()
        client.disconnect()
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())