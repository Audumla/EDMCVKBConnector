"""Run all tests via pytest.

This is a convenience wrapper.  Prefer running directly:
    python -m pytest -v
"""

import subprocess
import sys


def main():
    return subprocess.call([sys.executable, "-m", "pytest", "-v", "--tb=short"])


if __name__ == "__main__":
    sys.exit(main())
