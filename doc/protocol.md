# Smartrace Websocket Protocol

back to main page: [Smartrace analog hardware interface](../Readme.md)

For the geek among us, here some details about the communication between _Smartrace Connect_ server and client.
The communication occurs over Websockets. The script [smartrace_ws_bridge.py](reverse_eng/smartrace_ws_bridge.py) 
can be used to printout what messages server and clients exchange. An example is visible in 
[smartrace_ws_bridge_output.txt](reverse_eng/smartrace_ws_bridge_output.txt)

The sensor sends an api request
```
sensor >>> smartrace
{"type":"api_version"}
```

_Smartrace_ sends 3 replies 
- Overview of assigned controller and users
- Subscription tcircuit_diagram_websocket_reset_btno something?!? :)
- Api version

```
smartrace >>> sensor
{"type":"update_controller_data","data":
{"1":{"color":"rgb(0, 0, 0)","backgroundColor":"rgb(28, 237, 175)","driver":"Nic","car":"BMW M4"},
"2":{"color":"black","backgroundColor":"rgb(254, 249, 17)","driver":"Alex","car":"Ferrari 488"},
"3":{"color":"rgb(0, 0, 0)","backgroundColor":"rgb(188, 195, 188)","driver":"Non assegnato","car":"Non assegnato"},
"4":{"color":"rgb(0, 0, 0)","backgroundColor":"rgb(188, 195, 188)","driver":"Non assegnato","car":"Non assegnato"},
"5":{"color":"rgb(0, 0, 0)","backgroundColor":"rgb(188, 195, 188)","driver":"Non assegnato","car":"Non assegnato"},
"6":{"color":"rgb(0, 0, 0)","backgroundColor":"rgb(188, 195, 188)","driver":"Non assegnato","car":"Non assegnato"}}}

smartrace >>> sensor
{"type":"update_server_info","data":{"is_subscribed":false}}

smartrace >>> sensor
{"type":"api_version","data":{"api_version":7}}
```

The sensor registers itself as an analog sensor
```
sensor >>> smartrace
{"type":"controller_set","data":{"controller_id":"Z"}}
```

The sensor is nor registered, from now one laps are recorded with messages like:
```
sensor >>> smartrace
{"type":"analog_lap","data":{"timestamp":1722773108999,"controller_id":2}}
{"type":"analog_lap","data":{"timestamp":1722773109119,"controller_id":1}}
```

while additional features, like pit stop can be activated with messages like:
```
sensor >>> smartrace
{"type":"analog_pit_enter","data":{"controller_id":2}}
{"type":"analog_pit_leave","data":{"controller_id":2}}
```
