import shlex
import sys

from snaktui.web import build_command, build_parser


def test_web_command_runs_the_real_app():
    command = shlex.split(build_command())
    assert command[-2:] == ["-m", "snaktui"]
    assert command[0] == sys.executable


def test_web_defaults_to_loopback(monkeypatch):
    monkeypatch.delenv("SNAKTUI_WEB_HOST", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    args = build_parser().parse_args([])
    assert args.host == "127.0.0.1"
    assert args.port == 8000


def test_web_empty_port_falls_back(monkeypatch):
    monkeypatch.setenv("PORT", "")
    args = build_parser().parse_args([])
    assert args.port == 8000
