"""Parse and send Macro Buttons scripts over VBAN."""

from __future__ import annotations

import logging
import re

_LOGGER = logging.getLogger(__name__)

_CALL = re.compile(r"SendText\s*\(|BEGIN_SECTION\s*\(", re.IGNORECASE)
_END_SECTION = re.compile(r"END_SECTION", re.IGNORECASE)
_MAX_STREAM_NAME = 16


class ScriptError(ValueError):
    """A Macro Buttons script could not be parsed."""


def parse_macro_script(script: str) -> list[tuple[str, str]]:
    """Return (stream name, instruction) pairs from a Macro Buttons script.

    ``SendText("vban1", Strip(0).gain=-6;);`` becomes
    ``("vban1", "Strip(0).gain=-6;")``.

    ``BEGIN_SECTION("vban1") ... END_SECTION`` is accepted as well.
    A script with no SendText or BEGIN_SECTION is one instruction on the
    integration's configured command stream.
    """
    text = script.strip()
    if not text:
        raise ScriptError("empty")

    commands: list[tuple[str, str]] = []
    cursor = 0
    for match in _CALL.finditer(text):
        if match.start() < cursor:
            continue
        kind = "section" if text[match.start()].lower() == "b" else "sendtext"
        stream, instruction, cursor = _parse_call(text, match.end(), kind)
        if not stream or len(stream) > _MAX_STREAM_NAME:
            raise ScriptError("stream")
        if instruction:
            commands.append((stream, _terminate(instruction)))

    if _CALL.search(text):
        if not commands:
            raise ScriptError("invalid")
        return commands

    return [("", _terminate(text))]


def _terminate(instruction: str) -> str:
    instruction = instruction.strip()
    if instruction and not instruction.endswith(";"):
        instruction += ";"
    return instruction


def _parse_call(text: str, index: int, kind: str) -> tuple[str, str, int]:
    index = _skip(text, index)
    if index >= len(text) or text[index] not in "\"'":
        raise ScriptError("invalid")
    stream, index = _read_string(text, index)
    index = _skip(text, index)

    if kind == "section":
        if index >= len(text) or text[index] != ")":
            raise ScriptError("invalid")
        index += 1
        end = _END_SECTION.search(text, index)
        if end is None:
            raise ScriptError("invalid")
        return stream, text[index:end.start()], end.end()

    if index >= len(text) or text[index] != ",":
        raise ScriptError("invalid")
    instruction, index = _read_until_depth(text, index + 1, depth=1)
    return stream, instruction, index


def _read_string(text: str, index: int) -> tuple[str, int]:
    quote = text[index]
    index += 1
    chars: list[str] = []
    while index < len(text):
        char = text[index]
        if char == "\\" and index + 1 < len(text):
            chars.append(text[index + 1])
            index += 2
            continue
        if char == quote:
            return "".join(chars), index + 1
        chars.append(char)
        index += 1
    raise ScriptError("invalid")


def _read_until_depth(text: str, index: int, depth: int) -> tuple[str, int]:
    start = index
    while index < len(text):
        char = text[index]
        if char in "\"'":
            _, index = _read_string(text, index)
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return text[start:index], index + 1
        index += 1
    raise ScriptError("invalid")


def _skip(text: str, index: int) -> int:
    while index < len(text) and text[index] in " \t\r\n":
        index += 1
    return index


async def async_send_script(remote, script: str) -> None:
    """Send a Macro Buttons script to VoiceMeeter."""
    default_stream = remote.command_stream_name
    commands = parse_macro_script(script)
    original_stream = remote.command_stream_name
    try:
        for stream, instruction in commands:
            remote.command_stream_name = stream or default_stream
            _LOGGER.info(
                "VBAN text to %s on stream %s: %s",
                remote.device.address,
                remote.command_stream_name,
                instruction,
            )
            await remote.send_command(instruction)
    finally:
        remote.command_stream_name = original_stream
