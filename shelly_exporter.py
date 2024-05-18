#!/usr/bin/env python3
# coding: utf-8
# pyright: reportMissingImports=false

"""Shelly Exporter"""

import json
import logging
import os
import sys
import threading
import time
from datetime import datetime
from typing import Callable
from wsgiref.simple_server import make_server

import pytz
import requests
from prometheus_client import PLATFORM_COLLECTOR, PROCESS_COLLECTOR
from prometheus_client.core import REGISTRY, CollectorRegistry, Metric
from prometheus_client.exposition import _bake_output, _SilentHandler, parse_qs

SHELLY_EXPORTER_NAME = os.environ.get("SHELLY_EXPORTER_NAME", "shelly-exporter")
SHELLY_EXPORTER_LOGLEVEL = os.environ.get("SHELLY_EXPORTER_LOGLEVEL", "INFO").upper()
SHELLY_EXPORTER_TZ = os.environ.get("TZ", "Europe/Paris")


def make_wsgi_app(
    registry: CollectorRegistry = REGISTRY, disable_compression: bool = False
) -> Callable:
    """Create a WSGI app which serves the metrics from a registry."""

    def prometheus_app(environ, start_response):
        # Prepare parameters
        accept_header = environ.get("HTTP_ACCEPT")
        accept_encoding_header = environ.get("HTTP_ACCEPT_ENCODING")
        params = parse_qs(environ.get("QUERY_STRING", ""))
        headers = [
            ("Server", ""),
            ("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0"),
            ("Pragma", "no-cache"),
            ("Expires", "0"),
            ("X-Content-Type-Options", "nosniff"),
        ]
        if environ["PATH_INFO"] == "/":
            status = "301 Moved Permanently"
            headers.append(("Location", "/metrics"))
            output = b""
        elif environ["PATH_INFO"] == "/favicon.ico":
            status = "200 OK"
            output = b""
        elif environ["PATH_INFO"] == "/metrics":
            status, tmp_headers, output = _bake_output(
                registry,
                accept_header,
                accept_encoding_header,
                params,
                disable_compression,
            )
            headers += tmp_headers
        else:
            status = "404 Not Found"
            output = b""
        start_response(status, headers)
        return [output]

    return prometheus_app


def start_wsgi_server(
    port: int,
    addr: str = "0.0.0.0",  # nosec B104
    registry: CollectorRegistry = REGISTRY,
) -> None:
    """Starts a WSGI server for prometheus metrics as a daemon thread."""
    app = make_wsgi_app(registry)
    httpd = make_server(addr, port, app, handler_class=_SilentHandler)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.daemon = True
    thread.start()


start_http_server = start_wsgi_server


# Logging Configuration
try:
    pytz.timezone(SHELLY_EXPORTER_TZ)
    logging.Formatter.converter = lambda *args: datetime.now(
        tz=pytz.timezone(SHELLY_EXPORTER_TZ)
    ).timetuple()
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
        level=SHELLY_EXPORTER_LOGLEVEL,
    )
except pytz.exceptions.UnknownTimeZoneError:
    logging.Formatter.converter = lambda *args: datetime.now(
        tz=pytz.timezone("Europe/Paris")
    ).timetuple()
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
        level="INFO",
    )
    logging.error("TZ invalid : %s !", SHELLY_EXPORTER_TZ)
    os._exit(1)
except ValueError:
    logging.basicConfig(
        stream=sys.stdout,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%d/%m/%Y %H:%M:%S",
        level="INFO",
    )
    logging.error("SHELLY_EXPORTER_LOGLEVEL invalid !")
    os._exit(1)

# Check for SHELLY_HOST
SHELLY_HOST = None
if os.environ.get("SHELLY_HOST") is not None and os.environ.get("SHELLY_HOST") != "":
    SHELLY_HOST = os.environ.get("SHELLY_HOST")
else:
    logging.error("SHELLY_HOST must be set and not empty !")
    os._exit(1)

SHELLY_SCHEME = os.environ.get("SHELLY_SCHEME", "http")
if SHELLY_SCHEME not in ["http", "https"]:
    logging.error("SHELLY_SCHEME must be 'http' or 'https' !")
    os._exit(1)

# Check for SHELLY_EXPORTER_PORT
try:
    SHELLY_EXPORTER_PORT = int(os.environ.get("SHELLY_EXPORTER_PORT", "8123"))
except ValueError:
    logging.error("SHELLY_EXPORTER_PORT must be int !")
    os._exit(1)

