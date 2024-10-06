"""
Firmware: smartrace_analog_hw.py
Platform: Raspberry Pi Pico W
Version: 0.1 (2024/08/05)
Github Repo:

Description:
firmware for the Raspberry Pi Pico W that can replace a phone running Smartrace Connect APP.
The Smartrace Connect APP uses the phone camera to identify laps on analog slot car tracks.

Using the camera has some drawbacks, like changes in illumination (shadows moving) or bumps
to the track could result in wrong lap time registered.

Using an infrared portal placed in the slot of the track can recognize the car guide passing by.
This is what this firmware does.

IR portal are considered active low.
Communication with smartrace is done over WLAN and via Websockets protocol

Configuration parameters should be provided in the config.py file, check the config_example.py
for reference.

Fill sensor_pins with connection to be observed
Input pin reads from the IR sensors

For detail instruction check the Readme on Github repository

Implementation:
4 routines are being executed simultaneously + an interrupt
Interrput -> activated by a falling edge on an input pin.
note: data transfer between ISR and asyncio loop occurs over the 'data' bytearray

loop 1) wifi_connection_task -> handles WiFi connections
loop 2) ws_transmission_task -> handles Websocket connections
loop 3) check_isr_data_task -> regularly block ISR from happening and reads if 'data' bytearray
contains info to be transmitted. values will be exported to lap_time_queue.
loop 4) smartrace_reconnect -> workaround to casual 'connection aborted' exception
"""

import asyncio
from machine import Pin, disable_irq, enable_irq
from micropython import const, alloc_emergency_exception_buf
from collections import deque
from time import ticks_ms
from struct import pack_into, pack, unpack_from
import network as net
import uwebsockets.client
from config import config_wifi, config_smartrace, config_hardware

# global variable and ISR configuration
alloc_emergency_exception_buf(100)

DATASIZE = const(5)
ARRAYSIZE = const(10)
index = 0
data = bytearray(ARRAYSIZE * pack('!BI', 0, 0))

lap_time_queue = deque((), 20)


class CustomPin:
    def __init__(self, pin_id: int, lane_id: int, sensor_position: str) -> None:
        self.pin = Pin(pin_id, Pin.IN, Pin.PULL_UP)
        self.pin_id = pin_id
        self.pin.irq(self._pin_irq, trigger=Pin.IRQ_FALLING, hard=True)
        self.sensor_position = sensor_position
        self.lane_id = lane_id

    def _pin_irq(self, pin: Pin):
        global data, index, DATASIZE, ARRAYSIZE
        if index < ARRAYSIZE:
            pack_into('!BI', data, index * DATASIZE, self.pin_id, ticks_ms())
            index += 1


"""
# direct config
sensor_pins = {
    21: CustomPin(21, 1, 'FL'),  # finish line 1
    27: CustomPin(27, 2, 'FL'),  # finish line 2
}
"""

# pin allocation for IR portals inputs
# pin setup taken from config files
sensor_pins = {}

for pin in config_hardware:
    # example of pin: (21, 1, 'FL'),  # finish line for lane 1 on GPIO21
    sensor_pins[pin[0]] = CustomPin(pin[0], pin[1], pin[2])

# Wi-Fi related global variables
wifi = net.WLAN(net.STA_IF)
wifi.active(1)

# Smartrace connect related global variables
websocket = None
websocket_handshake_status = False
smartrace_need_reconnect_flag = False


# loop 3
async def check_isr_data_task():
    global index, data, DATASIZE, sensor_pins, lap_time_queue
    while True:
        await asyncio.sleep_ms(100)
        # check for new data from ISR
        irq_state = disable_irq()
        if index > 0:
            print(f"minigo/check_isr_data: data in pipeline {index}")
            for data_id in range(index):
                pin_id, timestamp = unpack_from('!BI', data, data_id * DATASIZE)
                pin = sensor_pins[pin_id]
                lap_time_queue.append((pin.sensor_position, pin.lane_id, timestamp))
            index = 0
        enable_irq(irq_state)


async def wifi_connect(SSID: str, pwd: str):
    global wifi

    await asyncio.sleep_ms(50)
    if wifi.status() != net.STAT_CONNECTING:
        print("WiFi connecting attempt")
        wifi.connect(SSID, pwd)
        print("WiFi connection status: " + str(wifi.isconnected()))


async def wifi_connection_task():
    global wifi
    global websocket_handshake_status

    while not wifi.isconnected():
        await wifi_connect(config_wifi["SSID"], config_wifi["password"])
        await asyncio.sleep_ms(3000)
        if wifi.isconnected():
            print("Wifi ifconfig: {}".format(wifi.ifconfig()))
        else:
            print("Wifi not connected.")
    while not websocket_handshake_status:
        await ws_handshake()
        await asyncio.sleep_ms(500)
        await smartrace_connect()
        await asyncio.sleep_ms(500)
    else:
        websocket_handshake_status = True



    while True:

        # try to reconnect if interrupted
        while not wifi.isconnected():
            await wifi_connect(config_wifi["SSID"], config_wifi["password"])
            await asyncio.sleep_ms(2000)
        await asyncio.sleep_ms(250)


