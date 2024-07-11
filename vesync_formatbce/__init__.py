"""VeSync integration."""
import logging
from typing import Dict, List

from pyvesync import VeSync
import voluptuous as vol

from homeassistant.config_entries import SOURCE_IMPORT
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send

from .common import CoordinatedVeSyncDevice, async_process_devices
from .const import (
    DOMAIN,
    SERVICE_UPDATE_DEVS,
    VS_DISCOVERY,
    VS_DISPATCHERS,
    VS_FANS,
    VS_HUMIDIFIERS,
    VS_LIGHTS,
    VS_MANAGER,
    VS_SWITCHES,
)

PLATFORMS = ["switch", "fan", "light", "humidifier", "sensor"]

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    vol.All(
        cv.deprecated(DOMAIN),
        {
            DOMAIN: vol.Schema(
                {
                    vol.Required(CONF_USERNAME): cv.string,
                    vol.Required(CONF_PASSWORD): cv.string,
                }
            )
        },
    ),
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass, config):
    """Set up the VeSync component."""
    conf = config.get(DOMAIN)

    if conf is None:
        return True

    if not hass.config_entries.async_entries(DOMAIN):
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data={
                    CONF_USERNAME: conf[CONF_USERNAME],
                    CONF_PASSWORD: conf[CONF_PASSWORD],
                },
            )
        )

    return True


async def async_setup_entry(hass, config_entry):
    """Set up Vesync as config entry."""
    username = config_entry.data[CONF_USERNAME]
    password = config_entry.data[CONF_PASSWORD]

    time_zone = str(hass.config.time_zone)

    manager = VeSync(username, password, time_zone)

    login = await hass.async_add_executor_job(manager.login)

    if not login:
        _LOGGER.error("Unable to login to the VeSync server")
        return False

    device_dict = await async_process_devices(hass, manager)

    hass.data[DOMAIN] = {}
    hass.data[DOMAIN][VS_MANAGER] = manager

    switches = hass.data[DOMAIN][VS_SWITCHES] = []
    fans = hass.data[DOMAIN][VS_FANS] = []
    humidifiers = hass.data[DOMAIN][VS_HUMIDIFIERS] = []
    lights = hass.data[DOMAIN][VS_LIGHTS] = []

    hass.data[DOMAIN][VS_DISPATCHERS] = []

    if device_dict[VS_SWITCHES]:
        switches.extend(device_dict[VS_SWITCHES])
        await hass.config_entries.async_forward_entry_setups(config_entry, ["switch"])

    if device_dict[VS_FANS]:
        fans.extend(device_dict[VS_FANS])
        await hass.config_entries.async_forward_entry_setups(config_entry, ["fan"])

    if device_dict[VS_HUMIDIFIERS]:
        humidifiers.extend(device_dict[VS_HUMIDIFIERS])
        await hass.config_entries.async_forward_entry_setups(config_entry, ["sensor", "humidifier"])

    if device_dict[VS_LIGHTS]:
        lights.extend(device_dict[VS_LIGHTS])
        await hass.config_entries.async_forward_entry_setups(config_entry, ["light"])

    async def async_new_device_discovery(service):
        """Discover if new devices should be added."""
        manager = hass.data[DOMAIN][VS_MANAGER]
        switches: List[CoordinatedVeSyncDevice] = hass.data[DOMAIN][VS_SWITCHES]
        fans: List[CoordinatedVeSyncDevice] = hass.data[DOMAIN][VS_FANS]
        humidifiers: List[CoordinatedVeSyncDevice] = hass.data[DOMAIN][VS_HUMIDIFIERS]
        lights: List[CoordinatedVeSyncDevice] = hass.data[DOMAIN][VS_LIGHTS]

        dev_dict = await async_process_devices(hass, manager)
        switch_devs = dev_dict.get(VS_SWITCHES, [])
        fan_devs = dev_dict.get(VS_FANS, [])
        humidifier_devs = dev_dict.get(VS_HUMIDIFIERS, [])
        light_devs = dev_dict.get(VS_LIGHTS, [])

        switch_set = set(switch_devs)
        new_switches = list(switch_set.difference(switches))
        if new_switches and switches:
            switches.extend(new_switches)
            async_dispatcher_send(hass, VS_DISCOVERY.format(VS_SWITCHES), new_switches)
            return
        if new_switches and not switches:
            switches.extend(new_switches)
            await hass.config_entries.async_forward_entry_setups(config_entry, ["switch"])

        fan_set = set(fan_devs)
        new_fans = list(fan_set.difference(fans))
        if new_fans and fans:
            fans.extend(new_fans)
            async_dispatcher_send(hass, VS_DISCOVERY.format(VS_FANS), new_fans)
            return
        if new_fans and not fans:
            fans.extend(new_fans)
            await hass.config_entries.async_forward_entry_setups(config_entry, ["fan"])

        humidifier_set = set(humidifier_devs)
        new_humidifiers = list(humidifier_set.difference(humidifiers))
        if new_humidifiers and humidifiers:
            humidifiers.extend(new_humidifiers)
            async_dispatcher_send(hass, VS_DISCOVERY.format(VS_HUMIDIFIERS), new_humidifiers)
            return
        if new_humidifiers and not humidifiers:
            humidifiers.extend(new_humidifiers)
            await hass.config_entries.async_forward_entry_setups(config_entry, ["sensor", "humidifier"])

        light_set = set(light_devs)
        new_lights = list(light_set.difference(lights))
        if new_lights and lights:
            lights.extend(new_lights)
            async_dispatcher_send(hass, VS_DISCOVERY.format(VS_LIGHTS), new_lights)
            return
        if new_lights and not lights:
            lights.extend(new_lights)
            await hass.config_entries.async_forward_entry_setups(config_entry, ["light"])

    hass.services.async_register(
        DOMAIN, SERVICE_UPDATE_DEVS, async_new_device_discovery
    )

    return True


async def async_unload_entry(hass, entry):
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
