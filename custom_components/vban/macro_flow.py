"""Config subentries for Macro Buttons style controls."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigSubentryFlow, SubentryFlowResult
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig

from .const import (
    CONF_COMMAND,
    CONF_COMMAND_OFF,
    CONF_COMMAND_ON,
    CONF_NAME,
    CONF_RELEASE,
)
from .script import ScriptError, parse_macro_script

_SCRIPT = TextSelector(TextSelectorConfig(multiline=True))


def _script_error(script: str) -> str | None:
    try:
        parse_macro_script(script)
    except ScriptError as err:
        reason = str(err)
        if reason == "empty":
            return "empty_script"
        if reason == "stream":
            return "invalid_stream"
        return "invalid_script"
    return None


class PushButtonSubentryFlow(ConfigSubentryFlow):
    """Add a push button that sends one script."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Create a push button."""
        return await self._async_form(user_input, reconfigure=False)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Edit a push button."""
        return await self._async_form(user_input, reconfigure=True)

    async def _async_form(
        self, user_input: dict[str, Any] | None, reconfigure: bool
    ) -> SubentryFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None and (error := _script_error(user_input[CONF_COMMAND])):
            errors["base"] = error
        elif user_input is not None:
            title = user_input[CONF_NAME]
            data = {
                CONF_COMMAND: user_input[CONF_COMMAND],
                CONF_RELEASE: bool(user_input.get(CONF_RELEASE, False)),
            }
            if reconfigure:
                return self.async_update_and_abort(
                    self._get_entry(),
                    self._get_reconfigure_subentry(),
                    title=title,
                    data=data,
                )
            return self.async_create_entry(title=title, data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_COMMAND): _SCRIPT,
                vol.Required(CONF_RELEASE, default=False): bool,
            }
        )
        if reconfigure:
            subentry = self._get_reconfigure_subentry()
            schema = self.add_suggested_values_to_schema(
                schema,
                {CONF_NAME: subentry.title, **subentry.data},
            )
        return self.async_show_form(
            step_id="reconfigure" if reconfigure else "user",
            data_schema=schema,
            errors=errors,
        )


class TwoPositionSubentryFlow(ConfigSubentryFlow):
    """Add a 2-position switch with separate on and off scripts."""

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Create a 2-position switch."""
        return await self._async_form(user_input, reconfigure=False)

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Edit a 2-position switch."""
        return await self._async_form(user_input, reconfigure=True)

    async def _async_form(
        self, user_input: dict[str, Any] | None, reconfigure: bool
    ) -> SubentryFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            for key in (CONF_COMMAND_ON, CONF_COMMAND_OFF):
                if error := _script_error(user_input[key]):
                    errors["base"] = error
                    break
        if user_input is not None and not errors:
            title = user_input[CONF_NAME]
            data = {
                CONF_COMMAND_ON: user_input[CONF_COMMAND_ON],
                CONF_COMMAND_OFF: user_input[CONF_COMMAND_OFF],
            }
            if reconfigure:
                return self.async_update_and_abort(
                    self._get_entry(),
                    self._get_reconfigure_subentry(),
                    title=title,
                    data=data,
                )
            return self.async_create_entry(title=title, data=data)

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_COMMAND_ON): _SCRIPT,
                vol.Required(CONF_COMMAND_OFF): _SCRIPT,
            }
        )
        if reconfigure:
            subentry = self._get_reconfigure_subentry()
            schema = self.add_suggested_values_to_schema(
                schema,
                {CONF_NAME: subentry.title, **subentry.data},
            )
        return self.async_show_form(
            step_id="reconfigure" if reconfigure else "user",
            data_schema=schema,
            errors=errors,
        )
