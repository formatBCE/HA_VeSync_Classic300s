"""Support for VeSync Humidifier's sensors."""
import logging

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.components.sensor import STATE_CLASS_MEASUREMENT, SensorEntity
from homeassistant.const import DEVICE_CLASS_HUMIDITY, PERCENTAGE
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .common import VeSyncDevice
from .const import DOMAIN, VS_DISCOVERY, VS_DISPATCHERS, VS_HUMIDIFIERS

_LOGGER = logging.getLogger(__name__)

DEV_TYPE_TO_HA = {
    "Classic300S": ("high-humidity-sensor", "humidity-sensor", "water-tank-sensor", "water-lack-sensor"),
}


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up Sensors."""

    async def async_discover(devices):
        """Add new devices to platform."""
        _async_setup_entities(devices, async_add_entities)

    disp = async_dispatcher_connect(
        hass, VS_DISCOVERY.format(VS_HUMIDIFIERS), async_discover
    )
    hass.data[DOMAIN][VS_DISPATCHERS].append(disp)

    _async_setup_entities(hass.data[DOMAIN][VS_HUMIDIFIERS], async_add_entities)


@callback
def _async_setup_entities(devices, async_add_entities):
    """Check if device is online and add entity."""
    entities = []
    for dev in devices:
        if "water-tank-sensor" in DEV_TYPE_TO_HA.get(dev.device_type):
            entities.append(VeSyncHumidifierWaterTankSensor(dev))
        if "water-lack-sensor" in DEV_TYPE_TO_HA.get(dev.device_type):
            entities.append(VeSyncHumidifierWaterLackSensor(dev))
        if "humidity-sensor" in DEV_TYPE_TO_HA.get(dev.device_type):
            entities.append(VeSyncHumiditySensorHA(dev))
        if "high-humidity-sensor" in DEV_TYPE_TO_HA.get(dev.device_type):
            entities.append(VeSyncHumidifierHighHumiditySensor(dev))

    async_add_entities(entities, update_before_add=True)


class VeSyncSensorHA:
    """Base class for VeSync Device Representations."""

    def __init__(self, device):
        """Initialize the VeSync device."""
        self.device = device

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
    def name(self):
        """Return the name of the device."""
        return self.device.device_name

    @property
    def available(self) -> bool:
        """Return True if device is available."""
        return self.device.connection_status == "online"

    def update(self):
        """Update vesync device."""
        self.device.update()


class VeSyncHumiditySensorHA(VeSyncSensorHA, SensorEntity):
    """Representation of a VeSync humidity sensor."""

    _attr_device_class = DEVICE_CLASS_HUMIDITY
    _attr_state_class = STATE_CLASS_MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE

    @property
    def unique_id(self):
        """Return the ID of this device."""
        if isinstance(self.device.sub_device_no, int):
            return f"{self.device.cid}{str(self.device.sub_device_no)}_humidity_sensor"
        return f"{self.device.cid}_humidity_sensor"

    @property
    def name(self):
        """Name of sensor entity"""
        return self.device.device_name + " (humidity sensor)"

    @property
    def native_value(self):
        """Get Humidity value."""
        # get value from pyvesync library api,
        result = self.device.details["humidity"]
        try:
            # check for validity of brightness value received
            humidity = int(result)
        except ValueError:
            # deal if any unexpected/non numeric value
            _LOGGER.debug(
                "VeSync - received unexpected 'humidity' value from pyvesync api: %s",
                result,
            )
            return 0
        # convert percent brightness to ha expected range
        return humidity


class VeSyncHumidifierWaterLackSensor(VeSyncSensorHA, BinarySensorEntity):
    """Representation of a VeSync Water Lack sensor."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def unique_id(self):
        """Return the ID of this device."""
        if isinstance(self.device.sub_device_no, int):
            return f"{self.device.cid}{str(self.device.sub_device_no)}_water_lack_sensor"
        return f"{self.device.cid}_water_lack_sensor"

    @property
    def name(self):
        """Name of sensor entity"""
        return self.device.device_name + " (water lack)"

    @property
    def is_on(self):
        """Return the status of the sensor."""
        # get value from pyvesync library api,
        result = self.device.details["water_lacks"]
        try:
            # check for validity of brightness value received
            water_lacks = bool(result)
        except ValueError:
            # deal if any unexpected/non numeric value
            _LOGGER.debug(
                "VeSync - received unexpected 'water_lacks' value from pyvesync api: %s",
                result,
            )
            return False
        # convert percent brightness to ha expected range
        return water_lacks


class VeSyncHumidifierWaterTankSensor(VeSyncSensorHA, BinarySensorEntity):
    """Representation of a VeSync Water Tank sensor."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def unique_id(self):
        """Return the ID of this device."""
        if isinstance(self.device.sub_device_no, int):
            return f"{self.device.cid}{str(self.device.sub_device_no)}_water_tank_sensor"
        return f"{self.device.cid}_water_tank_sensor"

    @property
    def name(self):
        """Name of sensor entity"""
        return self.device.device_name + " (water tank)"

    @property
    def is_on(self):
        """Return the status of the sensor."""
        # get value from pyvesync library api,
        result = self.device.details["water_tank_lifted"]
        try:
            # check for validity of brightness value received
            water_tank_lifted = bool(result)
        except ValueError:
            # deal if any unexpected/non numeric value
            _LOGGER.debug(
                "VeSync - received unexpected 'water_tank_lifted' value from pyvesync api: %s",
                result,
            )
            return False
        # convert percent brightness to ha expected range
        return water_tank_lifted


class VeSyncHumidifierHighHumiditySensor(VeSyncSensorHA, BinarySensorEntity):
    """Representation of a VeSync Water Tank sensor."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def unique_id(self):
        """Return the ID of this device."""
        if isinstance(self.device.sub_device_no, int):
            return f"{self.device.cid}{str(self.device.sub_device_no)}_high_humidity_sensor"
        return f"{self.device.cid}_high_humidity_sensor"

    @property
    def name(self):
        """Name of sensor entity"""
        return self.device.device_name + " (high humidity)"

    @property
    def is_on(self):
        """Return the status of the sensor."""
        # get value from pyvesync library api,
        result = self.device.details["humidity_high"]
        try:
            # check for validity of brightness value received
            humidity_high = bool(result)
        except ValueError:
            # deal if any unexpected/non numeric value
            _LOGGER.debug(
                "VeSync - received unexpected 'humidity_high' value from pyvesync api: %s",
                result,
            )
            return False
        # convert percent brightness to ha expected range
        return humidity_high