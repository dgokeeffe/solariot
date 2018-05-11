#!/usr/bin/env python

# Copyright (c) 2018 David O'Keeffe
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

from pymodbus.client.sync import ModbusTcpClient

import config
import json
import time
import datetime
import requests


def load_registers(type, start, COUNT = 100):
    try:
        if type == "read":
            rr = client.read_input_registers(int(start),
                                             count = int(COUNT),
                                             unit = config.slave)
        elif type == "holding":
            rr = client.read_holding_registers(int(start),
                                               count = int(COUNT),
                                               unit = config.slave)

        for num in range(0, int(COUNT)):
            run = int(start) + num + 1
            if type == "read" and modmap.read_register.get(str(run)):
                if '_10' in modmap.read_register.get(str(run)):
                    inverter[modmap.read_register.get(str(run))[:-3]] = float(rr.registers[num])/10
                else:
                    inverter[modmap.read_register.get(str(run))] = rr.registers[num]
            elif type == "holding" and modmap.holding_register.get(str(run)):
                inverter[modmap.holding_register.get(str(run))] = rr.registers[num]

    except Exception as err:
        print("[ERROR] %s",  err)

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()

    print("Load config %s", config.model)

    # Load the modbus register map for the inverter
    modmap_file = "modbus-" + config.model
    modmap = __import__(modmap_file)
    print("Load ModbusTcpClient")

    client = ModbusTcpClient(config.inverter_ip,
                             timeout = config.timeout,
                             RetryOnEmpty = True,
                             retries = 3,
                             port = config.inverter_port)
    print("Connect")
    client.connect()

    inverter = {}
    bus = json.loads(modmap.scan)

    print(bus)

    while True:
        try:
            inverter = {}

            # Reads the registers
            if 'sungrow-' in config.model:
                for i in bus['read']:
                    load_registers("read", i['start'], i['range'])
                for i in bus['holding']:
                    load_registers("holding", i['start'], i['range'])

              # Sungrow inverter specifics:
              # Work out if the grid power is being imported or exported
            if config.model == "sungrow-sh5k" and \
                    inverter['grid_import_or_export'] == 65535:
                        export_power = (65535 - inverter['export_power']) * -1
                        inverter['export_power'] = export_power
                        inverter['timestamp'] = "%s/%s/%s %s:%02d:%02d" % (
                            inverter['day'],
                            inverter['month'],
                            inverter['year'],
                            inverter['hour'],
                            inverter['minute'],
                            inverter['second'])

            print(inverter)

        except Exception as err:
            print("[ERROR] %s", err)
            client.close()
            client.connect()

        # Go to sleep for some period of time
        time.sleep(config.scan_interval)
