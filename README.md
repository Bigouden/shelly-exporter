# Shelly Exporter

## Quick Start

```bash
DOCKER_BUILDKIT=1 docker build -t shelly-exporter .
docker run -dit --name shelly-exporter --env SHELLY_HOST=<ip_or_hostname> shelly-exporter
```

## Metrics

```bash
# HELP shelly_bluetooth_state Bluetooth State (1: ON, 0: OFF
# TYPE shelly_bluetooth_state gauge
shelly_bluetooth_state{firmware="0.11.3",job="shelly-exporter",model="Plus1PM",wifi_ip="192.168.10.250"} 0.0
# HELP shelly_cloud_state Cloud State (1: ON, 0: OFF
# TYPE shelly_cloud_state gauge
shelly_cloud_state{firmware="0.11.3",job="shelly-exporter",model="Plus1PM",wifi_ip="192.168.10.250"} 1.0
# HELP shelly_mqtt_state MQTT State (1: ON, 0: OFF
# TYPE shelly_mqtt_state gauge
shelly_mqtt_state{firmware="0.11.3",job="shelly-exporter",model="Plus1PM",wifi_ip="192.168.10.250"} 0.0
# HELP shelly_output_state Output State (1: ON, 0: OFF)
# TYPE shelly_output_state gauge
shelly_output_state{firmware="0.11.3",job="shelly-exporter",model="Plus1PM",wifi_ip="192.168.10.250"} 1.0
# HELP shelly_apower Power (Watt)
# TYPE shelly_apower gauge
shelly_apower{firmware="0.11.3",job="shelly-exporter",model="Plus1PM",wifi_ip="192.168.10.250"} 22.0
# HELP shelly_voltage Voltage (Volt)
# TYPE shelly_voltage gauge
shelly_voltage{firmware="0.11.3",job="shelly-exporter",model="Plus1PM",wifi_ip="192.168.10.250"} 257.0
# HELP shelly_current Current (Ampere)
# TYPE shelly_current gauge
shelly_current{firmware="0.11.3",job="shelly-exporter",model="Plus1PM",wifi_ip="192.168.10.250"} 0.0
# HELP shelly_temperature Temperature (°C)
# TYPE shelly_temperature gauge
shelly_temperature{firmware="0.11.3",job="shelly-exporter",model="Plus1PM",wifi_ip="192.168.10.250"} 47.0
# HELP shelly_uptime_total Seconds elapsed since boot
# TYPE shelly_uptime_total counter
shelly_uptime{firmware="0.11.3",job="shelly-exporter",model="Plus1PM",wifi_ip="192.168.10.250"} 2.27239e+06
# HELP shelly_ram_size Total amount of RAM in bytes
# TYPE shelly_ram_size gauge
shelly_ram_size{firmware="0.11.3",job="shelly-exporter",model="Plus1PM",wifi_ip="192.168.10.250"} 234972.0
# HELP shelly_ram_free Available amount of RAM in bytes
# TYPE shelly_ram_free gauge
shelly_ram_free{firmware="0.11.3",job="shelly-exporter",model="Plus1PM",wifi_ip="192.168.10.250"} 157116.0
# HELP shelly_fs_size Total amount of FS in bytes
# TYPE shelly_fs_size gauge
shelly_fs_size{firmware="0.11.3",job="shelly-exporter",model="Plus1PM",wifi_ip="192.168.10.250"} 458752.0
# HELP shelly_fs_free Available amount of FS in bytes
# TYPE shelly_fs_free gauge
shelly_fs_free{firmware="0.11.3",job="shelly-exporter",model="Plus1PM",wifi_ip="192.168.10.250"} 163840.0
# HELP shelly_wifi_rssi Wifi Signal Strength
# TYPE shelly_wifi_rssi gauge
shelly_wifi_rssi{firmware="0.11.3",job="shelly-exporter",model="Plus1PM",wifi_ip="192.168.10.250"} -70.0
```
