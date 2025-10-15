# main.py
from fastapi import FastAPI
import asyncio
from typing import Any
from go2_webrtc_driver.constants import RTC_TOPIC, SPORT_CMD, WebRTCConnectionMethod
from go2_webrtc_driver.webrtc_driver import Go2WebRTCConnection

app = FastAPI()
conn = Go2WebRTCConnection(WebRTCConnectionMethod.LocalSTA, ip="192.168.100.101")

@app.post("/stand_up")
async def stand_up():
    await conn.connect()
    await conn.datachannel.pub_sub.publish_request_new(
        RTC_TOPIC["SPORT_MOD"], 
        {"api_id": SPORT_CMD["StandUp"]}
    )

@app.post("/stand_down")
async def stand_down():
    await conn.connect()
    await conn.datachannel.pub_sub.publish_request_new(
        RTC_TOPIC["SPORT_MOD"], 
        {"api_id": SPORT_CMD["StandDown"]}
    )

@app.post("/status")
async def status():
    await conn.connect()

    loop = asyncio.get_running_loop()
    future: asyncio.Future[Any] = loop.create_future()

    def sportmodestatus_callback(message):
        # Set result only if it hasn’t been set yet
        if not future.done():
            future.set_result(message["data"])

    # Subscribe to your topic
    conn.datachannel.pub_sub.subscribe(
        RTC_TOPIC["LF_SPORT_MOD_STATE"],
        sportmodestatus_callback
    )

    try:
        # Wait for the callback or timeout
        current_message = await asyncio.wait_for(future, timeout=5.0)
        return {"status": "ok", "data": current_message}
    except asyncio.TimeoutError:
        return {"status": "timeout", "message": "No message received within 5 seconds"}
