'''This module is for controlling a Megnajet/Xaar CIMSII/Midas (referred to as Midas) ink delivery
system for an inkjet printer. node_id is used for multiple midas systems on the same COM port,
it should be left as the default 0 (or not passed as an argument) for single systems'''
import serial
from serial import SerialException


class MidasSerial:
    '''This object controls the serial communications with the Midas ink delivery
    system'''
    def __init__(self, port, baudrate, stopbits, parity, databits, timeout):
        self.port = port
        self.baudrate = baudrate
        self.stopbits = stopbits
        self.parity = parity
        self.databits = databits
        self.timeout = timeout

    def open_connection(self):
        '''Open a serial connection to the Midas on the specified port'''
        self.serial = serial.Serial(
            port=self.port,
            baudrate=self.baudrate,
            parity=self.parity,
            stopbits=self.stopbits,
            bytesize=self.databits,
            timeout=self.timeout
        )

    def close_connection(self):
        '''Closes the connection to the Midas'''
        self.serial.close()

    def serial_write(self, command, node_id=0):
        '''node_id is when using multiple Midas systems on one COM port
        node_id should be 1-15 (A-O) if using networked Midas, or default of 0 for single
        if node_id is not 0, then it is converted to a network ID letter and 
        prepended to the command to reach the right Midas '''
        if node_id != 0:
            network_address = chr(ord('@')+node_id)
            command = network_address + command
        if self.serial.is_open:
            self.serial.write(bytes(command, 'utf-8'))

    def serial_response(self, response_type):
        '''Reads the response from the Midas to check if the command was successful
        If it was, returns "True" for a set command, and the requested value for get command'''
        try:
            response = self.serial.read_until(expected='C').decode("utf-8")
        except TimeoutError as ex:
            print(f'Error: Timeout, exception: {ex}')
            return ex
        except SerialException as ex:
            print(f'Error: Port Closed, exception: {ex}')
            return ex

        response_check = response[len(response) - 3, 1]

        if response_check == "?":
            print("Bad Command, not understood")
            return "?,C"
        if response_check == ">":
            print("Bad Command, data missing")
            return "<,C"
        if response_type == "set":
            return bool(response == ",A,C") # True if set correctly
        if response_type == "get":
            response_information = response[2, (len(response) - 2)]
            return response_information
        return "None"

