#!/usr/bin/env python3

import pprint
import sys
from typing import Optional
import requests
import hmac
import hashlib
import random
import time
import binascii


class EcoflowClient():
    _api_url_base = "https://api.ecoflow.com/iot-open/sign"
    _url_device_list: Optional[str] = None
    _url_device_quota: Optional[str] = None
    _devices_data: Optional[dict] = None

    def __init__(self, key: str, secret: str):
        self._key = key
        self._secret = secret
        self._url_device_list = f'{self._api_url_base}/device/list'
        self._url_device_quota = f'{self._api_url_base}/device/quota/all?sn='

    def _hmac_sha256(self, data: str) -> str:
        hashed = hmac.new(self._secret.encode('utf-8'),
                          data.encode('utf-8'), hashlib.sha256).digest()
        return binascii.hexlify(hashed).decode('utf-8')

    def _get_flattened_map(self, json_obj, prefix: Optional[str] = ""):
        def flatten(obj, pre: Optional[str] = ""):
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

    def _get_query_str(self, params: dict) -> str:
        return '&'.join(f"{key}={params[key]}" for key in sorted(params.keys()))

    def _get_api(self, url: str, params: any = None) -> Optional[dict]:
        nonce = str(random.randint(100000, 999999))
        timestamp = str(int(time.time() * 1000))
        headers = {'accessKey': self._key,
                   'nonce': nonce, 'timestamp': timestamp}
        sign_str = (self._get_query_str(self._get_flattened_map(
            params)) + '&' if params else '') + self._get_query_str(headers)
        headers['sign'] = self._hmac_sha256(sign_str)
        response = requests.get(url, json=params, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            sys.exit(f"Error fetching API data: {response.text}")

    def connect(self) -> None:
        # Fetch the device list and store it in _devices_data
        self._devices_data = self._get_api(self._url_device_list)
        print("Connected to Ecoflow API successfully.")

    def device_list(self) -> list:
        if self._devices_data is None:
            print("No devices data available. Please connect first.")
            return []
        if 'data' not in self._devices_data:
            print("No devices found in the data.")
            return []
        print("Device list retrieved successfully.")
        # Return the list of devices
        return self._devices_data.get('data', [])

    def get_data(self, serial_number: str) -> Optional[dict]:
        if self._devices_data is None:
            print("No devices data available. Please connect first.")
            return None
        if 'data' not in self._devices_data:
            print("No devices found in the data.")
            return None

        for device in self._devices_data.get('data', []):
            if device.get('sn') == serial_number:
                url_quota = f'{self._url_device_quota}{serial_number}'
                ef_data = self._get_api(url_quota, {"sn": serial_number})
                return ef_data
        print(f"Device with SN '{serial_number}' not found.")
        return None

    def device_is_online(self, serial_number: str) -> str:
        for device in self._devices_data.get('data', []):
            if device.get('sn') == serial_number:
                return "online" if device.get('online', 0) == 1 else "offline"
        return "device not found"


if __name__ == '__main__':
    # read key and secret from file
    try:
        with open('ef_api_key.txt', 'r') as key_file:
            key, secret = key_file.read().strip().split(':')
    except FileNotFoundError:
        print("No API key file found. Please create 'ef_api_key.txt' with the format 'key:secret'.")
        sys.exit(1)

    serial_numbers = []
    if len(sys.argv) > 1:
        serial_numbers.append(sys.argv[1])

    api_client = EcoflowClient(key=key, secret=secret)
    api_client.connect()
    device_list = api_client.device_list()

    # print a numbered list of available devices and serial numbers
    print("Available devices:")
    for i, device in enumerate(device_list):
        print(f"{i + 1}: {device.get('productName')} {device.get('sn')} ({device.get('deviceName')}) - {'Online' if device.get('online', 0) == 1 else 'Offline'}")

    if not serial_numbers:
        choice = input(
            "Enter the number of the device you want to retrieve data for: ")
        try:
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(device_list):
                serial_numbers.append(
                    device_list[choice_index].get('sn'))
            else:
                print("Invalid choice. Exiting.")
                sys.exit(0)
        except ValueError:
            print("Invalid input. Exiting.")
            sys.exit(0)
    for serial_number in serial_numbers:
        device_data = api_client.get_data(serial_number)
        pprint.pprint(device_data)
