# CIMSII-Midas_Ink_Control
Python library for communicating with a Megnajet/Xaar CIMS II/HV/Midas ink system.

This library uses RS422 communication with the CIMS II/Midas ink system.

# Dependencies

This program requires the use of [pySerial](https://github.com/pyserial/pyserial)

# Usage

1) Create a ``Midas`` object
``` python
import midas_comms

Midas = midas_comms.Midas()
```
2) The ``Midas`` object opens communications by calling the ``create_serial_connection(port)`` function with the port name as an argument. Baud rate, etc. can also be passed as arguments, but are set at a default. This function creates a ``Midas_Serial`` object tied to the ``Midas`` object.

``` python
Midas.create_serial_connection('/dev/ttyUSB0')

# The default settings are used as arguments below
Midas.create_serial_connection('/dev/ttyUSB0', baudrate=115200,
                                 stopbits=serial.STOPBITS_ONE,
                                 parity=serial.PARITY_NONE,
                                 databits=serial.EIGHTBITS, timeout=2):
```
3) The different parameters of the Midas can be accessed through different sub-classes, as well as some through the main Midas class:

``` python
Midas() - general control and information
Midas.Status() - alarms and status bits
Midas.Pressures() - infeed, meniscus  parameters
Midas.Temperatures() - heater parameters
Midas.Pumps() - recirc and meiscus pumps
Midas.Purge() - purge pressures and control
```

# Common Enable Bits Combinations

There are a few common enable bits that will most likely be used in all programs:

|   |   |   |   |   |
|---|---|---|---|---|
|Value|Ink Enable Command|Recirc.  Command|Fill Pump Command|Description|
|36922|0|0|0|Off|
|32896|0|0|1|Off|
|36933|1|0|0|Off|
|37001|1|1|0|Turns on the recirculation and enables printing|
|32897|1|0|1|Fills reservoir - needs 32905 sending first|
|32905|1|1|1|Fills reservoir when needed, prints|

NOTE: There is a quirk with having just the fill pump on, the system must be fully enabled, and then the recirculation and enable printing disabled.

They can be set using:

``` python
Midas.set_enable_bits(32905)  # Fully enable the Miday system
```

This is equivilent to sending ``SEB,32905\r`` through the serial port.