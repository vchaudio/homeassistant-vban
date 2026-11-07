"""Tests for Macro Buttons script parsing."""

from custom_components.vban.script import ScriptError, parse_macro_script
import pytest


def test_sendtext_example() -> None:
    """The full Macro Buttons line keeps the stream and the instruction."""
    assert parse_macro_script('SendText("vban1", Strip(0).gain=-6;);') == [
        ("vban1", "Strip(0).gain=-6;")
    ]


def test_several_sendtext_calls() -> None:
    """Each SendText call is sent separately, in order."""
    script = """
    SendText("vban1", Strip(0).Mute=1;);
    SendText('vban1', Strip(1).A1=0; Strip(1).A2=1;);
    """
    assert parse_macro_script(script) == [
        ("vban1", "Strip(0).Mute=1;"),
        ("vban1", "Strip(1).A1=0; Strip(1).A2=1;"),
    ]


def test_begin_section() -> None:
    """BEGIN_SECTION blocks are the other Macro Buttons stream syntax."""
    script = """
    BEGIN_SECTION("vban1")
    Strip(0).Mute=1;
    END_SECTION
    """
    assert parse_macro_script(script) == [("vban1", "Strip(0).Mute=1;")]


def test_plain_instruction_uses_configured_stream() -> None:
    """A script without SendText stays one instruction."""
    assert parse_macro_script("Strip(0).gain=-6;") == [("", "Strip(0).gain=-6;")]


def test_broken_sendtext_is_rejected() -> None:
    """An opened SendText call must contain a stream and an instruction."""
    with pytest.raises(ScriptError):
        parse_macro_script('SendText("vban1"')
