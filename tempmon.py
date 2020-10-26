#! /usr/bin/python3
import time
import sys
import configparser
import requests
from w1thermsensor import W1ThermSensor
import requests
from urllib3.exceptions import InsecureRequestWarning

# Suppress only the single warning from urllib3 needed.
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

config_fname='sensors.txt'
config=configparser.ConfigParser()
config.read(config_fname)
host='raspi4.lan'
debug=False


report_interval=15
sensors={}
units=W1ThermSensor.DEGREES_F
for key in config['thermosensors']:
	id=config['thermosensors'][key]
	sensors[key]=W1ThermSensor(sensor_id=id)
while True:
	last=time.time()
	vals=[]
	n=0
	for key in sensors:
		sensor=sensors[key]
		temp=sensors[key].get_temperature(units)
		val=f'{key.upper()}={temp:.2f}'
		if debug: print(time.asctime(time.localtime()),val) 
		vals.append(val)
	if debug: print(50*'-')
	req = requests.get(f"https://{host}/httpendpoint?id=1234&{'&'.join(vals)}", auth=("pi","TarPon23"), verify=False)
	now=time.time()
	sleeptime=last+report_interval-now
	time.sleep(sleeptime)
