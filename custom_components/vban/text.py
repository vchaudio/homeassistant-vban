"""Text platform for VBAN VoiceMeeter."""
from __future__ import annotations

import logging
from homeassistant.components.text import TextEntity
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import VBANConfigEntry, VBANUpdateCoordinator
from .const import DOMAIN
from .entity import VBANBaseEntity

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: VBANConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the VBAN text entities."""
    data = entry.runtime_data
    remote = data.remote
    coordinator = data.coordinator

    entities = []
    for strip in remote.strips:
        entities.append(VBANLabelText(coordinator, "strip", strip.index))
    for bus in remote.buses:
        entities.append(VBANLabelText(coordinator, "bus", bus.index))
    entities.append(VBANCommandText(coordinator))

    async_add_entities(entities)

class VBANLabelText(VBANBaseEntity, TextEntity):
    """Text entity for VBAN labels."""
    _attr_translation_key = "label"

    def __init__(self, coordinator: VBANUpdateCoordinator, kind: str, index: int) -> None:
        super().__init__(coordinator, kind, index)
        self._attr_unique_id = f"{self.host_id}_{kind}_{index}_label"
        self._attr_suggested_object_id = f"{kind}_{index + 1}_label"

    @property
    def native_value(self) -> str | None:
        return self.obj.label

    async def async_set_value(self, value: str) -> None:
        _LOGGER.info("Setting label for %s to %s", self.identifier, value)
        await self.obj.set_label(value)


class VBANCommandText(CoordinatorEntity[VBANUpdateCoordinator], TextEntity, RestoreEntity):
    """Local text box whose contents are sent by the Send command button."""

    _attr_translation_key = "command"
    _attr_icon = "mdi:console-line"
    _attr_has_entity_name = True
    _attr_native_max = 512

    def __init__(self, coordinator: VBANUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._value = ""
        self.remote = coordinator.remote
        data = self.remote.device.connected_application_data
        self.host_id = data.host_name if data and data.host_name else self.remote.device.address
        self._attr_unique_id = f"{self.host_id}_command"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, self.host_id)},
            name=f"VoiceMeeter ({self.host_id})",
            manufacturer="VB-Audio",
            model=self.remote.type.name if self.remote.type else "VoiceMeeter",
            sw_version=self.remote.version,
        )

    @property
    def available(self) -> bool:
        return self.remote.online and super().available

    @property
    def native_value(self) -> str:
        return self._value

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state and last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            self._value = last_state.state
            self.coordinator.custom_command = self._value

    async def async_set_value(self, value: str) -> None:
        self._value = value
        self.coordinator.custom_command = value
        self.async_write_ha_state()
