"""Button platform for VBAN VoiceMeeter."""
from __future__ import annotations

import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import VBANConfigEntry, VBANUpdateCoordinator
from .const import (
    CONF_MACRO_BUTTONS,
    DOMAIN,
    format_vban_command,
    macro_button_command,
    parse_macro_buttons,
)

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: VBANConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the VBAN buttons."""
    data = entry.runtime_data
    coordinator = data.coordinator

    entities: list[ButtonEntity] = [
        VBANRestartButton(coordinator),
        VBANShowWindowButton(coordinator),
        VBANSendCommandButton(coordinator),
    ]
    configured = entry.options.get(
        CONF_MACRO_BUTTONS, entry.data.get(CONF_MACRO_BUTTONS, "")
    )
    for index in parse_macro_buttons(configured):
        entities.append(VBANMacroButton(coordinator, index))

    async_add_entities(entities)

class VBANBaseButton(CoordinatorEntity[VBANUpdateCoordinator], ButtonEntity):
    """Base class for VBAN buttons."""
    _attr_has_entity_name = True

    def __init__(self, coordinator: VBANUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self.remote = coordinator.remote
        
        # Determine stable host identifier (host_name > IP)
        data = self.remote.device.connected_application_data
        self.host_id = data.host_name if data and data.host_name else self.remote.device.address

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

class VBANRestartButton(VBANBaseButton):
    """Button to restart VoiceMeeter audio engine."""
    _attr_translation_key = "restart_engine"
    _attr_icon = "mdi:restart"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: VBANUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.host_id}_restart_engine"

    async def async_press(self) -> None:
        _LOGGER.info("Restarting VoiceMeeter audio engine for %s", self.host_id)
        await self.remote.restart()

class VBANShowWindowButton(VBANBaseButton):
    """Button to show VoiceMeeter window."""
    _attr_translation_key = "show_window"
    _attr_icon = "mdi:window-maximize"
    _attr_entity_registry_enabled_default = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: VBANUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.host_id}_show_window"

    async def async_press(self) -> None:
        _LOGGER.info("Showing VoiceMeeter window for %s", self.host_id)
        await self.remote.show()


class VBANMacroButton(VBANBaseButton):
    """Push a VoiceMeeter macro button."""

    _attr_translation_key = "macro_button"
    _attr_icon = "mdi:gesture-tap-button"

    def __init__(self, coordinator: VBANUpdateCoordinator, index: int) -> None:
        super().__init__(coordinator)
        self._index = index
        self._attr_translation_placeholders = {"index": str(index)}
        self._attr_unique_id = f"{self.host_id}_macro_button_{index}"

    async def async_press(self) -> None:
        command = macro_button_command(self._index, True)
        _LOGGER.info("Sending macro button command %s", command)
        await self.remote.send_command(command)


class VBANSendCommandButton(VBANBaseButton):
    """Send the text stored in the command entity."""

    _attr_translation_key = "send_command"
    _attr_icon = "mdi:send"

    def __init__(self, coordinator: VBANUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{self.host_id}_send_command"

    async def async_press(self) -> None:
        command = format_vban_command(self.coordinator.custom_command)
        if not command:
            _LOGGER.warning("VBAN command text is empty")
            return
        _LOGGER.info("Sending custom VBAN command %s", command)
        await self.remote.send_command(command)
