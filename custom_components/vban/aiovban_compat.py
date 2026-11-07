"""Keep VoiceMeeter RT packets parseable on Python 3.14.

aiovban models strip and bus state as ``enum.Flag``. Python 3.14 uses a strict
boundary, so a state bit the library does not name (VoiceMeeter sends
``0x40000000``) raises ``ValueError``. The RT worker then never marks the
device online, and every entity stays unavailable.
"""

from __future__ import annotations

from enum import KEEP

from aiovban.enums import State


def apply() -> None:
    """Allow unnamed VoiceMeeter state bits through aiovban's Flag."""
    State._boundary_ = KEEP


apply()
