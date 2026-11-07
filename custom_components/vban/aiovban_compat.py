"""Runtime fixes for the aiovban package shipped with this integration.

aiovban models strip and bus state as ``enum.Flag``. Python 3.14 uses a strict
boundary, so a state bit the library does not name (VoiceMeeter sends
``0x40000000``) raises ``ValueError``. The RT worker then never marks the
device online, and every entity stays unavailable.
"""

from __future__ import annotations

from enum import KEEP

from aiovban.asyncio.voicemeeter.remote import VoicemeeterRemote
from aiovban.enums import State

_orig_apply_rt_packet_type1 = VoicemeeterRemote.apply_rt_packet_type1


def _apply_rt_packet_type1(self, body) -> None:
    """Keep Type 1 strip gain in decibels.

    aiovban divides ``dblevel`` by 100. VoiceMeeter already sends that float in
    dB, so a mute, solo, or fader change briefly publishes gain / 100.
    """
    _orig_apply_rt_packet_type1(self, body)
    for index, strip_param in enumerate(body.strips):
        if index < len(self._all_strips):
            self._all_strips[index].gain = strip_param.dblevel


def apply() -> None:
    """Apply runtime fixes for the bundled aiovban package."""
    State._boundary_ = KEEP
    VoicemeeterRemote.apply_rt_packet_type1 = _apply_rt_packet_type1


apply()
