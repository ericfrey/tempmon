This contain two services that use the w1thermsensors module from PyPi
to read temperatures from ds18xx 1-wire temperature sensors.

tempmon.py sents the temperatures to the lowpowerlabs server via an http request. It is configure using sensors.txt, which tells the sensor id and mac addresses for sensors to read.

ds18xxmqtt.py sents the temperatures to a mqtt server. The data are
sent in  format that enables autodiscovery in home assistant. Note
that you must restart for home assistant to discover the sensors. The
configuration is in ds18xx_sensors.txt. By default, this is in /etc, but
it can be overridden by setting the environment variable ds18xx_config.
The sensors file is read using Pythons configparser module and contains
3 sections: mqtt, misc, and sensors. A default file is included in the
repository to show the format. The mqtt section contains the password
for the mqtt user, so the file should be read only by non-root and the
group sensorsdaemon specified in the sample systemd service file. To
install the daemon, copy ds18xxmqtt.service to /etc/systemd/system and remove
all permissions for group and other. Then, enable the service using
systemctl enable ds18xxmqtt.service. Note that you should previously
edit the config file discussed above, put it in /etc, add the sensorsdaemon group,
and set the group and permissions of the config file as discussed above.


