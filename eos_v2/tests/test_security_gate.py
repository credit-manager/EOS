import subprocess
import sys


def test_security_gate_passes_non_production_defaults():
    result = subprocess.run([sys.executable, "scripts/security_gate.py"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert "PASS" in result.stdout
