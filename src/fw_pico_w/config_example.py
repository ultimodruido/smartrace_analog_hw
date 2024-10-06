config_wifi = {
    "SSID": "ssid",
    "password": "password",
}

config_smartrace = {
    "server": "198.166.144.28",
    "port": 50780,
}

config_hardware = [
    # hardware configuration (GPIO, lane_number, track_point
    # GPIO: refer to Rasberry pinout, image circuit_diagram.png, it can be any light gree GPxx pin
    # lane_number: an integer from 1 to 8 representing the controller in Smartrace
    # track_point: what does it mean when a car is passing by. It can be either
    #     FL -> finish lane
    #     PE -> pit enter
    #     PL -> pit leave
    #     FLPL -> finish line together with pit leave
    # example for lane 1 with 3 different sensors for finish line, pit enter and leave
    (21, 1, 'FL'),  # finish line for lane 1 on GPIO21
    (20, 1, 'PE'),  # pit enter for lane 1 on GPIO20
    (19, 1, 'PL'),  # pit leave for lane 1 on GPIO19
    # example for lave 2 with only 2 sensors, one for pit enter, and one shared for finish line and pit leave
    (6, 2, 'FLPL'),  # finish line together with pit leave for lane 2 on GPIO6
    (7, 2, 'PE'),  # pit enter for lane 2 on GPIO7
]
