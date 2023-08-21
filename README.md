# CIMSII-Midas_Ink_Control
Python library for communicating with a Megnajet/Xaar CIMS II/HV/Midas ink control system.

This library uses RS422 communication with the CIMS II/Midas

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
Midas()
Midas.Status()
Midas.Pressures()
Midas.Temperatures()
Midas.Pumps()
Midas.Purge()
