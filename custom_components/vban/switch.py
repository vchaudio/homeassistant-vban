"""Switch platform for VBAN VoiceMeeter."""
from __future__ import annotations

import asyncio
import logging
from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_ON
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import VBANConfigEntry, VBANUpdateCoordinator
from .const import (
    CONF_COMMAND,
    CONF_COMMAND_OFF,
    CONF_COMMAND_ON,
    DOMAIN,
    SUBENTRY_PUSH,
    SUBENTRY_TWO_POSITION,
)
from .script import PUSH_RELEASE_SECONDS, async_send_script, release_script
from .entity import VBANBaseEntity, async_remove_stale_script_entities

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: VBANConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the VBAN switches."""
    data = entry.runtime_data
    remote = data.remote
    coordinator = data.coordinator

    entities = []
    for strip in remote.strips:
        entities.append(VBANMuteSwitch(coordinator, "strip", strip.index))
        entities.append(VBANSoloSwitch(coordinator, strip.index))
        entities.append(VBANEQSwitch(coordinator, "strip", strip.index))
        entities.append(VBANMCSwitch(coordinator, strip.index))
        
        # Routing: A1-A5, B1-B3
        for i in range(1, 6):
            bus_id = f"A{i}"
            if hasattr(strip, bus_id.lower()):
                entities.append(VBANRoutingSwitch(coordinator, strip.index, bus_id))
        for i in range(1, 4):
            bus_id = f"B{i}"
            if hasattr(strip, bus_id.lower()):
                entities.append(VBANRoutingSwitch(coordinator, strip.index, bus_id))
            
    for bus in remote.buses:
        entities.append(VBANMuteSwitch(coordinator, "bus", bus.index))
        entities.append(VBANEQSwitch(coordinator, "bus", bus.index))

    async_add_entities(entities)
    switches: list[VBANScriptSwitch] = []
    live_ids: set[str] = set()
    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_TWO_POSITION:
            continue
        live_ids.add(subentry.subentry_id)
        switches.append(
            VBANScriptSwitch(
                coordinator,
                subentry.subentry_id,
                subentry.title,
                subentry.data[CONF_COMMAND_ON],
                subentry.data[CONF_COMMAND_OFF],
            )
        )
    async_remove_stale_script_entities(
        hass, entry.entry_id, "switch", "two_position_", live_ids
    )
    if switches:
        async_add_entities(switches)

    pushes: list[VBANPushSwitch] = []
    live_push_ids: set[str] = set()
    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_PUSH:
            continue
        live_push_ids.add(subentry.subentry_id)
        pushes.append(
            VBANPushSwitch(
                coordinator,
                subentry.subentry_id,
                subentry.title,
                subentry.data[CONF_COMMAND],
            )
        )
    async_remove_stale_script_entities(hass, entry.entry_id, "switch", "push_", live_push_ids)
    if pushes:
        async_add_entities(pushes)

class VBANMuteSwitch(VBANBaseEntity, SwitchEntity):
    """Mute switch for VBAN."""
    _attr_translation_key = "mute"

    def __init__(self, coordinator: VBANUpdateCoordinator, kind: str, index: int) -> None:
        super().__init__(coordinator, kind, index)
        self._attr_unique_id = f"{self.host_id}_{kind}_{index}_mute"
        self._attr_suggested_object_id = f"{self.identifier}_mute"

    @property
    def is_on(self):
        return self.obj.mute

    async def async_turn_on(self, **kwargs):
        await self.obj.set_mute(True)

    async def async_turn_off(self, **kwargs):
        await self.obj.set_mute(False)

class VBANSoloSwitch(VBANBaseEntity, SwitchEntity):
    """Solo switch for VBAN."""
    _attr_translation_key = "solo"

    def __init__(self, coordinator: VBANUpdateCoordinator, index: int) -> None:
        super().__init__(coordinator, "strip", index)
        self._attr_unique_id = f"{self.host_id}_strip_{index}_solo"
        self._attr_suggested_object_id = f"strip_{index + 1}_solo"

    @property
    def is_on(self):
        return self.obj.solo

    async def async_turn_on(self, **kwargs):
        await self.obj.set_solo(True)

    async def async_turn_off(self, **kwargs):
        await self.obj.set_solo(False)

class VBANEQSwitch(VBANBaseEntity, SwitchEntity):
    """EQ switch for VBAN."""
    _attr_translation_key = "eq"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: VBANUpdateCoordinator, kind: str, index: int) -> None:
        super().__init__(coordinator, kind, index)
        self._attr_unique_id = f"{self.host_id}_{kind}_{index}_eq"
        self._attr_suggested_object_id = f"{self.identifier}_eq"

    @property
    def is_on(self):
        return self.obj.eq

    async def async_turn_on(self, **kwargs):
        await self.obj.set_eq(True)

    async def async_turn_off(self, **kwargs):
        await self.obj.set_eq(False)

class VBANMCSwitch(VBANBaseEntity, SwitchEntity):
    """MC (Multi-Channel) switch for VBAN."""
    _attr_translation_key = "mc"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator: VBANUpdateCoordinator, index: int) -> None:
        super().__init__(coordinator, "strip", index)
        self._attr_unique_id = f"{self.host_id}_strip_{index}_mc"
        self._attr_suggested_object_id = f"strip_{index + 1}_mc"

    @property
    def is_on(self):
        return self.obj.mc

    async def async_turn_on(self, **kwargs):
        await self.obj.set_mc(True)

    async def async_turn_off(self, **kwargs):
        await self.obj.set_mc(False)

class VBANRoutingSwitch(VBANBaseEntity, SwitchEntity):
    """Routing switch for VBAN."""
    _attr_translation_key = "bus_routing"

    def __init__(self, coordinator: VBANUpdateCoordinator, index: int, bus_id: str) -> None:
        super().__init__(coordinator, "strip", index)
        self.bus_id = bus_id.lower()
        self._attr_unique_id = f"{self.host_id}_strip_{index}_route_{self.bus_id}"
        self._attr_suggested_object_id = f"strip_{index + 1}_route_{self.bus_id}"
        self._attr_translation_placeholders = {"bus": bus_id.upper()}

    @property
    def is_on(self):
        return getattr(self.obj, self.bus_id)

    async def async_turn_on(self, **kwargs):
        _LOGGER.info("Turning ON routing to %s for %s", self.bus_id.upper(), self.identifier)
        await self.obj.set_bus_routing(self.bus_id, True)

    async def async_turn_off(self, **kwargs):
        _LOGGER.info("Turning OFF routing to %s for %s", self.bus_id.upper(), self.identifier)
        await self.obj.set_bus_routing(self.bus_id, False)


class VBANScriptSwitch(CoordinatorEntity[VBANUpdateCoordinator], SwitchEntity, RestoreEntity):
    """2-position control. On and off each send their own script."""

    _attr_icon = "mdi:toggle-switch"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VBANUpdateCoordinator,
        subentry_id: str,
        name: str,
        command_on: str,
        command_off: str,
    ) -> None:
        super().__init__(coordinator)
        self._command_on = command_on
        self._command_off = command_off
        self._is_on = False
        self.remote = coordinator.remote
        host_id = coordinator.host
        self._attr_name = name
        self._attr_unique_id = f"two_position_{subentry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, host_id)},
            name=f"VoiceMeeter ({host_id})",
            manufacturer="VB-Audio",
            model=self.remote.type.name if self.remote.type else "VoiceMeeter",
            sw_version=self.remote.version,
        )

    @property
    def available(self) -> bool:
        return self.remote.online and super().available

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is not None:
            self._is_on = last_state.state == STATE_ON

    async def async_turn_on(self, **kwargs) -> None:
        await async_send_script(self.remote, self._command_on)
        self._is_on = True
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        await async_send_script(self.remote, self._command_off)
        self._is_on = False
        self.async_write_ha_state()


class VBANPushSwitch(CoordinatorEntity[VBANUpdateCoordinator], SwitchEntity):
    """Push control. It turns on, sends the script, then returns to off."""

    _attr_icon = "mdi:gesture-tap-button"
    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: VBANUpdateCoordinator,
        subentry_id: str,
        name: str,
        script: str,
    ) -> None:
        super().__init__(coordinator)
        self._script = script
        self._is_on = False
        self._pulsing = False
        self.remote = coordinator.remote
        host_id = coordinator.host
        self._attr_name = name
        self._attr_unique_id = f"push_{subentry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, host_id)},
            name=f"VoiceMeeter ({host_id})",
            manufacturer="VB-Audio",
            model=self.remote.type.name if self.remote.type else "VoiceMeeter",
            sw_version=self.remote.version,
        )

    @property
    def available(self) -> bool:
        return self.remote.online and super().available

    @property
    def is_on(self) -> bool:
        return self._is_on

    async def async_turn_on(self, **kwargs) -> None:
        if self._pulsing:
            return
        self._pulsing = True
        self._is_on = True
        self.async_write_ha_state()
        try:
            await async_send_script(self.remote, self._script)
            await asyncio.sleep(PUSH_RELEASE_SECONDS)
            if (release := release_script(self._script)) is not None:
                await async_send_script(self.remote, release)
        finally:
            self._is_on = False
            self._pulsing = False
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        if (release := release_script(self._script)) is not None:
            await async_send_script(self.remote, release)
        self._is_on = False
        self.async_write_ha_state()
