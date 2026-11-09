"""Runtime fixes for the aiovban package shipped with this integration.

aiovban models strip and bus state as ``enum.Flag``. Python 3.14 uses a strict
boundary, so a state bit the library does not name (VoiceMeeter sends
``0x40000000``) raises ``ValueError``. The RT worker then never marks the
device online, and every entity stays unavailable.
"""

from __future__ import annotations

import logging
from enum import KEEP

from aiovban.asyncio.voicemeeter.remote import VoicemeeterRemote
from aiovban.enums import State

_LOGGER = logging.getLogger(__name__)

_orig_apply_rt_packet_type1 = VoicemeeterRemote.apply_rt_packet_type1


def _apply_rt_packet_type1(self, body) -> None:
    """Keep Type 1 strip gain in decibels before Home Assistant is notified.

    aiovban divides ``dblevel`` by 100. VoiceMeeter already sends that float in
    dB. The stock method notifies callbacks with the wrong value first, so the
    gain slider jumps between the real level and level / 100.
    """
    callbacks = self._callbacks
    self._callbacks = []
    try:
        _orig_apply_rt_packet_type1(self, body)
        for index, strip_param in enumerate(body.strips):
            if index < len(self._all_strips):
                self._all_strips[index].gain = strip_param.dblevel
    finally:
        self._callbacks = callbacks

    for callback in self._callbacks:
        try:
            callback(self, body)
        except Exception as err:
            _LOGGER.error("Error in VoicemeeterRemote callback (Type 1): %s", err)


def apply() -> None:
    """Apply runtime fixes for the bundled aiovban package."""
    State._boundary_ = KEEP
    VoicemeeterRemote.apply_rt_packet_type1 = _apply_rt_packet_type1


apply()