class Status:
    '''Contains the information about the alarms and status bits of the Midas system
    This is created with the Midas object'''
    def __init__(self, serialconn):
        self.serialconn = serialconn
        self.status_word = ""
        self.status_bit = ""
        self.error_desc = ""
        self.alarm = ""
        self.alarm_masks = {'actual': "", 'demand': ""}
        self.critical_alarms = {'actual': "", 'demand': ""}
        self.running_hours = ""
        self.fill_cycles = ""

    def get_status_word(self, node_id=0):
        '''Read the current status of the system and return the current backpressure 
        in scaled units, the system status and any current active alarms
        System Status word:
        00000000 00000001 Tank filling
        00000000 00000010 purging
        00000000 00000100 tank heater output on
        00000000 00001000 ext heater output on
        00000000 00010000 cure lamp output on
        00000000 00100000 internal recirc
        00000000 01000000 head lockoff valve open
        00000000 10000000 System Enabled
        00000001 00000000 preheat active
        00000010 00000000 bypass active
        00000100 00000000 drain system active
        00001000 00000000 flush system active
        00010000 00000000 Calibration in progress
        00100000 00000000 spare
        01000000 00000000 spare
        10000000 00000000 spare'''
        self.serialconn.serial_write("STA?\r", node_id)
        self.status_word = self.serialconn.serial_response("get")
        return self.status_word

    def get_status_bit(self, node_id=0):
        '''Return the status bits (see bit representation in STA? command above)
        Decimal representing binary value (0-65535)'''
        self.serialconn.serial_write("SSB?\r", node_id)
        self.status_bit = self.serialconn.serial_response("get")
        return self.status_bit

    def get_last_error_code(self, node_id=0):
        '''laser error code that is present on the Midas
        returns string'''
        self.serialconn.serial_write("SLE?\r", node_id)
        error_code = self.serialconn.serial_response("get")
        match error_code:
            case "0":
                self.error_desc = "0 - No error reported"
            case "10":
                self.error_desc = "10 - Temperature heater 1 less than 1"
            case "20":
                self.error_desc = "20 - Temperature heater 1 higher than upper limit"
            case "30":
                self.error_desc = "30 - Temperature heater 1 ground loop error"
            case "40":
                self.error_desc = "40 - Temperature heater 2 less than 1"
            case "50":
                self.error_desc = "50 - Temperature heater 2 higher than upper limit"
            case "60":
                self.error_desc = "60 - Temperature heater 2 ground loop error"
            case "70":
                self.error_desc = "70 - i2c read erro"
            case _:
                self.error_desc = "No response"

        return self.error_desc

    def get_alarms(self, node_id=0):
        '''Check current status
        System alarm byte:
        00000000 00000001 vacuum / pressure alarm
        00000000 00000010 pump timeout
        00000000 00000100 ink level warning
        00000000 00001000 ink bottle empty
        00000000 00010000 Tank thermocouple fault
        00000000 00100000 degass fault(if fitted)
        00000000 01000000 recirc fault(if recirc version)
        00000000 10000000 Failsafe alarm(float switch in the air bottle)
        00000001 00000000 meniscus pump running to slow(bleed filter blocked)
        00000010 00000000 meniscus pump running to fast(air leak)
        00000100 00000000 recirc pump running to slow(blockage in pipework / head)
        00001000 00000000 recirc pump running to fast(leak / pump fault)
        00010000 00000000 spare
        00100000 00000000 spare
        01000000 00000000 spare
        10000000 00000000 spare'''
        self.serialconn.serial_write("SA1?\r", node_id)
        midas_response = self.serialconn.serial_response("get")
        match midas_response:
            case "00000000 00000001":
                self.alarm = "vacuum/pressure alarm"
            case "00000000 00000010":
                self.alarm = "pump timeout"
            case "00000000 00000100":
                self.alarm = "ink level warning"
            case "00000000 00001000":
                self.alarm = "ink bottle empty"
            case "00000000 00010000":
                self.alarm = "Tank thermocouple fault"
            case "00000000 00100000":
                self.alarm = "degass fault (if fitted)"
            case "00000000 01000000":
                self.alarm = "recirc fault (if recirc version)"
            case "00000000 10000000":
                self.alarm = "Failsafe alarm (float switch in the air bottle)"
            case "00000001 00000000":
                self.alarm = "meniscus pump running to slow (bleed filter blocked)"
            case "00000010 00000000":
                self.alarm = "meniscus pump running to fast (air leak)"
            case "00000100 00000000":
                self.alarm = "recirc pump running to slow (blockage in pipework/head)"
            case "00001000 00000000":
                self.alarm = "recirc pump running to fast (leak/pump fault)"
            case _:
                self.alarm = "None"
        return self.alarm

    def get_system_running_hours(self, node_id=0):
        '''System running hours
        String (hours-mins)'''
        self.serialconn.serial_write("SVN?\r", node_id)
        self.running_hours = self.serialconn.serial_response("get")
        return self.running_hours

    def get_alam_masks(self, node_id=0):
        '''Mask alarm output on alarm
        Integer representation of binary
        00000000 00000001 set alarm output on meniscus sensor fault
        00000000 00000010 set alarm output on pump timeout
        00000000 00000100 set alarm output on ink level warning
        00000000 00001000 set alarm output on ink bottle empty
        00000000 00010000 set alarm output on tank thermocouple fault
        00000000 00100000 set alarm output on degas fault(if fitted)
        00000000 01000000 set alarm output on recirculation sensor fault
        00000000 10000000 set alarm output on failsafe alarm
        00000001 00000000 set alarm output on meniscus pump running to slow(bleed filter blocked)
        00000010 00000000 set alarm output on meniscus pump running to fast(air leak)
        00000100 00000000 set alarm output on recirc pump running to slow(blockage in pipework/head)
        00001000 00000000 set alarm output on recirc pump running to fast(leak / pump fault)
        00010000 00000000 spare
        00100000 00000000 spare
        01000000 00000000 spare
        10000000 00000000 spare'''
        self.serialconn.serial_write("SAB?\r", node_id)
        self.alarm_masks['actual'] = self.serialconn.serial_response("get")
        return self.alarm_masks['actual']

    def set_alam_masks(self, alarm_mark, node_id=0):
        '''Set mask alarm output on alarm
        Integer representation of binary
        00000000 00000001 set alarm output on meniscus sensor fault
        00000000 00000010 set alarm output on pump timeout
        00000000 00000100 set alarm output on ink level warning
        00000000 00001000 set alarm output on ink bottle empty
        00000000 00010000 set alarm output on tank thermocouple fault
        00000000 00100000 set alarm output on degas fault(if fitted)
        00000000 01000000 set alarm output on recirculation sensor fault
        00000000 10000000 set alarm output on failsafe alarm
        00000001 00000000 set alarm output on meniscus pump running to slow(bleed filter blocked)
        00000010 00000000 set alarm output on meniscus pump running to fast(air leak)
        00000100 00000000 set alarm output on recirc pump running to slow(blockage in pipework/head)
        00001000 00000000 set alarm output on recirc pump running to fast(leak / pump fault)
        00010000 00000000 spare
        00100000 00000000 spare
        01000000 00000000 spare
        10000000 00000000 spare'''
        command = "SAB," + alarm_mark + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.alarm_masks['demand'] = alarm_mark
            self.get_alam_masks(node_id)
        return midas_response

    def get_critical_alarms(self, node_id=0):
        '''Shows which alarms will raise a critical alarm and shutdown the system.
        Integer representation of binary
        bits 1,7 + 8 are hard coded so always enabled (can't be turned off).
        00000000 00000001 shutdown on meniscus sensor fault(always on)
        00000000 00000010 shutdown on pump timeout
        00000000 00000100 shutdown on ink level warning
        00000000 00001000 shutdown on ink bottle empty
        00000000 00010000 shutdown on tank thermocouple fault
        00000000 00100000 shutdown on degas fault(if fitted)
        00000000 01000000 shutdown on recirculation sensor fault
        00000000 10000000 shutdown on failsafe alarm(always on)
        00000001 00000000 shutdown on meniscus pump running to slow(bleed filter blocked)
        00000010 00000000 shutdown on meniscus pump running to fast(air leak)
        00000100 00000000 shutdown on recirc pump running to slow(blockage in pipework / head)
        00001000 00000000 shutdown on recirc pump running to fast(leak / pump fault)
        00010000 00000000 spare
        00100000 00000000 spare
        01000000 00000000 spare
        10000000 00000000 spare'''
        self.serialconn.serial_write("SAM?\r", node_id)
        self.critical_alarms['actual'] = self.serialconn.serial_response("get")
        return self.critical_alarms['actual']

    def set_critical_alarms(self, alarm_mask, node_id=0):
        '''Selects which alarms will raise a critical alarm and shutdown the system.
        Integer representation of binary
        bits 1,7 + 8 are hard coded so always enabled (can't be turned off).
        00000000 00000001 shutdown on meniscus sensor fault(always on)
        00000000 00000010 shutdown on pump timeout
        00000000 00000100 shutdown on ink level warning
        00000000 00001000 shutdown on ink bottle empty
        00000000 00010000 shutdown on tank thermocouple fault
        00000000 00100000 shutdown on degas fault(if fitted)
        00000000 01000000 shutdown on recirculation sensor fault
        00000000 10000000 shutdown on failsafe alarm(always on)
        00000001 00000000 shutdown on meniscus pump running to slow(bleed filter blocked)
        00000010 00000000 shutdown on meniscus pump running to fast(air leak)
        00000100 00000000 shutdown on recirc pump running to slow(blockage in pipework / head)
        00001000 00000000 shutdown on recirc pump running to fast(leak / pump fault)
        00010000 00000000 spare
        00100000 00000000 spare
        01000000 00000000 spare
        10000000 00000000 spare'''
        command = "SAM," + alarm_mask + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.critical_alarms['demand']= alarm_mask
            self.get_critical_alarms(node_id)
        return midas_response

    def clear_alarms(self, node_id=0):
        '''Reset alarms on the system'''
        command = "SA1,0\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.get_alarms(node_id)
        return midas_response

    def get_fill_cycles(self, node_id=0):
        '''Fill cycles completed
        Integer in string format'''
        self.serialconn.serial_write("SFC?\r", node_id)
        self.fill_cycles = self.serialconn.serial_response("get")
        return self.fill_cycles

