"""Constants for the VBAN VoiceMeeter integration."""

DOMAIN = "vban"

CONF_HOST = "host"

CONF_PORT = "port"

CONF_COMMAND_STREAM = "command_stream"
CONF_MEDIA_STREAM = "media_stream"
CONF_CHAT_STREAM = "chat_stream"
CONF_MACRO_BUTTONS = "macro_buttons"

MAX_MACRO_BUTTON = 79

DEFAULT_PORT = 6980

DEFAULT_COMMAND_STREAM = "Command1"
DEFAULT_MEDIA_STREAM = "Stream1"
DEFAULT_CHAT_STREAM = "VBAN Chat"


def parse_macro_buttons(value: str | None) -> list[int]:
    """Parse a comma-separated list of macro button indexes."""
    if not value or not value.strip():
        return []

    indexes: list[int] = []
    for part in value.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        index = int(part)
        if index < 0 or index > MAX_MACRO_BUTTON:
            raise ValueError(index)
        if index not in indexes:
            indexes.append(index)
    return indexes


def format_vban_command(command: str) -> str:
    """Return a VoiceMeeter instruction terminated with a semicolon."""
    command = command.strip()
    if command and not command.endswith(";"):
        command += ";"
    return command


def macro_button_command(index: int, pressed: bool) -> str:
    """Build the VBAN text instruction for one macro button."""
    state = 1 if pressed else 0
    return f"Command.Button[{index}].State={state};"
