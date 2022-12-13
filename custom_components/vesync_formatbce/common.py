"""Common utilities for VeSync Component."""
import logging
from typing import Dict, List

from homeassistant.helpers.entity import ToggleEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    Debouncer,
    CoordinatorEntity,
)

from pyvesync import VeSync

from .const import DOMAIN, VS_FANS, VS_LIGHTS, VS_SWITCHES, VS_HUMIDIFIERS, SCAN_INTERVAL, DEBOUNCE_COOLDOWN

_LOGGER = logging.getLogger(__name__)

HUMI_DEV_TYPE_TO_HA = {
    "Classic300S": "humidifier",
    "Dual200S": "humidifier",
    "Dual301S": "humidifier",
    "LUH-D301S-WEU": "humidifier",
}

HUMI_PROPS = {
    "Classic300S": [VS_HUMIDIFIERS, VS_SWITCHES, VS_LIGHTS],
    "Dual200S": [VS_HUMIDIFIERS, VS_SWITCHES],
}


class CoordinatedVeSyncDevice:
    """"Container wrapping VeSync device and attached DataUpdateCoordinator."""
    def __init__(self, hass: HomeAssistant, device) -> None:
        self.hass = hass
        self.device = device
        self.coordinator = DataUpdateCoordinator(
            hass,
            _LOGGER,
            name=self.device_name,
            update_method=self.async_update_data,
            update_interval=SCAN_INTERVAL,
            request_refresh_debouncer=Debouncer(
                hass, _LOGGER, cooldown=DEBOUNCE_COOLDOWN, immediate=True
            ),
        )

    async def async_update_data(self):
        _LOGGER.debug("Fetching latest data")
        await self.hass.async_add_executor_job(self.device.update)
        return self.device

    @property
    def device_type(self) -> str:
        return self.device.device_type

    @property
    def device_name(self):
        return self.device.device_name


async def async_process_devices(hass: HomeAssistant, manager: VeSync) -> Dict[str, List[CoordinatedVeSyncDevice]]:
    """Assign devices to proper component."""
    devices: Dict[str, List[CoordinatedVeSyncDevice]] = {}
    devices[VS_SWITCHES] = []
    devices[VS_FANS] = []
    devices[VS_LIGHTS] = []
    devices[VS_HUMIDIFIERS] = []

    await hass.async_add_executor_job(manager.update)

    fans_count = 0
    humidifiers_count = 0
    lights_count = 0
    outlets_count = 0
    switches_count = 0
    if manager.fans:
        for fan in manager.fans:
            coordinated_fan = CoordinatedVeSyncDevice(hass, fan)

            if HUMI_PROPS.get(fan.device_type):
                if (VS_HUMIDIFIERS in HUMI_PROPS.get(fan.device_type)):
                    devices[VS_HUMIDIFIERS].append(coordinated_fan)
                    humidifiers_count += 1
                if (VS_SWITCHES in HUMI_PROPS.get(fan.device_type)):
                    devices[VS_SWITCHES].append(coordinated_fan)
                    switches_count += 1
                if (VS_LIGHTS in HUMI_PROPS.get(fan.device_type)):
                    devices[VS_LIGHTS].append(coordinated_fan)
                    lights_count += 1
            else:
                devices[VS_FANS].append(coordinated_fan)
                fans_count += 1

    if manager.bulbs:
        for bulb in manager.bulbs:
            coordinated_bulb = CoordinatedVeSyncDevice(hass, bulb)
            devices[VS_LIGHTS].append(coordinated_bulb)
            lights_count += 1

    if manager.outlets:
        for outlet in manager.outlets:
            coordinated_outlet = CoordinatedVeSyncDevice(hass, outlet)
            devices[VS_SWITCHES].append(coordinated_outlet)
            outlets_count += 1

    if manager.switches:
        for switch in manager.switches:
            coordinated_switch = CoordinatedVeSyncDevice(hass, switch)
            if not switch.is_dimmable():
                devices[VS_SWITCHES].append(coordinated_switch)
            else:
                devices[VS_LIGHTS].append(coordinated_switch)
        switches_count += len(manager.switches)

    if fans_count > 0:
        _LOGGER.info("%d VeSync fans found", fans_count)
    if humidifiers_count > 0:
        _LOGGER.info("%d VeSync humidifiers found", humidifiers_count)
    if lights_count > 0:
        _LOGGER.info("%d VeSync lights found", lights_count)
    if outlets_count > 0:
        _LOGGER.info("%d VeSync outlets found", outlets_count)
    if switches_count > 0:
        _LOGGER.info("%d VeSync switches found", switches_count)
    return devices


class VeSyncEntity(CoordinatorEntity):
    """Base class for VeSync Device Representations."""

    def __init__(self, coordinated_device: CoordinatedVeSyncDevice):
        """Initialize the VeSync device."""
        super().__init__(coordinated_device.coordinator)
        self.device = coordinated_device.device

    @property
    def device_info(self):
        return {
            "identifiers": {
                # Serial numbers are unique identifiers within a specific domain
                (DOMAIN, self._device_id)
            },
            "name": self.device.device_name,
            "manufacturer": "Levoit",
            "model": self.device.device_type,
        }

    @property
    def _device_id(self):
        """Return the ID of this device."""
        if isinstance(self.device.sub_device_no, int):
            return f"{self.device.cid}{str(self.device.sub_device_no)}"
        return self.device.cid

    @property
    def unique_id(self):
        """Return the ID of this device."""
        if isinstance(self.device.sub_device_no, int):
            return f"{self.device.cid}{str(self.device.sub_device_no)}"
        return self.device.cid

    @property
    def name(self):
        """Return the name of the device."""
        return self.device.device_name

    @property
    def available(self) -> bool:
        """Return True if device is available."""
        return self.device.connection_status == "online"

    @callback
    def _state_update(self):
        """Call when the coordinator has an update."""
        self.async_write_ha_state()

    async def async_added_to_hass(self):
        """Subscribe to updates."""
        self.async_on_remove(self.coordinator.async_add_listener(self._state_update))


class ToggleVeSyncEntity(VeSyncEntity, ToggleEntity):
    """Base class for Toggle VeSync Device Representations."""

    @property
    def is_on(self):
        """Return True if device is on."""
        return self.device.device_status == "on"

    def turn_off(self, **kwargs):
        """Turn the device off."""
        self.device.turn_off()
