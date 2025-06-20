#!/usr/local/bin/python3.11

import pprint
import sys
from typing import Optional
import requests
import hmac
import hashlib
import random
import time
import binascii


def hmac_sha256(data, key):
    hashed = hmac.new(key.encode('utf-8'),
                      data.encode('utf-8'), hashlib.sha256).digest()
    return binascii.hexlify(hashed).decode('utf-8')


def get_flattened_map(json_obj, prefix=""):
    def flatten(obj, pre=""):
        result = {}
        if isinstance(obj, dict):
            for k, v in obj.items():
                result.update(flatten(v, f"{pre}.{k}" if pre else k))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                result.update(flatten(item, f"{pre}[{i}]"))
        else:
            result[pre] = obj
        return result
    return flatten(json_obj, prefix)


def get_qstr(params):
    return '&'.join(f"{key}={params[key]}" for key in sorted(params.keys()))


def get_api(url, key, secret, params=None) -> Optional[dict]:
    nonce = str(random.randint(100000, 999999))
    timestamp = str(int(time.time() * 1000))
    headers = {'accessKey': key, 'nonce': nonce, 'timestamp': timestamp}
    sign_str = (get_qstr(get_flattened_map(params)) +
                '&' if params else '') + get_qstr(headers)
    headers['sign'] = hmac_sha256(sign_str, secret)
    print(f"Requesting URL: {url} with params: {params} and headers: {headers}")
    response = requests.get(url, json=params, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        sys.exit(f"Error fetching API data: {response.text}")


def check_if_device_is_online(serial_number, devices_data):
    for device in devices_data.get('data', []):
        if device.get('sn') == serial_number:
            return "online" if device.get('online', 0) == 1 else "offline"
    return "device not found"


def get_ef_data(serial_numbers: list = []) -> None:
    api_url_base = "https://api.ecoflow.com/iot-open/sign"

    # read key and secret from file
    try:
        with open('ef_api_key.txt', 'r') as key_file:
            key, secret = key_file.read().strip().split(':')
    except FileNotFoundError:
        print("API key file 'ef_api_key.txt' not found. Please create it with the format 'key:secret'.")
        sys.exit(1)

    url_device = f'{api_url_base}/device/list'

    # Cache the device list to avoid repeated API calls
    device_list = get_api(url_device, key, secret)
    print("device list:")
    pprint.pprint(device_list)

    if serial_numbers:
        # check if provided serial numbers are valid
        for sn in serial_numbers:
            if not any(device.get('sn') == sn for device in device_list["data"]):
                print(f"Serial number '{sn}' not found in the device list.")
                sys.exit(1)
    else:
        answer = input(
            "Serial number is not provided. Do you want to retrieve data for all found devices? (y/n): ")
        if answer.lower() == 'y':
            for device in device_list["data"]:
                serial_numbers.append(device.get('sn'))
        else:
            # print a numbered list of available devices and serial numbers
            print("Available devices:")
            for i, device in enumerate(device_list["data"]):
                print(f"{i + 1}: {device.get('productName')} {device.get('sn')} ({device.get('deviceName')}) - {'Online' if device.get('online', 0) == 1 else 'Offline'}")
            choice = input(
                "Enter the number of the device you want to retrieve data for: ")
            try:
                choice_index = int(choice) - 1
                if 0 <= choice_index < len(device_list["data"]):
                    serial_numbers.append(
                        device_list["data"][choice_index].get('sn'))
                else:
                    print("Invalid choice. Exiting.")
                    sys.exit(0)
            except ValueError:
                print("Invalid input. Exiting.")
                sys.exit(0)

    for serial_number in serial_numbers:
        url_quota = f'{api_url_base}/device/quota/all?sn={serial_number}'

        online_status = check_if_device_is_online(serial_number, device_list)

        if online_status == "online":
            ef_data = get_api(url_quota, key, secret, {"sn": serial_number})
            pprint.pprint(ef_data)
        else:
            print(f"The device with SN '{serial_number}' is {online_status}.")


if __name__ == '__main__':
    serial_numbers = []
    if len(sys.argv) > 1:
        serial_numbers.append(sys.argv[1])
    get_ef_data(serial_numbers)