class Pressures:
    '''Contains the information about the actual and demand pressures Midas system
    This is created with the Midas object'''
    def __init__(self, serialconn):
        self.serialconn = serialconn
        self.return_pressure = {'actual': "", 'demand': ""}
        self.non_recirc_meniscus_pressure = {'actual': "", 'demand': ""}
        self.infeed_pressure = {'actual': "", 'demand': ""}
        self.pressure_sensor_type = {'actual': "", 'demand': ""}

    def get_return_pressure(self, node_id=0):
        '''Read current target meniscus pressure in system scaled units 
        (on recirculating systems this is the recirculating meniscus)
        System scaled units (0-1500) value = 10 x pressure[mbar]'''
        self.serialconn.serial_write("SVP?\r", node_id)
        self.return_pressure['actual'] = self.serialconn.serial_response("get")
        return self.return_pressure['actual']

    def set_return_pressure(self, pressure, node_id=0):
        '''Set current target meniscus pressure in system scaled units 
        (on recirculating systems this is the recirculating meniscus)
        System scaled units (0-1500) value = 10 x pressure[mbar]'''
        command = "SVP," + pressure + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.return_pressure['demand'] = pressure
            self.get_return_pressure(node_id)
        return midas_response

    def get_non_recirc_meniscus_pressure(self, node_id=0):
        '''Read current target vacuum pressure in system scaled units
        (on recirculating systems this is the NON recirculating meniscus)
        System scaled units (0-1500) value = 10 x pressure[mbar]'''
        self.serialconn.serial_write("SV2?\r", node_id)
        self.non_recirc_meniscus_pressure['actual'] = self.serialconn.serial_response(
            "get")
        return self.non_recirc_meniscus_pressure['actual']

    def set_non_recirc_meniscus_pressure(self, pressure, node_id=0):
        '''Set current target vacuum pressure in system scaled units
        (on recirculating systems this is the NON recirculating meniscus)
        System scaled units (0-1500) value = 10 x pressure[mbar]'''
        command = "SV2," + pressure + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.non_recirc_meniscus_pressure['demand'] = pressure
            self.get_non_recirc_meniscus_pressure(node_id)
        return midas_response

    def get_infeed_pressure(self, node_id=0):
        '''Read current target recirculation pump pressure in mbar
        mbar (0-255)'''
        self.serialconn.serial_write("SRS?\r", node_id)
        self.infeed_pressure['actual'] = self.serialconn.serial_response("get")
        return self.infeed_pressure['actual']

    def set_infeed_pressure(self, pressure, node_id=0):
        '''Set current target recirculation pump pressure in mbar
        mbar (0-255)'''
        command = "SRS," + pressure + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.infeed_pressure['demand'] = pressure
            self.get_infeed_pressure(node_id)
        return midas_response

    def get_pressure_sensor_type(self, node_id=0):
        '''Read sensors remote (enable manifold) changes between internal sensors and remote sensors
        0 internal sensors (default), 1 remote manifold'''
        self.serialconn.serial_write("SSR?\r", node_id)
        self.pressure_sensor_type['actual'] = self.serialconn.serial_response("get")
        return self.pressure_sensor_type['actual']

    def set_pressure_sensor_type(self, sensor_type, node_id=0):
        '''Set sensors remote (enable manifold) changes between internal sensors and remote sensors
        0 internal sensors (default), 1 remote manifold'''
        command = "SSR," + sensor_type + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.pressure_sensor_type['demand'] = sensor_type
            self.get_pressure_sensor_type(node_id)
        return midas_response

