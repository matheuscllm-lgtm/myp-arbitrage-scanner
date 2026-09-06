"""The native CLI must work when Windows redirects stdout using cp1252."""
import os
from pathlib import Path
import subprocess
import sys


def test_cli_help_with_legacy_redirected_encoding():
    result = subprocess.run(
        [sys.executable, str(Path(__file__).with_name("myp_arbitrage_scanner.py")), "--help"],
        env=dict(os.environ, PYTHONIOENCODING="cp1252", PYTHONUTF8="0"),
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", errors="replace")
    help_text = result.stdout.decode("utf-8")
    assert "Pokémon" in help_text
    assert "−" in help_text
    assert "--resume" in help_text
