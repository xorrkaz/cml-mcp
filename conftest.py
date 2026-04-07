"""Root conftest for packaging/mcp_server.

Loaded before tests/conftest.py; sets env var defaults so that
cml_mcp.settings can be imported at module level without error.
"""

from __future__ import annotations

import argparse
import os
import sys


def _arg_value(option: str, argv: list[str], default: str) -> str:
    prefixed = f"{option}="
    for idx, arg in enumerate(argv):
        if arg.startswith(prefixed):
            return arg[len(prefixed) :]
        if arg == option and idx + 1 < len(argv):
            return argv[idx + 1]
    return default


def _has_arg(option: str, argv: list[str]) -> bool:
    return any(a == option or a.startswith(f"{option}=") for a in argv)


def _bootstrap_mcp_test_env_from_argv(argv: list[str]) -> None:
    """Set env vars needed by MCP tests from pytest CLI args."""
    os.environ.setdefault("CML_USERNAME", _arg_value("--controller-username", argv, "cml2"))
    os.environ.setdefault("CML_PASSWORD", _arg_value("--controller-password", argv, "cml2cml2"))
    os.environ.setdefault("CML_URL", _arg_value("--controller-url", argv, "https://localhost"))

    if "--use-mcp-mocks" in argv:
        os.environ["USE_MOCKS"] = "true"
    elif _has_arg("--controller-url", argv):
        os.environ.setdefault("USE_MOCKS", "false")
    else:
        os.environ.setdefault("USE_MOCKS", "true")


_bootstrap_mcp_test_env_from_argv(sys.argv[1:])


def pytest_addoption(parser):
    group = parser.getgroup("cml", "CML test options")
    group.addoption(
        "--use-mcp-mocks",
        action="store_true",
        default=False,
        help="Run MCP tests in mock mode",
    )
    for opt, default, help_text in (
        ("--controller-url", None, "URL of the CML controller"),
        ("--controller-username", "cml2", "CML controller username"),
        ("--controller-password", "cml2cml2", "CML controller password"),
    ):
        try:
            group.addoption(opt, default=default, help=help_text)
        except argparse.ArgumentError:
            pass
