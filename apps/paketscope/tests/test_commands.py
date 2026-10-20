import pytest

from paketscope import commands


def test_empty_command_is_rejected():
    with pytest.raises(ValueError, match="kosong"):
        commands.run_command([])


def test_command_unavailable_is_reported(monkeypatch):
    monkeypatch.setattr(commands.shutil, "which", lambda _name: None)
    with pytest.raises(commands.CommandUnavailable):
        commands.run_command(["not-a-real-system-command"])