METRICS = [
    {
        "name": "bluetooth_state",
        "description": "Bluetooth State (1: ON, 0: OFF",
        "type": "gauge",
    },
    {
        "name": "cloud_state",
        "description": "Cloud State (1: ON, 0: OFF",
        "type": "gauge",
    },
    {
        "name": "mqtt_state",
        "description": "MQTT State (1: ON, 0: OFF",
        "type": "gauge",
    },
    {
        "name": "apower",
        "description": "Power (Watt)",
        "type": "gauge",
    },
    {
        "name": "voltage",
        "description": "Voltage (Volt)",
        "type": "gauge",
    },
    {
        "name": "current",
        "description": "Current (Ampere)",
        "type": "gauge",
    },
    {
        "name": "output_state",
        "description": "Output State (1: ON, 0: OFF)",
        "type": "gauge",
    },
    {
        "name": "temperature",
        "description": "Temperature (°C)",
        "type": "gauge",
    },
    {
        "name": "wifi_rssi",
        "description": "Wifi Signal Strength",
        "type": "gauge",
    },
    {
        "name": "fs_size",
        "description": "Total amount of FS in bytes",
        "type": "gauge",
    },
    {
        "name": "fs_free",
        "description": "Available amount of FS in bytes",
        "type": "gauge",
    },
    {
        "name": "ram_size",
        "description": "Total amount of RAM in bytes",
        "type": "gauge",
    },
    {
        "name": "ram_free",
        "description": "Available amount of RAM in bytes",
        "type": "gauge",
    },
    {
        "name": "uptime",
        "description": "Seconds elapsed since boot",
        "type": "counter",
    },
]

# REGISTRY Configuration
REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(REGISTRY._names_to_collectors["python_gc_objects_collected_total"])


class ShellyCollector:
    """Shelly Collector Class"""

    def __init__(self):
        self.session = requests.session()
        self.api_endpoint = f"{SHELLY_SCHEME}://{SHELLY_HOST}/rpc"

    def get_data(self):
        """Get Shelly Data"""
        # Init Default Dicts
        labels = {}
        data = {}
        # Job
        labels["job"] = SHELLY_EXPORTER_NAME
        # Collect Shelly Data
        try:
            shelly_info = self.session.get(
                f"{self.api_endpoint}/Shelly.GetDeviceInfo"
            ).json()
            shelly_config = self.session.get(
                f"{self.api_endpoint}/Shelly.GetConfig"
            ).json()
            shelly_status = self.session.get(
                f"{self.api_endpoint}/Shelly.GetStatus"
            ).json()
        except json.decoder.JSONDecodeError:
            logging.error("Invalid JSON Response")
            os._exit(1)
        except requests.exceptions.ConnectionError as exception:
            logging.error(exception)
            os._exit(1)

        # Shelly Model
        labels["model"] = shelly_info["app"]
        # Firmware Version
        labels["firmware"] = shelly_info["ver"]
        # Bluetooth State
        if shelly_config["ble"]["enable"]:
            data["bluetooth_state"] = 1
        else:
            data["bluetooth_state"] = 0
        # Cloud State
        if shelly_config["cloud"]["enable"]:
            data["cloud_state"] = 1
        else:
            data["cloud_state"] = 0
        # MQTT State
        if shelly_config["mqtt"]["enable"]:
            data["mqtt_state"] = 1
        else:
            data["mqtt_state"] = 0
        # Output State
        if shelly_status["switch:0"]["output"]:
            data["output_state"] = 1
        else:
            data["output_state"] = 0
        # APower
        data["apower"] = shelly_status["switch:0"]["apower"]
        # Voltage
        data["voltage"] = shelly_status["switch:0"]["voltage"]
        # Current
        data["current"] = shelly_status["switch:0"]["current"]
        # Temperature
        data["temperature"] = shelly_status["switch:0"]["temperature"]["tC"]
        # Uptime
        data["uptime"] = shelly_status["sys"]["uptime"]
        # RAM Size
        data["ram_size"] = shelly_status["sys"]["ram_size"]
        # RAM Free
        data["ram_free"] = shelly_status["sys"]["ram_free"]
        # FS Size
        data["fs_size"] = shelly_status["sys"]["fs_size"]
        # RAM Free
        data["fs_free"] = shelly_status["sys"]["fs_free"]
        # Wifi IP
        labels["wifi_ip"] = shelly_status["wifi"]["sta_ip"]
        # Wifi RSSI
        data["wifi_rssi"] = shelly_status["wifi"]["rssi"]
        return labels, data

    def collect(self):
        """Collect Prometheus Metrics"""
        # Get Data
        labels, data = self.get_data()
        logging.info("Labels : %s.", dict(labels))
        logging.info("Data : %s.", dict(data))
        # Forge Prometheus Metrics
        metrics = []
        for key, value in data.items():
            if key in labels:
                continue
            description = [i["description"] for i in METRICS if key == i["name"]][0]
            metric_type = [i["type"] for i in METRICS if key == i["name"]][0]
            metrics.append(
                {
                    "name": f"shelly_{key.lower()}",
                    "value": int(value),
                    "description": description,
                    "type": metric_type,
                }
            )
        # Return Prometheurs Metrics
        for metric in metrics:
            prometheus_metric = Metric(
                metric["name"], metric["description"], metric["type"]
            )
            prometheus_metric.add_sample(
                metric["name"], value=metric["value"], labels=labels
            )
            yield prometheus_metric


def main():
    """Main Function"""
    logging.info("Starting Shelly Exporter on port %s.", SHELLY_EXPORTER_PORT)
    logging.debug("SHELLY_EXPORTER_PORT: %s.", SHELLY_EXPORTER_PORT)
    logging.debug("SHELLY_EXPORTER_NAME: %s.", SHELLY_EXPORTER_NAME)
    # Start Prometheus HTTP Server
    start_http_server(SHELLY_EXPORTER_PORT)
    # Init ShellyCollector
    REGISTRY.register(ShellyCollector())
    # Infinite Loop
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