class Temperatures:
    '''Contains the information about the actual and demand temperatures Midas system
    This is created with the Midas object'''
    def __init__(self, serialconn):
        self.serialconn = serialconn
        self.temp_heater_1 = ""
        self.tank_temperature = {'actual': "", 'demand': ""}
        self.aux_temp = {'actual': "", 'demand': ""}
        self.preheat_time = {'actual': "", 'demand': ""}
        self.heater_1_duty = {'actual': "", 'demand': ""}
        self.heater_2_duty = {'actual': "", 'demand': ""}

    def get_heater_temp_1(self, node_id=0):
        '''Read spare thermocouple read back on manifold
        String representing floating point temperature (e.g. "10.2")'''
        self.serialconn.serial_write("ST3?\r", node_id)
        self.temp_heater_1 = self.serialconn.serial_response("get")
        return self.temp_heater_1

    def get_tank_temperature(self, node_id=0):
        '''Read current target tank heater temperature
        Degrees C (0-60)'''
        self.serialconn.serial_write("SHT?\r", node_id)
        self.tank_temperature['actual'] = self.serialconn.serial_response("get")
        return self.tank_temperature['actual']

    def set_tank_temperature(self, temperature, node_id=0):
        '''Set current target tank heater temperature
        Degrees C (0-60)'''
        command = "SHT," + temperature + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.tank_temperature['demand'] = temperature
            self.get_tank_temperature(node_id)
        return midas_response

    def get_aux_temperture(self, node_id=0):
        '''Read current target auxiliary heater temperature (450 only)
        Degrees C (0-60)'''
        self.serialconn.serial_write("SH2?\r", node_id)
        self.aux_temp['actual'] = self.serialconn.serial_response("get")
        return self.aux_temp['actual']

    def set_aux_temperture(self, temperature, node_id=0):
        '''Set current target auxiliary heater temperature (450 only)
        Degrees C (0-60)'''
        command = "SH2," + temperature + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.aux_temp['demand'] = temperature
            self.get_aux_temperture(node_id)
        return midas_response

    def get_preheat_time(self, node_id=0):
        '''Read preheat time
        Seconds (0-600)'''
        self.serialconn.serial_write("SPH?\r", node_id)
        self.preheat_time['actual'] = self.serialconn.serial_response("get")
        return self.preheat_time['actual']

    def set_preheat_time(self, time, node_id=0):
        '''Set preheat time
        Seconds (0-600)'''
        command = "SPH," + time + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.preheat_time['demand'] = time
            self.get_preheat_time(node_id)
        return midas_response

    def get_heater_1_duty(self, node_id=0):
        '''Read Heater 1 duty in %
        %duty ((0-100)'''
        self.serialconn.serial_write("SHD?\r", node_id)
        self.heater_1_duty['actual'] = self.serialconn.serial_response("get")
        return self.heater_1_duty['actual']

    def set_heater_1_duty(self, duty, node_id=0):
        '''Set Heater 1 duty in %
        %duty ((0-100)'''
        command = "SHD," + duty + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.heater_1_duty['demand'] = duty
            self.get_heater_1_duty(node_id)
        return midas_response

    def get_heater_2_duty(self, node_id=0):
        '''Read Heater 2 duty in %
        %duty ((0-100)'''
        self.serialconn.serial_write("SHA?\r", node_id)
        self.heater_2_duty['actual'] = self.serialconn.serial_response("get")
        return self.heater_2_duty['actual']

    def set_heater_2_duty(self, duty, node_id=0):
        '''Set Heater 2 duty in %
        %duty ((0-100)'''
        command = "SHA," + duty + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.heater_2_duty['demand'] = duty
            self.get_heater_2_duty(node_id)
        return midas_response

