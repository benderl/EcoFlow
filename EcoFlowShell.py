#!/usr/bin/env python3
import pprint
from typing import List
import cmd

from EcoFlowApi import EcoFlowClient

class EcoFlowShell(cmd.Cmd):
    intro = "Welcome to the EcoFlow API Shell. Type help or ? to list commands.\n"
    prompt = "(EcoFlow) "

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
        "Exit the program"
        print("Exiting the program.")
        return True

    def default(self, line):
        print("Unknown command:", line)
        print("Available commands: get_cert, list_devices, get_data, exit")


if __name__ == '__main__':
    EcoFlowShell().cmdloop()
