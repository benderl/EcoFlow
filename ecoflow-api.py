#!/usr/bin/env python3

import pprint
import sys
from typing import List, Optional
import requests
import hmac
import hashlib
import random
import time
import binascii
import cmd


class EcoFlowClient():
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
        self._devices_data = self._get_api(self._url_device_list)
        print("Connected to Ecoflow API.")

    def device_list(self) -> list:
        if self._devices_data is None:
            print("No devices data available. Please connect first.")
            return []
        if 'data' not in self._devices_data:
            print("No devices found in the data.")
            return []
        print("Device list retrieved successfully.")
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
    
    def get_mqtt_certificate(self):
        url = f"{self._api_url_base}/certification"
        response = self._get_api(url)
        if response and 'data' in response:
            return response['data']
        print("Failed to retrieve MQTT certificate.")
        return None


class EcoFlowShell(cmd.Cmd):
    intro = "Welcome to the EcoFlow API Shell. Type help or ? to list commands.\n"
    prompt = "(ecoflow) "

    def __init__(self):
        super().__init__()
        # read key and secret from file
        try:
            with open('ef_api_key.txt', 'r') as key_file:
                key, secret = key_file.read().strip().split(':')
        except FileNotFoundError as error:
            raise FileNotFoundError("No API key file found. Please create 'ef_api_key.txt' with the format 'key:secret'.") from error
        except ValueError as error:
            raise ValueError("Invalid format in 'ef_api_key.txt'. Please use 'key:secret' format.") from error
        self._api_client = EcoFlowClient(key=key, secret=secret)
        self._api_client.connect()

    def _print_device_list(self, device_list: List[dict]) -> None:
        # print a numbered list of available devices and serial numbers
        if not device_list:
            print("No devices found.")
            return
        print("Available devices:")
        for i, device in enumerate(device_list):
            print(f"{i + 1}: {device.get('productName')} {device.get('sn')} ({device.get('deviceName')}) - {'Online' if device.get('online', 0) == 1 else 'Offline'}")

    def do_get_mqtt_cert(self, arg):
        "Retrieve the MQTT certificate"
        cert = self._api_client.get_mqtt_certificate()
        if cert:
            print("MQTT Certificate:")
            pprint.pprint(cert)
        else:
            print("Failed to retrieve MQTT certificate.")

    def do_list_devices(self, arg):
        "List all devices"
        device_list = self._api_client.device_list()
        self._print_device_list(device_list)

    def do_get_data(self, arg):
        "Show data for a specific device"
        device_list = self._api_client.device_list()
        if not device_list:
            print("No devices found.")
            return
        self._print_device_list(device_list)
        choice = input("Choose a device by list number: ")
        try:
            choice_index = int(choice) - 1
            if 0 <= choice_index < len(device_list):
                serial_number = device_list[choice_index].get('sn')
                device_data = self._api_client.get_data(serial_number)
                if device_data:
                    pprint.pprint(device_data)
                else:
                    print(f"No data found for device with SN '{serial_number}'.")
            else:
                print("Invalid choice.")
        except ValueError:
            print("Invalid input.")

    def do_exit(self, arg) -> bool:
        "Exit the programm"
        print("Exiting the program.")
        return True

    def default(self, line):
        print("Unknown command:", line)
        print("Available commands: get_cert, list_devices, get_data, exit")


if __name__ == '__main__':
    EcoFlowShell().cmdloop()