class Pumps:
    '''Contains the information about the recirc and fill pumps on the Midas system
    This is created with the Midas object'''
    def __init__(self, serialconn):
        self.serialconn = serialconn
        self.pump_timeout = {'actual': "", 'demand': ""}
        self.manual_recirc_speed = {'actual': "", 'demand': ""}
        self.fill_speed = {'actual': "", 'demand': ""}
        self.recirc_command = ""
        self.manual_meniscus_state = {'actual': "", 'demand': ""}
        self.meniscus_command = ""


    def get_pump_timeout(self, node_id=0):
        '''Gets the fill pump timeout
        Seconds (0-90)'''
        self.serialconn.serial_write("STO?\r", node_id)
        self.pump_timeout['actual'] = self.serialconn.serial_response("get")
        return self.pump_timeout['actual']

    def set_pump_timeout(self, timeout, node_id=0):
        '''Sets the fill pump timeout
        Seconds (0-90)'''
        command = "STO," + timeout + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.pump_timeout['demand'] = timeout
            self.get_pump_timeout(node_id)
        return midas_response

    def get_manual_recirc_speed(self, node_id=0):
        '''Read Manual Recirc speed
        Internal (0-700)'''
        self.serialconn.serial_write("SMR?\r", node_id)
        self.manual_recirc_speed['actual'] = self.serialconn.serial_response("get")
        return self.manual_recirc_speed['actual']

    def set_manual_recirc_speed(self, speed, node_id=0):
        '''Set Manual Recirc speed
        Internal (0-700)'''
        command = "SMR," + speed + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.manual_recirc_speed['demand'] = speed
            self.get_manual_recirc_speed(node_id)
        return midas_response

    def get_fill_speed(self, node_id=0):
        '''Read Fill pump speed in ml per min
        ml per minute (0-255)'''
        self.serialconn.serial_write("SFS?\r", node_id)
        self.fill_speed['actual'] = self.serialconn.serial_response("get")
        return self.fill_speed['actual']

    def set_fill_speed(self, speed, node_id=0):
        '''Set Fill pump speed in ml per min
        ml per minute (0-255)'''
        command = "SFS," + speed + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.fill_speed['demand'] = speed
            self.get_fill_speed(node_id)
        return midas_response

    def get_recirc_pump_command(self, node_id=0):
        '''Current recirc pump command
        Integer in string format'''
        self.serialconn.serial_write("SVR?\r", node_id)
        self.recirc_command = self.serialconn.serial_response("get")
        return self.recirc_command

    def get_manual_meniscus(self, node_id=0):
        '''Runs the meniscus pump at the fixed minimuim speed on HV controllers to
        allow the setting of the minimium meniscus pressure
        1 or 0'''
        self.serialconn.serial_write("SNI?\r", node_id)
        self.manual_meniscus_state['actual'] = self.serialconn.serial_response("get")
        return self.manual_meniscus_state['actual']

    def set_manual_meniscus(self, enable, node_id=0):
        '''Runs the meniscus pump at the fixed minimuim speed on HV controllers to
        allow the setting of the minimium meniscus pressure
        1 or 0'''
        command = "SNI," + enable + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.manual_meniscus_state['demand'] = enable
            self.get_manual_meniscus(node_id)
        return midas_response

    def get_meniscus_pump_command(self, node_id=0):
        '''Current meniscus pump command
        Integer in string format'''
        self.serialconn.serial_write("SVM?\r", node_id)
        self.meniscus_command = self.serialconn.serial_response("get")
        return self.meniscus_command