class WebSocketHandshakeError(Exception):
    pass


async def ws_handshake():
    global websocket
    global websocket_handshake_status
    server_address = f"ws://{config_smartrace["server"]}:{config_smartrace["port"]}"
    try:
        await asyncio.sleep_ms(250)
        print(f"Websocket connecting to... {server_address}")
        # connect to test socket server with random client number
        try:
            websocket = uwebsockets.client.connect(server_address)
        except Exception as e:
            print(e)
            raise WebSocketHandshakeError('Websocket connecting error.')
        print("websocket connecting...done")
        #websocket_handshake_status = True

    except WebSocketHandshakeError as e:
        print(e)
        websocket_handshake_status = False




async def smartrace_connect():
    global websocket
    global websocket_handshake_status

    await asyncio.sleep_ms(30)
    # connect to smartrace
    print("1")
    websocket.send('{"type":"api_version"}')
    await asyncio.sleep_ms(30)
    # drop 3 messages from smartrace
    print("2")
    websocket.recv()
    await asyncio.sleep_ms(30)
    websocket.recv()
    await asyncio.sleep_ms(30)
    websocket.recv()
    await asyncio.sleep_ms(30)
    # send configuration for analog sensor
    print("3")
    websocket.send('{"type": "controller_set", "data": {"controller_id": "Z"}}')
    await asyncio.sleep_ms(30)
    websocket_handshake_status = True
    print("...handshaked.")


def ws_message_create(lap_time):
    # see check_isr_data
    # lap_time[0] is either FL (finish line), PE (pit enter), PL (pit leave), or FLPL (finish line + pit leave)
    # lap_time[1] is the lane indicator 1,2 or 3
    # lap_time[2] is the timestamp in ms
    if lap_time[0] == 'FL':
        return '{"type":"analog_lap","data":{"timestamp":' + str(lap_time[2]) + ',"controller_id":' + str(
            lap_time[1]) + '}}'
    if lap_time[0] == 'PE':
        return '{"type":"analog_pit_enter","data":{"controller_id":' + str(lap_time[1]) + '}}'
    if lap_time[0] == 'PL':
        return '{"type":"analog_pit_leave","data":{"controller_id":' + str(lap_time[1]) + '}}'
    if lap_time[0] == 'FLPL':
        return ('{"type":"analog_pit_leave","data":{"controller_id":' + str(lap_time[1]) +
                '}}##{"type":"analog_lap","data":{"timestamp":' + str(lap_time[2]) + ',"controller_id":' + str(
                    lap_time[1]) + '}}')


async def ws_transmission_task():
    global lap_time_queue
    global websocket_handshake_status
    global wifi
    global smartrace_need_reconnect_flag

    #counter = 0
    lap_data_backup = ('FL', 12, 1000)

    while True:
        # loop and wait for data in the shared queue
        while len(lap_time_queue) == 0:
            await asyncio.sleep_ms(50)

        print(f"ws_transmission_task: {len(lap_time_queue)} data available")

        if not websocket_handshake_status:
            await ws_handshake()
            websocket_handshake_status = True

        if websocket_handshake_status & wifi.isconnected():
            lap_time = lap_time_queue.popleft()
            print(f"ws_transmission_task: data to be transferred {lap_time}")

            # create message to encode
            mgs = ws_message_create(lap_time)
            #counter += 1
            #print(f"ws_transmission_task: counter {counter}")
            try:
                for m in mgs.split('##'):
                    websocket.send(m)
                lap_data_backup = lap_time
            except:
                print('')
                print('***** ERROR *****')
                print('websocket.send real exception caught')
                print('***** ERROR *****')
                lap_time_queue.appendleft(lap_time)
                lap_time_queue.appendleft(lap_data_backup)
                websocket_handshake_status = False
                smartrace_need_reconnect_flag = True
                #await asyncio.sleep_ms(2000)
            await asyncio.sleep_ms(10)

        await asyncio.sleep_ms(10)


async def smartrace_reconnect_task():
    global websocket
    global smartrace_need_reconnect_flag
    control_pin = Pin(2, Pin.IN, Pin.PULL_UP)

    while True:
        if smartrace_need_reconnect_flag and not control_pin.value():
            # try force device registration again
            websocket.send('{"type": "controller_set", "data": {"controller_id": "Z"}}')
            smartrace_need_reconnect_flag = False
        await asyncio.sleep_ms(1000)


async def main():
    tasks = [
        wifi_connection_task(),
        ws_transmission_task(),
        check_isr_data_task(),
        smartrace_reconnect_task(),
    ]
    await asyncio.gather(*tasks)


asyncio.run(main())
