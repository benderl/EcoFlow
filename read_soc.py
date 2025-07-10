#!/usr/bin/env python3
from EcoFlowApi import EcoFlowClient

# read key and secret from file
try:
    with open('ef_api_key.txt', 'r') as key_file:
        key, secret = key_file.read().strip().split(':')
except FileNotFoundError as error:
    raise FileNotFoundError(
        "No API key file found. Please create 'ef_api_key.txt' with the format 'key:secret'.") from error
except ValueError as error:
    raise ValueError(
        "Invalid format in 'ef_api_key.txt'. Please use 'key:secret' format.") from error
api_client = EcoFlowClient(key=key, secret=secret)
api_client.connect()

device_list = api_client.device_list()
device_serial_number = None
if not device_list:
    print("No devices found.")
    exit(1)
else:
    for device in device_list:
        if "DELTA 2" in device.get('productName'):
            print(f"Found device: {device.get('productName')} with SN: {device.get('sn')}")
            device_serial_number = device.get('sn')
            break
if not device_serial_number:
    print("No DELTA 2 device found.")
    exit(1)

device_data = api_client.get_data(device_serial_number)
if device_data:
    soc = int(device_data.get('data', {}).get('bms_bmsStatus.soc', 0))
    soh = int(device_data.get('data', {}).get('bms_bmsStatus.soh', 0))
    print(f"State of Charge (SoC) for device with SN '{device_serial_number}': {soc}%")
    print(f"State of Health (SoH) for device with SN '{device_serial_number}': {soh}%")
else:
    print(
        f"No data found for device with SN '{device_serial_number}'.")