class Purge:
    '''Contains the information about the purge parameters on the Midas system
    This is created with the Midas object'''
    def __init__(self, serialconn):
        self.serialconn = serialconn
        self.purge_pressure = {'actual': "", 'demand': ""}
        self.purge_type = {'actual': "", 'demand': ""}
        self.purge_time = {'actual': "", 'demand': ""}
        self.local_purge_time = {'actual': "", 'demand': ""}

    def get_purge_pressure(self, node_id=0):
        '''Read current target Purge pressure in system scaled units
        units = 0-500 mbar'''
        self.serialconn.serial_write("SPP?\r", node_id)
        self.purge_pressure['actual'] = self.serialconn.serial_response("get")
        return self.purge_pressure['actual']

    def set_purge_pressure(self, pressure, node_id=0):
        '''Set current target Purge pressure in system scaled units
        units = 0-500 mbar'''
        command = "SPP," + pressure + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.purge_pressure['demand'] = pressure
            self.get_purge_pressure(node_id)
        return midas_response

    def get_purge_status(self, node_id=0):
        '''Check if purge is active
        0 inactive, 1 active'''
        self.serialconn.serial_write("STP?\r", node_id)
        self.purge_type['actual'] = self.serialconn.serial_response("get")
        return self.purge_type['actual']

    def triger_purge(self, purge_type, node_id=0):
        '''Trigger a purge cycle of type specified by the parameter
        Parameter
        1.soft purge - valves remain open purge for time defined by SPT
        2.hard purge - valves close and build pressure to that defined by SPP 
          then purge for time defined by SPT
        3.cancel purge
        4.head de-airing purge(Gravity + system only) – opens both valves and allows
          fluid from the back of the head to purge out the second head port
        5.release pressure purge(100ms purge used internally)'''
        command = "STP," + purge_type + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.purge_type['demand'] = purge_type
            self.get_purge_status(node_id)
        return midas_response

    def get_purge_time(self, node_id=0):
        '''Read purge time in 0.1 seconds
        0.1 seconds (0-255), e.g 30 is 0.3s'''
        self.serialconn.serial_write("SPT?\r", node_id)
        self.purge_time['actual'] = self.serialconn.serial_response("get")
        return self.purge_time['actual']

    def set_purge_time(self, time, node_id=0):
        '''Set purge time in 0.1 seconds
        0.1 seconds (0-255), e.g 30 is 0.3s'''
        command = "SPT," + time + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.purge_time['demand'] = time
            self.get_purge_time(node_id)
        return midas_response

    def get_local_purge_time(self, node_id=0):
        '''Read local purge time
        Seconds (0-60)'''
        self.serialconn.serial_write("SLP?\r", node_id)
        self.local_purge_time['actual'] = self.serialconn.serial_response("get")
        return self.local_purge_time['actual']

    def set_local_purge_time(self, time, node_id=0):
        '''Set local purge time
        Seconds (0-60)'''
        command = "SLP," + time + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.local_purge_time['demand'] = time
            self.get_local_purge_time(node_id)
        return midas_response

