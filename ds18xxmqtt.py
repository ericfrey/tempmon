#! /home/frey/src/venv/bin/python3
import time
import sys
import configparser
from os import environ
from w1thermsensor import W1ThermSensor, Unit
import configparser
import paho.mqtt.client as mqtt  # import the client
import json
from socket import gethostname
from gpiozero import CPUTemperature

hostname = gethostname()

QOS1 = 1
QOS2 = 1
CLEAN_SESSION = True


def open_config():
    # opens the config file, using the default in /etc or as specified in the environment
    global debug
    config_fname = environ.get("ds18xx_config", "/etc/ds18xx_sensors.txt")
    print(config_fname)
    config = configparser.ConfigParser()
    config.read(config_fname)
    # turn on debug flag if verbose starts with t
    if "misc" in config.sections():
        debug = config["misc"].get("verbose", "f").strip().lower()[0] == "t"
    return config


def get_mqtt_config(config):
    # gets mqtt configuration (broker, mqtt_user, and mqtt_password) from config file
    if "mqtt" not in config.sections():
        print("config file has no mqtt section")
        print(config.sections())
        exit(1)
    mqtt_user = config["mqtt"].get("mqtt_user", None)
    mqtt_passwd = config["mqtt"].get("mqtt_passwd", None)
    broker = config["mqtt"].get("broker", None)
    if mqtt_user is None or mqtt_passwd is None or broker is None:
        print("must specify mqtt_user,mqtt_passwd and broker")
        exit(1)
    return broker, mqtt_user, mqtt_passwd


def get_misc_config(config):
    # gets the units (F or C supported), update interval, and location of the sensor host
    if "misc" not in config.sections():
        print("missing misc section. Using default units and location")
        outunits = "C"
        location = "Unknown"
        interval = 60
    else:
        outunits = config["misc"].get("units", "C")
        location = config["misc"].get("location", "Unknown")
        interval = float(config["misc"].get("interval", 60))
    if outunits == "F":
        units = Unit.DEGREES_F
    elif outunits == "C":
        units = Unit.DEGREES_C
    else:
        print(f"illegal units: {outunits}")
    return units, location, interval


def get_sensors_config(config, units):
    # reads the list of sensors to query. Each sensor has a short name (key), a mac
    # address and a friendly name. See the sample ds18xx_sensors.txt file to see the format
    sensors = {}
    names = {}
    for key in config["thermsensors"]:
        # for each sensor the line is of the format key=id[,friendly name]
        # where the id is the sensor id used by w1thermsensor and friendly name
        # is an optional friendly name. If  the friendly name is not specified
        # then the key is used for the name. Note that if id is cpu, then the
        # temperature of the CPU is returned using gpizo.CPUTemperature()
        val = config["thermsensors"][key]
        if val.find(",") > 0:
            id, name = val.split(",")[0:2]
            id = id.strip()
            val = val.strip()
        else:
            id = val.strip()
            name = key
        if id.lower() == "cpu":
            sensors[key] = cpu_temp
        else:
            sensors[key] = W1ThermSensor(sensor_id=id).get_temperature
        names[key] = name
    return sensors, names


def on_disconnect(client, userdata, flags, rc=0):
    m = "DisConnected flags" + "result code " + str(rc)
    print(m)


def on_connect(client, userdata, flags, rc):
    print("Connected flags ", str(flags), "result code ", str(rc))


def on_message(client, userdata, message):
    if debug: print("message received  ", str(message.payload.decode("utf-8")))


def on_publish(client, userdata, mid):
    if debug: print("message published: mid=", str(mid))


def setup_mqtt(broker, mqtt_user, mqtt_password):
    # sets up mqtt broker and the functions that print messages on various events.
    client = mqtt.Client(
        hostname + ".blemqtt", clean_session=CLEAN_SESSION
    )  # create new instance
    client.username_pw_set(username=mqtt_user, password=mqtt_password)
    client.on_disconnect = on_disconnect
    client.on_connect = on_connect
    if debug:
        client.on_publish = on_publish
    client.connect(broker)
    return client


def cpu_temp(units):
    # uses gpiozero CPUTemperature function to ge the CPU temperature
    # units are from the w1thermsensors.units module
    temp = CPUTemperature().value * 100
    if units == Unit.DEGREES_F:
        temp = temp * 9.0 / 5.0 + 32.0
    return temp


def send_discovery_packets(mqtt_client, sensors, names, location, units):
    # send packet for each sensor so that home admin can auto discover
    # the key thing is that it has to go to the correct topic. See
    # the MQTT Discovery part of the MQTT integration for details.
    # One such config message is published for each sensor in the
    # config file.
    if units == Unit.DEGREES_F:
        outunits = "°F"
    elif units == Unit.DEGREES_C:
        outunits = "C"
    else:
        outunits = "?"
    for id, mac in sensors.items():
        name = names[id]
        payload = dict(
            device_class="temperature",
            name=name,
            state_topic=f"thermsensor/{location}",
            unit_of_meas=outunits,
            val_tpl="{{value_json['%s']}}" % (id),
        )
        if debug: print(payload)
        mqtt_client.publish(
            f"homeassistant/sensor/thermsensor/{location}_{id}/config",
            retain=True,
            payload=json.dumps(payload),
        )


config = open_config()
broker, mqtt_user, mqtt_passwd = get_mqtt_config(config)
mqtt_client = setup_mqtt(broker, mqtt_user, mqtt_passwd)
outunits, location, report_interval = get_misc_config(config)
sensors, names = get_sensors_config(config, outunits)
if debug: print(sensors)

send_discovery_packets(mqtt_client, sensors, names, location, outunits)
while True:
    last = time.time()
    n = 0
    payload = {}
    # prepare the payload. All the sensors data are published in a single topic where the key is the sensors key and the value is
    # the sensor's temperature
    for key in sensors:
        sensor = sensors[key]
        temp = sensors[key](outunits)
        payload[key] = f"{temp:.2f}"
    if debug:
        print(payload)
    mqtt_client.publish(
        f"thermsensor/{location}", retain=True, payload=json.dumps(payload)
    )
    now = time.time()
    # report interval is specified in the config file
    sleeptime = last + report_interval - now
    time.sleep(sleeptime)
