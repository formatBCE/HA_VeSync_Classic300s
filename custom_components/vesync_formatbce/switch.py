"""Support for VeSync switches."""
import logging
from typing import List

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .common import CoordinatedVeSyncDevice, ToggleVeSyncEntity
from .const import DOMAIN, VS_DISCOVERY, VS_DISPATCHERS, VS_SWITCHES

_LOGGER = logging.getLogger(__name__)

DEV_TYPE_TO_HA = {
    "wifi-switch-1.3": "outlet",
    "ESW03-USA": "outlet",
    "ESW01-EU": "outlet",
    "ESW15-USA": "outlet",
    "ESWL01": "switch",
    "ESWL03": "switch",
    "ESO15-TB": "outlet",
    "Classic300S": "humidifier_display",
    "Dual200S": "humidifier_display",
    "Dual301S": "humidifier_display",
    "LUH-D301S-WEU": "humidifier_display",
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up switches."""

    async def async_discover(devices):
        """Add new devices to platform."""
        _async_setup_entities(devices, async_add_entities)

    disp = async_dispatcher_connect(
        hass, VS_DISCOVERY.format(VS_SWITCHES), async_discover
    )
    hass.data[DOMAIN][VS_DISPATCHERS].append(disp)

    _async_setup_entities(hass.data[DOMAIN][VS_SWITCHES], async_add_entities)
    return True


@callback
def _async_setup_entities(devices: List[CoordinatedVeSyncDevice], async_add_entities):
    """Check if device is online and add entity."""
    dev_list = []
    for dev in devices:
        if DEV_TYPE_TO_HA.get(dev.device_type) == "outlet":
            dev_list.append(VeSyncSwitchHA(dev))
        elif DEV_TYPE_TO_HA.get(dev.device_type) == "switch":
            dev_list.append(VeSyncLightSwitch(dev))
        elif DEV_TYPE_TO_HA.get(dev.device_type) == "humidifier_display":
            dev_list.append(VeSyncHumidifierDisplaySwitch(dev))
        else:
            _LOGGER.warning(
                "%s - Unknown device type - %s", dev.device_name, dev.device_type
            )
            continue

    async_add_entities(dev_list, update_before_add=True)


class VeSyncBaseSwitch(ToggleVeSyncEntity, SwitchEntity):
    """Base class for VeSync switch Device Representations."""

    def turn_on(self, **kwargs):
        """Turn the device on."""
        self.device.turn_on()


class VeSyncSwitchHA(VeSyncBaseSwitch, SwitchEntity):
    """Representation of a VeSync switch."""

    def __init__(self, plug):
        """Initialize the VeSync switch device."""
        super().__init__(plug)
        self.smartplug = plug

    @property
    def extra_state_attributes(self):
        """Return the state attributes of the device."""
        if not hasattr(self.smartplug, "weekly_energy_total"):
            return {}
        return {
            "voltage": self.smartplug.voltage,
            "weekly_energy_total": self.smartplug.weekly_energy_total,
            "monthly_energy_total": self.smartplug.monthly_energy_total,
            "yearly_energy_total": self.smartplug.yearly_energy_total,
        }

    @property
    def current_power_w(self):
        """Return the current power usage in W."""
        return self.smartplug.power

    @property
    def today_energy_kwh(self):
        """Return the today total energy usage in kWh."""
        return self.smartplug.energy_today

    def update(self):
        """Update outlet details and energy usage."""
        self.smartplug.update()
        self.smartplug.update_energy()


class VeSyncLightSwitch(VeSyncBaseSwitch, SwitchEntity):
    """Handle representation of VeSync Light Switch."""

    def __init__(self, switch):
        """Initialize Light Switch device class."""
        super().__init__(switch)
        self.switch = switch

class VeSyncHumidifierDisplaySwitch(ToggleVeSyncEntity, SwitchEntity):
    """Class for VeSync humidifier display switch Device Representations."""
       
    @property
    def name(self):
        return self.device.device_name + " (display)"

    @property
    def is_on(self):
        """Return True if device is on."""
        return self.device.enabled and self.device.details["display"]

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self.device.turn_off_display()


    def turn_on(self, **kwargs):
        """Turn the device on."""
        self.device.turn_on_display()
