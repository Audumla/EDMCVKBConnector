"""Developer test runner for EDMCVKBConnector.

Usage:
  python scripts/run_plugin_dev.py --edmc-path "C:/Path/To/EDMC" --plugin-dir "C:/Path/To/EDMCVKBConnector"

This script configures Python to import EDMC's `config` module from a custom location
and runs `plugin_start3()` from the plugin's `load.py` for quick local testing.
It sends a single synthetic journal event and then calls `plugin_stop()`.
"""
import argparse
import os
import sys
import time


def main():
    parser = argparse.ArgumentParser(description="Run EDMCVKBConnector plugin for local testing")
    parser.add_argument("--edmc-path", help="Path to EDMC installation containing config.py", required=False)
    parser.add_argument("--plugin-dir", help="Path to plugin folder (contains load.py)", required=False)
    args = parser.parse_args()

    if args.edmc_path:
        edmc_path = os.path.abspath(args.edmc_path)
        if edmc_path not in sys.path:
            sys.path.insert(0, edmc_path)
        os.environ["EDMC_PATH"] = edmc_path

    plugin_dir = os.path.abspath(args.plugin_dir) if args.plugin_dir else os.getcwd()

    # Ensure plugin directory on sys.path for package imports
    package_root = os.path.join(plugin_dir, "src")
    if package_root not in sys.path:
        sys.path.insert(0, package_root)

    # Add plugin folder itself so load.py can be imported when running from source
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)

    # Import and start plugin
    try:
        import load

        print("Starting plugin via load.plugin_start3()")
        name = load.plugin_start3(plugin_dir)
        print(f"plugin_start3 returned: {name}")

        # Send a synthetic event for quick smoke test
        from load import journal_entry

        sample_event = {"event": "FSDJump", "StarSystem": "TestSystem"}
        journal_entry("TestCmdr", False, "TestSystem", None, sample_event, {})

        time.sleep(1)

    except Exception as e:
        print(f"Error running plugin: {e}")

    finally:
        try:
            load.plugin_stop()
            print("plugin_stop called")
        except Exception:
            pass


if __name__ == "__main__":
    main()
