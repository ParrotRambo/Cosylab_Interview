# Cosylab challenge

**Particle Accelerator Monitoring**

In the particle accelerator, various sensor devices are deployed to monitor the operational parameters. These devices include a temperature sensor, pressure sensor, humidity sensor, radiation sensor, etc. They have an important role in ensuring the safety and efficiency of the accelerator by continuously tracking specific variables. Each device is designed to operate in different states (e.g., on, off, idle, measuring, etc.). When it is in a measuring state, the sensor is actively capturing the live data at regular intervals.

The purpose of the exercise it to prepare a software representation of the sensor devices in the accelerator and it consists of the following tasks:

-   **Device Representation -** The first task is to represent these devices in your program.
    
-   **Data Transmission -** Each device is sending the measured values to multiple recipients:
    

-   **Archiving Service -** This service is responsible for archiving the data. Make sure everything is sorted by time and no data is lost or skipped.
    
-   **Monitoring Service -** The service monitors the values and raises an alarm if any of the values fall outside their allowed intervals, indicating a possible emergency inside the facility (note that only one device sending abnormal values could mean a faulty sensor device).
    
-   **Operator clients -** Several simple clients display the real-time values to operators for easy monitoring.
    

-   **Alarm Handling -** When an alarm is triggered, the operators should be able to see that on their clients.
    
-   **[Optional task] Control Functionality -** In addition to displaying values, the clients should provide the functionality to start and stop the measurement process for all devices. Once the measurement process is stopped by an operator, no further data should be aggregated or monitored for that device type.


# Implementation

The implementation has been done in Python with the use of standard libraries. This language was chosen due to the speed of development and ease of working with network based applications.

## device.py

The file contains the implementation of the device that once started sends random float value at a fixed rate (default 3 second). It supports the change of state (on, off) by the clients. While the real world sensors are probably connected through serial ports, I have opted for HTTP based approach because emulating serial ports usually requires 3rd party drivers. For now it supports only 'temp', 'rad', 'pres' and 'hum' types of devices (in this case it's just a name that carries no other responsibility rather than identifying the device). Using other names for the devices will not result in any problems, only the monitoring service will ignore them because it doesn't have the value ranges for them.

To start a device:
```python
python device.py --type name --rate int --state on/off
```

rate - frequency of sending data in seconds (default 3)
state - starting state of the device (default 'on')
type - name of the device (e.g. temp', 'rad', 'pres', 'hum')

## aggr_server.py

This is the main part of the implementation containing the server that connects clients and services with the devices. The assumption here is that there should be a machine that first records the data from the devices before sending them to the clients/services and receiving the commands from the clients and passing them to the devices.

It supports multiple connections to any type of service/client/device. In other words we can have multiple archiving services and monitoring services working at once. This is mainly done for redundancy (maybe we want to archive data at multiple location for example).

To start server:
```python
python aggr_server.py
```

## client.py

This file contains a simple client class that upon start connects to the AggrServer instance and starts to receive data from there and outputs it to the console.  The clients supports input from user during the execution in order to send the commands to the devices.

The input might be a bit buggy due to the fact that it is done through the same console as the output.

To start client:
```python
python client.py
```

To change the state of the devices with the same type write the name of the device type and the desired state (on, off):
```python
rad on
rad off
```

## archive_svc.py

This is the archiving service. Upon start it creates a .txt file in the archive folder. The files are ended with a random number in order to make sure that the archiving services are writing to their respective files.

To start archiving service:
```python
python archive_svc.py
```

## monitor_svc.py

This is a monitoring service. It checks if the value fall out of predefined range ([10, 90] for all sensors) and sends an alarm back to the server to be sent to all connected clients. It also logs the alarms in the monitor folder in a .txt file. In order to make sure that each monitor writes to its own file a random number is added to the end of the file name.

To start monitoring service:
```python
python monitor_svc.py
```

## start_devices.py

A simple script to start a number of devices.

To start devices:
```python
python start_devices.py --state on/off --rate number --num_rad number --num_temp number --num_hum number
--num_pres number
```

rate - frequency of sending data in seconds (default 3)
state - starting state of the device (default 'on')
num_rad - number of radiation sensors (default 2)
num_temp  - number of temperature sensors (default 2)
num_hum  - number of humidity sensors (default 2)
num_pres  - number of pressure sensors (default 2)


# Starting

In order to start the implementation first start the server with
```python
python aggr_server.py
```
After that you can connect services/clients/devices in any order by starting the respective scripts
Client:
```python
python client.py
```
Archiving service:
```python
python archive_svc.py
```
Monitoring service:
```python
python monitor_svc.py
```
Device:
```python
python device.py --type name --rate int --state on/off
```
or alternatively:
```python
python start_devices.py --state on/off --rate number --num_rad number --num_temp number --num_hum number
--num_pres number
```

