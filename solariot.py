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

import config
import json
import datetime
import time

from pymodbus.client.sync import ModbusTcpClient
from pymodbus.payload import BinaryPayloadDecoder
from pymodbus.constants import Endian


def load_registers(registers, read_or_holding, inverter_dict):

    # request each register from datasets, omit first row which contains only column headers
    for register in registers:
        name = register[0]
        startPos = register[1]
        data_type = register[2]
        unit = register[3]

        # if the connection is somehow not possible (e.g. target not responding)
        # show a error message instead of excepting and stopping
        try:
            if read_or_holding == "read":
                received = client.read_input_registers(address=startPos - 1,
                                                       count=sungrow_datatype[data_type],
                                                       unit=config.slave)
            elif read_or_holding == "holding":
                received = client.read_holding_registers(address=startPos - 1,
                                                         count=sungrow_datatype[data_type],
                                                         unit=config.slave)
        except:
            this_date = str(datetime.datetime.now()).partition('.')[0]
            error_message = this_date + ': Connection not possible. Check settings or connection.'
            print(error_message)
            return  ## prevent further execution of this function

        # provide the correct result depending on the defined data type
        # double word data is encoded in little endian, single byte data is in big endian
        if '32' in data_type:
            message = BinaryPayloadDecoder.fromRegisters(received.registers, byteorder='>', wordorder='>')
        else:
            message = BinaryPayloadDecoder.fromRegisters(received.registers, byteorder='>', wordorder='<')

        # decode based off data type
        if data_type == 'S32':
            interpreted = message.decode_32bit_int()
        elif data_type == 'U32':
            interpreted = message.decode_32bit_uint()
        elif data_type == 'S16':
            interpreted = message.decode_16bit_int()
        elif data_type == 'U16':
            interpreted = message.decode_16bit_uint()
        elif 'STR' in data_type:
            interpreted = message.decode_string(10)
        else: ## if no data data_type is defined do raw interpretation of the delivered data
            interpreted = message.decode_16bit_uint()

        ## che<k for "None" data before doing anything else
        if ((interpreted == MIN_SIGNED) or (interpreted == MAX_UNSIGNED)):
            displaydata = None
        else:
          ## put the data with correct unitting into the data table
            if unit == 'FIX1':
                displaydata = float(interpreted) / 10
            elif unit == 'FIX2':
                displaydata = float(interpreted) / 100
            elif unit == 'FIX3':
                displaydata = float(interpreted) / 1000
            else:
                displaydata = interpreted

        #print '************** %s = %s' % (name, str(displaydata))
        inverter_dict[name] = displaydata

    # Add timestamp
    inverter_dict["Timestamp"] = str(datetime.datetime.now()).partition('.')[0]
    return(interver_dict)

if __name__ == "__main__":
    print("Load config %s", config.model)

    # Load the modbus register map for the inverter
    modmap_file = "modbus-" + config.model
    modmap = __import__(modmap_file)
    print("Load ModbusTcpClient")

    # Connect to the client
    client = ModbusTcpClient(config.inverter_ip,
                             timeout=config.timeout,
                             RetryOnEmpty=True,
                             retries=3,
                             port=config.inverter_port)
    print("Connected")
    client.connect()

    MIN_SIGNED   = -2147483648
    MAX_UNSIGNED =  4294967295

    print("Load config %s", config.model)

    # SMA datatypes and their register lengths
    # S = Signed Number, U = Unsigned Number
    sungrow_datatype = {
      'S16':1,
      'U16':1,
      'S32':2,
      'U32':2,
      'STR16*10':10,
      'U16*18':18,
    }

    while True:
        try:
            inverter = {}

            # Reads the registers
            if 'sungrow-' in config.model:
                inverter = load_registers(modmap.sungrow_read_registers, "read", inverter)
                inverter = load_registers(modmap.sungrow_holding_registers, "holding", inverter)

            print(inverter)

        except Exception as err:
            print("[ERROR] %s", err)
            client.close()
            client.connect()

        # Go to sleep for some period of time
        time.sleep(config.scan_interval)
