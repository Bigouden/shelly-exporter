#!/usr/bin/env python3
#coding: utf-8

'''Shelly Exporter'''

import logging
import os
import json
import sys
import time
from collections import defaultdict
import requests
from prometheus_client.core import REGISTRY, Metric
from prometheus_client import start_http_server, PROCESS_COLLECTOR, PLATFORM_COLLECTOR

SHELLY_EXPORTER_NAME = os.environ.get('SHELLY_EXPORTER_NAME',
                                      'shelly-exporter')
SHELLY_EXPORTER_LOGLEVEL = os.environ.get('SHELLY_EXPORTER_LOGLEVEL',
                                          'INFO').upper()

# Logging Configuration
try:
    logging.basicConfig(stream=sys.stdout,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S',
                        level=SHELLY_EXPORTER_LOGLEVEL)
except ValueError:
    logging.basicConfig(stream=sys.stdout,
                        format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%d/%m/%Y %H:%M:%S',
                        level='INFO')
    logging.error("SHELLY_EXPORTER_LOGLEVEL invalid !")
    sys.exit(1)

# Check for SHELLY_HOST
if os.environ.get('SHELLY_HOST') is not None and os.environ.get('SHELLY_HOST') != '':
    SHELLY_HOST = os.environ.get('SHELLY_HOST')
else:
    logging.error("SHELLY_HOST must be set and not empty !")
    sys.exit(1)

# Check for SHELLY_EXPORTER_PORT
try:
    SHELLY_EXPORTER_PORT = int(os.environ.get('SHELLY_EXPORTER_PORT', '8123'))
except ValueError:
    logging.error("SHELLY_EXPORTER_PORT must be int !")
    sys.exit(1)

METRICS = [
    {'name': 'bluetooth_state', 'description': 'Bluetooth State (1: ON, 0: OFF', 'type': 'gauge'},
    {'name': 'cloud_state', 'description': 'Cloud State (1: ON, 0: OFF', 'type': 'gauge'},
    {'name': 'mqtt_state', 'description': 'MQTT State (1: ON, 0: OFF', 'type': 'gauge'},
    {'name': 'apower', 'description': 'Power (Watt)', 'type': 'gauge'},
    {'name': 'voltage', 'description': 'Voltage (Volt)', 'type': 'gauge'},
    {'name': 'current', 'description': 'Current (Amperer)', 'type': 'gauge'},
    {'name': 'output_state', 'description': 'Output State (1: ON, 0: OFF)', 'type': 'gauge'},
    {'name': 'temperature', 'description': 'Temperature (°C)', 'type': 'gauge'},
    {'name': 'wifi_rssi', 'description': 'Wifi Signal Strentgh', 'type': 'gauge'},
    {'name': 'fs_free', 'description': 'Available amount of FS in bytes', 'type': 'gauge'},
    {'name': 'ram_free', 'description': 'Available amount of RAM in bytes', 'type': 'gauge'},
    {'name': 'uptime', 'description': 'Seconds elapsed since boot', 'type': 'counter'}
]

# REGISTRY Configuration
REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(REGISTRY._names_to_collectors['python_gc_objects_collected_total'])

class ShellyCollector():
    '''Shelly Collector Class'''
    def __init__(self):
        self.session = requests.session()
        self.api_endpoint = f"http://{SHELLY_HOST}/rpc"

    def get_data(self):
        '''Get Shelly Data'''
        # Init Default Dicts
        labels = defaultdict(dict)
        data = defaultdict(dict)
        # Job
        labels['job'] = SHELLY_EXPORTER_NAME
        # Collect Shelly Data
        try:
            shelly_info = self.session.get(f"{self.api_endpoint}/Shelly.GetDeviceInfo").json()
            shelly_config = self.session.get(f"{self.api_endpoint}/Shelly.GetConfig").json()
            shelly_status = self.session.get(f"{self.api_endpoint}/Shelly.GetStatus").json()
        except json.decoder.JSONDecodeError:
            logging.error("Invalid JSON Response")
            sys.exit(1)
        except requests.exceptions.ConnectionError as exception:
            logging.error(exception)
            sys.exit(1)

        # Shelly Model
        labels['model'] = shelly_info['app']
        # Firmware Version
        labels['firmware'] = shelly_info['ver']
        # Bluetooth State
        if shelly_config['ble']['enable']:
            data['bluetooth_state'] = 1
        else:
            data['bluetooth_state'] = 0
        # Cloud State
        if shelly_config['cloud']['enable']:
            data['cloud_state'] = 1
        else:
            data['cloud_state'] = 0
        # MQTT State
        if shelly_config['mqtt']['enable']:
            data['mqtt_state'] = 1
        else:
            data['mqtt_state'] = 0
        # Output State
        if shelly_status['switch:0']['output']:
            data['output_state'] = 1
        else:
            data['output_state'] = 0
        # APower
        data['apower'] = shelly_status['switch:0']['apower']
        # Voltage
        data['voltage'] = shelly_status['switch:0']['voltage']
        # Current
        data['current'] = shelly_status['switch:0']['current']
        # Temperature
        data['temperature'] = shelly_status['switch:0']['temperature']['tC']
        # Uptime
        data['uptime'] = shelly_status['sys']['uptime']
        # RAM Size
        labels['ram_size'] = str(shelly_status['sys']['ram_size'])
        # RAM Free
        data['ram_free'] = shelly_status['sys']['ram_free']
        # FS Size
        labels['fs_size'] = str(shelly_status['sys']['fs_size'])
        # RAM Free
        data['fs_free'] = shelly_status['sys']['fs_free']
        # Wifi IP
        labels['wifi_ip'] = shelly_status['wifi']['sta_ip']
        # Wifi RSSI
        data['wifi_rssi'] = shelly_status['wifi']['rssi']
        return labels, data

    def collect(self):
        '''Collect Prometheus Metrics'''
        # Get Data
        labels, data = self.get_data()
        logging.info('Labels : %s.', dict(labels))
        logging.info('Data : %s.', dict(data))
        # Forge Prometheus Metrics
        metrics = []
        for key, value in data.items():
            if key in labels.keys():
                continue
            description = [i['description'] for i in METRICS if key == i['name']][0]
            metric_type = [i['type'] for i in METRICS if key == i['name']][0]
            metrics.append({'name': f'shelly_{key.lower()}',
                            'value': int(value),
                            'description': description,
                            'type': metric_type
                          })
        # Return Prometheurs Metrics
        for metric in metrics:
            prometheus_metric = Metric(metric['name'], metric['description'], metric['type'])
            prometheus_metric.add_sample(metric['name'], value=metric['value'], labels=labels)
            yield prometheus_metric

def main():
    '''Main Function'''
    logging.info("Starting Shelly Exporter on port %s.", SHELLY_EXPORTER_PORT)
    logging.debug("SHELLY_EXPORTER_PORT: %s.", SHELLY_EXPORTER_PORT)
    logging.debug("SHELLY_EXPORTER_NAME: %s.", SHELLY_EXPORTER_NAME)
    # Start Prometheus HTTP Server
    start_http_server(SHELLY_EXPORTER_PORT)
    # Init HueMotionSensorCollector
    REGISTRY.register(ShellyCollector())
    # Loop Infinity
    while True:
        time.sleep(1)

if __name__ == '__main__':
    main()
