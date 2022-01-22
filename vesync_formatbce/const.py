"""Constants for VeSync Component."""
from datetime import timedelta

DOMAIN = "vesync_formatbce"
VS_DISPATCHERS = "vesync_dispatchers"
VS_DISCOVERY = "vesync_discovery_{}"
SERVICE_UPDATE_DEVS = "update_devices"

VS_SWITCHES = "switches"
VS_FANS = "fans"
VS_HUMIDIFIERS = "humidifiers"
VS_LIGHTS = "lights"
VS_MANAGER = "manager"

SCAN_INTERVAL = timedelta(seconds=1)
DEBOUNCE_COOLDOWN = 15  # Seconds