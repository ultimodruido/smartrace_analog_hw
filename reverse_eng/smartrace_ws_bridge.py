"""
Smartrace websocket bridge
--------------------------
This simple script can be used to reverce engineer the communication between
'smartware app' and 'smartrace connect' when using it as analo sensor.
SMARTRACE_HOST_IP -> the ip of the server that smartrace uses
BRIDGE_HOST_IP -> the ip of the pc where this script is running
BRIDGE_HOST_PORT -> the port of the server that smartrace uses, is used also in the bridge

In the command lint interface the communication is printed out, an example is
visible in the file smartrace_ws_bridge_output.txt
"""
import asyncio
from websockets.server import serve
from websockets.client import connect
from websockets import ConnectionClosed


#SMARTRACE_HOST_IP = "192.168.178.58"
SMARTRACE_HOST_IP = "192.168.178.26"
BRIDGE_HOST_IP = "192.168.178.61"
BRIDGE_HOST_PORT = 50780

msg_list_to_sensors = []
msg_list_to_tablet = []

websocket_tablet = None

async def sensor2tablet(websocket_sensor, websocket_tablet):
    print("### sensor2tablet ###")
    msg = await websocket_sensor.recv()
    print("tablet <<< sensor")
    print(msg)

    print("Server comm: send to tablet")
    await websocket_tablet.send(msg)


async def tablet2sensor(websocket_sensor, websocket_tablet):
    print("### tablet2sensor ###")
    print("Server comm: read from tablet")
    msg = await websocket_tablet.recv()
    print("tablet >>> sensor")
    print(msg)
    await websocket_sensor.send(msg)




async def bridge_callback(websocket_sensor):
    global websocket_tablet

    await sensor2tablet(websocket_sensor, websocket_tablet) # request api version
    await tablet2sensor(websocket_sensor, websocket_tablet) # list of controller
    await tablet2sensor(websocket_sensor, websocket_tablet) # subscription
    await tablet2sensor(websocket_sensor, websocket_tablet) # api reply -> sensor display available
    await sensor2tablet(websocket_sensor, websocket_tablet) # click on "analog sensor"
    while True:
        await sensor2tablet(websocket_sensor, websocket_tablet)



async def bridge_server():

    async with serve(bridge_callback, BRIDGE_HOST_IP, BRIDGE_HOST_PORT) as websocket:
        await asyncio.Future()


async def smartrace_client():
    # connect to tablet only when sensor tried to connect
    #while len(msg_list_to_tablet) == 0:
    #    await asyncio.sleep(0.5)

    url = f"ws://{SMARTRACE_HOST_IP}:{BRIDGE_HOST_PORT}"
    print(url)
    global websocket_tablet
    while True:
        try:
            async with connect(url) as websocket:
                # register websocket_sensor reference
                websocket_tablet = websocket

                while websocket_tablet is not None:
                    await asyncio.sleep(0.2)

        except ConnectionClosed:
            websocket_tablet = None
            await asyncio.sleep(0.2)
            continue


# Run both tasks.
async def main():

    tasks = [
        bridge_server(),
        smartrace_client(),
    ]
    await asyncio.gather(*tasks)


asyncio.run(main())
