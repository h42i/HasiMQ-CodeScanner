#!/usr/bin/python
import os
import sys
import tty
import json
import time
import subprocess
import urllib
import urllib.request
import urllib.parse
import copy
import mosquitto
import threading

from datetime import datetime
from evdev import InputDevice, list_devices, ecodes, events, categorize

class CodeScanner:
    _scan_codes = {
        0: None, 1: u'ESC', 2: u'1', 3: u'2', 4: u'3', 5: u'4', 6: u'5', 7: u'6', 8: u'7', 9: u'8',
        10: u'9', 11: u'0', 12: u'-', 13: u'=', 14: u'BKSP', 15: u'TAB', 16: u'Q', 17: u'W', 18: u'E', 19: u'R',
        20: u'T', 21: u'Y', 22: u'U', 23: u'I', 24: u'O', 25: u'P', 26: u'[', 27: u']', 28: u'CRLF', 29: u'LCTRL',
        30: u'A', 31: u'S', 32: u'D', 33: u'F', 34: u'G', 35: u'H', 36: u'J', 37: u'K', 38: u'L', 39: u';',
        40: u'"', 41: u'`', 42: u'LSHFT', 43: u'\\', 44: u'Z', 45: u'X', 46: u'C', 47: u'V', 48: u'B', 49: u'N',
        50: u'M', 51: u',', 52: u'.', 53: u'/', 54: u'RSHFT', 56: u'LALT', 100: u'RALT'
    }

    _error_wait_time = 3

    def __init__(self, broker, scan_device):
        self._broker = broker
        self._client = None

        self._code = ''
        self._scan_device = scan_device
        self._scanner = None

        self._connect_to_broker()
        self._connect_to_device()

    def _connect_to_broker(self):
        try:
            print('Connecting to broker.')

            self._client = mosquitto.Mosquitto('code_scanner')

            self._client.on_connect = self.on_connect
            self._client.on_disconnect = self.on_disconnect
            self._client.on_publish = self.on_publish

            self._client.connect(self._broker, 1883, 120)
        except:
            print('Could not connect to broker. Trying again in a few seconds.')

            time.sleep(self._error_wait_time)
            self._connect_to_broker()

    def _reconnect_to_broker(self):
        try:
            print('Reconnecting to broker')

            self._client.connect(self._broker, 1883, 120)
        except:
            print('Could not reconnect to broker. Trying again in a few seconds.')

            self._reconnect_to_broker()

    def _connect_to_device(self):
        try:
            if self._scanner != None:
                self._scanner.ungrab()
        except:
            pass

        scanner_found = False

        try:
            devices = map(InputDevice, list_devices())

            for device in devices:
                if device.name == self._scan_device:
                    self._scanner = InputDevice(device.fn)
                    scanner_found = True
        except:
            print('Could not connect to scanner. Trying again in a few seconds.')

            time.sleep(self._error_wait_time)
            self._connect_to_device()

        if not scanner_found:
            print('No scanner found. Trying again in a few seconds.')

            time.sleep(self._error_wait_time)
            self._connect_to_device()
        else:
            print('Connected to the scanner.')

    def on_connect(self, mosq, obj, rc):
        print('Connected to the broker.')

    def on_disconnect(self, mosq, obj, rc):
        print('Disconnected from the broker. Reconnecting now.')

        self._reconnect_to_broker()

    def on_publish(self, mosq, obj, mid):
        print('Scanned code successfully published.')

    def send_code(self, code):
        try:
            self._client.publish('hasi/null', 'connection_test_message_because_mosquittos_publish_callback_is_false_positive_when_sending_the_first_message_after_lost_connection_but_actually_it_should_not_lose_the_connection_this_fast_at_all', 0, True)
            self._client.publish('hasi/code_scanner', code, 0, True)
        except:
            print('Could not publish scanned code. Reconnecting to the broker and publishing again.')

            self._reconnect_to_broker()
            self.send_code(code)

    def loop(self):
        if self._client.loop() != 0:
            print('Fatal error. Trying to reconnect to the scanner.')

            self._reconnect_to_broker()

        try:
            for event in self._scanner.read_loop():
                if event.type == ecodes.EV_KEY:
                    data = categorize(event)

                    if data.keystate == 1 and data.scancode != 42:
                        if data.scancode == 28:
                            print('Scanned code: ' + self._code)

                            sending_thread = threading.Thread(target=self.send_code, args=[copy.deepcopy(self._code)])
                            sending_thread.start()

                            self._code = ''
                        else:
                            self._code += self._scan_codes[data.scancode]
        except:
            print('Fatal error. Trying to reconnect to the scanner.')

            time.sleep(self._error_wait_time)
            self._connect_to_device()

if __name__ == '__main__':
    scanner = CodeScanner('atlas.hasi', '© Symbol Technologies, Inc, 2000 Symbol Bar Code Scanner')

    while True:
        scanner.loop()
