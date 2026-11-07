"""Button platform for VBAN VoiceMeeter."""
from __future__ import annotations

import logging
from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import VBANConfigEntry, VBANUpdateCoordinator
from .const import CONF_COMMAND, DOMAIN, SUBENTRY_PUSH
from .entity import async_remove_stale_script_entities
from .script import async_send_script

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(
    hass: HomeAssistant,
    entry: VBANConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the VBAN buttons."""
    data = entry.runtime_data
    coordinator = data.coordinator

    async_add_entities([
        VBANRestartButton(coordinator),
        VBANShowWindowButton(coordinator),
    ])
    buttons: list[VBANScriptButton] = []
    live_ids: set[str] = set()
    for subentry in entry.subentries.values():
        if subentry.subentry_type != SUBENTRY_PUSH:
            continue
        live_ids.add(subentry.subentry_id)
        buttons.append(
            VBANScriptButton(
                coordinator,
                subentry.subentry_id,
                subentry.title,
                subentry.data[CONF_COMMAND],
            )
        )
    async_remove_stale_script_entities(hass, entry.entry_id, "button", "push_", live_ids)
    if buttons:
        async_add_entities(buttons)

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


class VBANScriptButton(VBANBaseButton):
    """Push button that sends a Macro Buttons script."""

    _attr_icon = "mdi:gesture-tap-button"

    def __init__(
        self,
        coordinator: VBANUpdateCoordinator,
        subentry_id: str,
        name: str,
        script: str,
    ) -> None:
        super().__init__(coordinator)
        self._script = script
        self._attr_name = name
        self._attr_unique_id = f"push_{subentry_id}"

    async def async_press(self) -> None:
        await async_send_script(self.remote, self._script)