class Midas:
    '''This object holds the information regarding the Midas ink delivery system, 
    including the actual and demand values for various parameters.
    It has a number of functions to get/set different parameters and start the system'''
    def __init__(self,  port, baudrate=115200,
                                 stopbits=serial.STOPBITS_ONE,
                                 parity=serial.PARITY_NONE,
                                 databits=serial.EIGHTBITS, timeout=1):
        self.serialconn =  MidasSerial(port, baudrate, stopbits,
                                      parity, databits, timeout)
        self.status = Status(self.serialconn)
        self.pressures = Pressures(self.serialconn)
        self.temperature = Temperatures(self.serialconn)
        self.pumps = Pumps(self.serialconn)
        self.purge = Purge(self.serialconn)

        self.firmware_version = ""
        self.serial_number = ""
        self.system_type = ""
        self.active_heads = ""
        self.bypass_time = {'actual': "", 'demand': ""}
        self.statup_function = ""
        self.drain_status = {'actual': "", 'demand': ""}
        self.prime_state = {'actual': "", 'demand': ""}
        self.network_id = ""
        self.enable_bits = {'actual': "", 'demand': ""}
        self.extended_enable_bits = {'actual': "", 'demand': ""}
        self.dynamic_calibration_state = {'actual': "", 'demand': ""}

    def open_serial_connection(self):
        '''Create an instance of the MidasSerial class to talk to laser
        Default serial settings'''
        self.serialconn.open_connection()

    def close_serial(self):
        '''Close the connection with the laser'''
        self.serialconn.close_connection()

    def get_firmware_version(self, node_id=0):
        '''Firmware version number
        String '''
        self.serialconn.serial_write("SVN?\r", node_id)
        self.firmware_version = self.serialconn.serial_response("get")
        return self.firmware_version

    def get_serial_number(self, node_id=0):
        '''System serial Number
        String'''
        self.serialconn.serial_write("SSN?\r", node_id)
        self.serial_number = self.serialconn.serial_response("get")
        return self.serial_number

    def get_system_type(self, node_id=0):
        '''Unit type (used for system id in system detection)
        Integer representing the system type'''
        self.serialconn.serial_write("SUT?\r", node_id)
        self.system_type = self.serialconn.serial_response("get")
        return self.system_type

    def set_active_heads(self, heads, node_id=0):
        '''Set active heads
        Binary representation of heads 1,2,4,8,16,32 (max 63) e.g. "15" sets heads 1-4 open'''
        command = "SAH," + heads + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.active_heads = heads
        return midas_response
    def get_bypass_time(self, node_id=0):
        '''Read bypass time
        Seconds (0-600)'''
        self.serialconn.serial_write("SBT?\r", node_id)
        self.bypass_time['actual'] = self.serialconn.serial_response("get")
        return self.bypass_time['actual']

    def set_bypass_time(self, time, node_id=0):
        '''Set bypass time
        Seconds (0-600)'''
        command = "SBT," + time + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.bypass_time['demand'] = time
            self.get_bypass_time(node_id)
        return midas_response

    def set_startup_function(self, function, node_id=0):
        '''Trigger the startup mode function
        Parameter
        0.rerun PreHeat / Bypass
        1.cancel PreHeat / Bypass
        2.rerun Bypass only
        3.run bypass indefinitely'''
        command = "SCS," + function + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.statup_function = function
        return midas_response

    def get_drain_status(self, node_id=0):
        '''Read drain system active
        Will return 1 or 0 if active or inactive'''
        self.serialconn.serial_write("SDS?\r", node_id)
        self.drain_status['actual'] = self.serialconn.serial_response("get")
        return self.drain_status['actual']

    def set_drain(self, drain_type, node_id=0):
        '''Set drain system parameter - this turns off the meniscus and opens 
        the head valve whilst allowing the user to use the purge functions 
        to push out the fluid in the system
        Parameter
        0 – disable
        1 – enable drain(active heads)
        2 – enable drain(active heads) with permanent purge
        3 – enable drain(active heads +deairing) with permanent purge'''
        command = "SDS," + drain_type + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.drain_status['demand'] = drain_type
            self.get_drain_status(node_id)
        return midas_response

    def get_prime_system_status(self, node_id=0):
        '''Checks if system priming, 
        returns 1 or 0 is active or inactive'''
        self.serialconn.serial_write("SPR?\r", node_id)
        self.prime_state['actual'] = self.serialconn.serial_response("get")
        return self.prime_state['actual']

    def set_prime_system(self, enable, node_id=0):
        '''To access this function you must disable bit 0 of the enables (ink enable) 
        the unit will run in bypass until the bypass is cancelled then will prime
        heads once happy send SPR,0 to end
        1 is active, 0 is inactive'''
        command = "SPR," + enable + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.prime_state['demand'] = enable
            self.get_prime_system_status(node_id)
        return midas_response

    def get_network_id(self, node_id=0):
        '''Read network ID, return in a string representation of an int, though commands use letters
        ID = 1-15'''
        self.serialconn.serial_write("SNI?\r", node_id)
        self.network_id = self.serialconn.serial_response("get")
        return self.network_id

    def set_network_id(self, network_id, node_id=0):
        '''Set network ID using a string representation of an int, though commands use letters
        ID = 1-15'''
        command = "SNI," + network_id + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.network_id = network_id
            self.get_network_id(node_id)
        return midas_response

    def get_enable_bits(self, node_id=0):
        '''Read enable bits to define system functionality
        Decimal representing binary value (0- 65535)
        00000000 00000001 enables ink
        00000000 00000010 enable Tank heater
        00000000 00000100 enable External heater
        00000000 00001000 enable recirc
        00000000 00010000 enable user pwm
        00000000 00100000 enable pressure data streaming
        00000000 01000000 enable onboard purge button
        00000000 10000000 USE INTERNAL SIGNALS
        00000001 00000000 enable Hard Purge from HW Inputs
        00000010 00000000 enable external purge signal
        00000100 00000000 use pin12 as bulk level(else used as bcd purge)
        00001000 00000000 invert bottle empty signal
        00010000 00000000 invert user input signal
        00100000 00000000 enable degass(if fitted)
        01000000 00000000 Use manual recirc speed(Not on Midas)
        10000000 00000000 enable pull mode(Not on Midas)'''
        self.serialconn.serial_write("SEB?\r", node_id)
        self.enable_bits['actual'] = self.serialconn.serial_response("get")
        return self.enable_bits['actual']

    def set_enable_bits(self, enable_bits, node_id=0):
        '''Set enable bits to define system functionality
        Decimal representing binary value (0- 65535)
        00000000 00000001 enables ink
        00000000 00000010 enable Tank heater
        00000000 00000100 enable External heater
        00000000 00001000 enable recirc
        00000000 00010000 enable user pwm
        00000000 00100000 enable pressure data streaming
        00000000 01000000 enable onboard purge button
        00000000 10000000 USE INTERNAL SIGNALS
        00000001 00000000 enable Hard Purge from HW Inputs
        00000010 00000000 enable external purge signal
        00000100 00000000 use pin12 as bulk level(else used as bcd purge)
        00001000 00000000 invert bottle empty signal
        00010000 00000000 invert user input signal
        00100000 00000000 enable degass(if fitted)
        01000000 00000000 Use manual recirc speed(Not on Midas)
        10000000 00000000 enable pull mode(Not on Midas)'''
        command = "SEB," + enable_bits + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.enable_bits['demand'] = enable_bits
            self.get_enable_bits(node_id)
        return midas_response

    def get_extended_enable_bits(self, node_id=0):
        '''Read extended enables
        Decimal representing binary value (0- 65535)
        00000000 00000001 disables system enable on power off
        00000000 00000010 disables PID loop separation algorithm(manifold systems)
        00000000 00000100 disables fill purge blocking
        00000000 00001000 disables fill recirculation on mixer configurations
        00000000 00010000 not assigned
        00000000 00100000 not assigned
        00000000 01000000 not assigned
        00000000 10000000 not assigned
        00000001 00000000 not assigned
        00000010 00000000 not assigned
        00000100 00000000 not assigned
        00001000 00000000 not assigned
        00010000 00000000 not assigned
        00100000 00000000 not assigned
        01000000 00000000 not assigned
        10000000 00000000 not assigned'''
        self.serialconn.serial_write("SEE?\r", node_id)
        self.extended_enable_bits['actual'] = self.serialconn.serial_response("get")
        return self.extended_enable_bits['actual']

    def set_extended_enable_bits(self, enable_bits, node_id=0):
        '''Set extended enables
        Decimal representing binary value (0- 65535)
        00000000 00000001 disables system enable on power off
        00000000 00000010 disables PID loop separation algorithm(manifold systems)
        00000000 00000100 disables fill purge blocking
        00000000 00001000 disables fill recirculation on mixer configurations
        00000000 00010000 not assigned
        00000000 00100000 not assigned
        00000000 01000000 not assigned
        00000000 10000000 not assigned
        00000001 00000000 not assigned
        00000010 00000000 not assigned
        00000100 00000000 not assigned
        00001000 00000000 not assigned
        00010000 00000000 not assigned
        00100000 00000000 not assigned
        01000000 00000000 not assigned
        10000000 00000000 not assigned'''
        command = "SEE," + enable_bits + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.extended_enable_bits['demand'] = enable_bits
            self.get_extended_enable_bits(node_id)
        return midas_response

    def get_dynamic_calibration_state(self, node_id=0):
        '''Gets dynamic calibration on the system
        Decimal'''
        self.serialconn.serial_write("SDC?\r", node_id)
        self.dynamic_calibration_state['actual'] = self.serialconn.serial_response("get")
        return self.dynamic_calibration_state['actual']

    def set_dynamic_calibration_state(self, calibration, node_id=0):
        '''Sets dynamic calibration on the system
        Decimal'''
        command = "SDC," + calibration + "\r"
        self.serialconn.serial_write(command, node_id)
        midas_response = self.serialconn.serial_response("set")
        if midas_response is True:
            self.dynamic_calibration_state['demand']= calibration
            self.get_dynamic_calibration_state(node_id)
        return midas_response


help(Midas.get_dynamic_calibration_state)