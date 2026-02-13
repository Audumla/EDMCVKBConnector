"""
Real VKB Server Integration Tests

Tests against actual VKB hardware via VKB-Link TCP/IP server.
These tests are OPTIONAL and require VKB hardware + VKB-Link running.

Configuration:
  Environment variables (or create .env file):
    TEST_VKB_HOST - VKB server host (default: 127.0.0.1)
    TEST_VKB_PORT - VKB server port (default: 50995)
    TEST_VKB_ENABLED - Set to "1" to enable real server tests (default: 0)

Usage:
  pytest test_real_vkb_server.py -v                    # Run if configured
  TEST_VKB_ENABLED=1 pytest test_real_vkb_server.py   # Force run
  pytest test_real_vkb_server.py -v -k "not real"     # Skip real tests
"""

import functools
import json
import sys
import os
import time
import socket
from pathlib import Path
from contextlib import contextmanager

# Load .env file if it exists
def load_env_file():
    """Load environment variables from .env file."""
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        os.environ.setdefault(key.strip(), value.strip())

load_env_file()

from edmcruleengine.config import DEFAULTS
from edmcruleengine.vkb_client import VKBClient
from edmcruleengine.event_handler import EventHandler
from edmcruleengine.rules_engine import FLAGS, FLAGS2, GUI_FOCUS


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

TEST_VKB_HOST = os.environ.get("TEST_VKB_HOST", "127.0.0.1")
TEST_VKB_PORT = int(os.environ.get("TEST_VKB_PORT", 50995))
TEST_VKB_ENABLED = os.environ.get("TEST_VKB_ENABLED", "0") == "1"

FIXTURES_DIR = Path(__file__).parent / "fixtures"
RULES_FILE = FIXTURES_DIR / "rules_comprehensive.json"
NOTIFICATIONS_FILE = FIXTURES_DIR / "edmc_notifications.json"

# Delay between VKB sends so hardware visually updates
STEP_DELAY = 0.20  # 200 ms


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def check_server_available(host=TEST_VKB_HOST, port=TEST_VKB_PORT) -> bool:
    """Check if VKB server is accessible."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False


class RealServerConfig:
    """Config stub that lets us override rules_path for real-hardware tests."""

    def __init__(self, **overrides):
        self._values = dict(DEFAULTS)
        self._values.update(overrides)

    def get(self, key, default=None):
        return self._values.get(key, default)


def skip_if_no_real_server(func):
    """Decorator to skip test if real VKB server not available."""
    @functools.wraps(func)
    def wrapper():
        if not TEST_VKB_ENABLED:
            print(f"\nSKIP: Real VKB server tests disabled")
            print(f"      To enable: set TEST_VKB_ENABLED=1")
            return

        if not check_server_available():
            print(f"\nSKIP: VKB server not available at {TEST_VKB_HOST}:{TEST_VKB_PORT}")
            print(f"      Start VKB-Link and try again")
            return

        # Small gap after the availability probe so VKB-Link can accept
        # the next connection cleanly.
        time.sleep(0.3)

        print(f"\nRUNNING: Real VKB server test at {TEST_VKB_HOST}:{TEST_VKB_PORT}")
        return func()

    return wrapper


def _make_handler_with_rules(rules_path: Path = RULES_FILE) -> EventHandler:
    """Create an EventHandler wired to the real VKB server with rules loaded."""
    config = RealServerConfig(
        rules_path=str(rules_path),
        vkb_host=TEST_VKB_HOST,
        vkb_port=TEST_VKB_PORT,
    )
    handler = EventHandler(config, plugin_dir=str(rules_path.parent))
    # Override host/port on the already-created client
    handler.vkb_client.host = TEST_VKB_HOST
    handler.vkb_client.port = TEST_VKB_PORT
    return handler


def _load_notifications() -> dict:
    """Load the edmc_notifications.json fixture."""
    with NOTIFICATIONS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Basic connection tests
# ---------------------------------------------------------------------------

@skip_if_no_real_server
def test_real_server_connection():
    """Test connection to actual VKB hardware."""
    print(f"Test: Connect to real VKB server at {TEST_VKB_HOST}:{TEST_VKB_PORT}")

    client = VKBClient(
        host=TEST_VKB_HOST,
        port=TEST_VKB_PORT,
        initial_retry_interval=1,
        initial_retry_duration=5,
        fallback_retry_interval=1,
        socket_timeout=5,
    )

    try:
        success = client.connect()
        assert success, f"Failed to connect to {TEST_VKB_HOST}:{TEST_VKB_PORT}"
        assert client.connected, "Client reports not connected"
        print(f"  [OK] Connected to {TEST_VKB_HOST}:{TEST_VKB_PORT}")
        # Hold connection for 1 second so VKB-Link TCP icon can be confirmed
        time.sleep(1.0)
        print(f"  [OK] Held connection for 1 second")
    finally:
        client.disconnect()
        time.sleep(0.3)  # let VKB-Link register the disconnect
        assert not client.connected, "Client should be disconnected"
        print(f"  [OK] Disconnected cleanly")


@skip_if_no_real_server
def test_real_server_send_shift_state():
    """Send shift state to real VKB hardware."""
    print("Test: Send shift state to real VKB hardware")

    client = VKBClient(
        host=TEST_VKB_HOST,
        port=TEST_VKB_PORT,
        socket_timeout=5,
    )

    try:
        assert client.connect(), "Failed to connect"
        time.sleep(STEP_DELAY)

        for shift_val in (1, 2, 0):
            success = client.send_event("VKBShiftBitmap", {"shift": shift_val, "subshift": 0})
            assert success, f"Failed to send shift={shift_val}"
            print(f"  [OK] Sent shift={shift_val}")
            time.sleep(STEP_DELAY)
    finally:
        client.send_event("VKBShiftBitmap", {"shift": 0, "subshift": 0})
        client.disconnect()


@skip_if_no_real_server
def test_real_server_multiple_shifts():
    """Test all shift/subshift value combinations on real hardware."""
    print("Test: Send all shift value combinations to hardware")

    client = VKBClient(
        host=TEST_VKB_HOST,
        port=TEST_VKB_PORT,
        socket_timeout=5,
    )

    try:
        assert client.connect(), "Failed to connect"
        time.sleep(STEP_DELAY)
        messages_sent = 0
        for shift in range(3):  # Shift 0-2 only
            for subshift in range(8):  # Subshift byte: bits 0-6
                success = client.send_event(
                    "VKBShiftBitmap",
                    {"shift": shift, "subshift": subshift},
                )
                if success:
                    messages_sent += 1
                    print(f"  [OK] Shift={shift}, SubShift={subshift}")
                    time.sleep(STEP_DELAY)

        print(f"  [OK] Sent {messages_sent} shift combinations")
        assert messages_sent > 0, "No messages sent successfully"
    finally:
        client.send_event("VKBShiftBitmap", {"shift": 0, "subshift": 0})
        client.disconnect()


# ---------------------------------------------------------------------------
# Roll through every individual shift flag
# ---------------------------------------------------------------------------

@skip_if_no_real_server
def test_real_server_roll_shift_flags():
    """Roll through each valid Shift and Subshift bit with 200ms pause.

    Shift: 3 codes (Shift0-2) -> bits 0-2 of shift byte
    Subshift: 7 codes (Subshift1-7) -> bits 0-6 of subshift byte
    """
    print("Test: Roll through valid shift/subshift flags")

    client = VKBClient(
        host=TEST_VKB_HOST,
        port=TEST_VKB_PORT,
        socket_timeout=5,
    )

    try:
        assert client.connect(), "Failed to connect"
        time.sleep(STEP_DELAY)

        # Roll shift bits (0-2)
        print("  -- Shift bits (Shift0-Shift2) --")
        for bit in range(3):
            shift_val = 1 << bit
            success = client.send_event("VKBShiftBitmap", {"shift": shift_val, "subshift": 0})
            assert success, f"Failed to send Shift bit {bit} (value={shift_val})"
            print(f"  [OK] Shift{bit}  -> shift=0x{shift_val:02X} ({shift_val})")
            time.sleep(STEP_DELAY)

        # Clear
        client.send_event("VKBShiftBitmap", {"shift": 0, "subshift": 0})
        time.sleep(STEP_DELAY)

        # Roll subshift bits (Subshift1-7 -> bits 0-6)
        print("  -- Subshift bits (Subshift1-Subshift7 -> bits 0-6) --")
        for code in range(1, 8):  # Subshift1 through Subshift7
            bit_pos = code - 1
            subshift_val = 1 << bit_pos
            success = client.send_event("VKBShiftBitmap", {"shift": 0, "subshift": subshift_val})
            assert success, f"Failed to send Subshift{code} (bit {bit_pos}, value={subshift_val})"
            print(f"  [OK] Subshift{code} -> bit {bit_pos} -> subshift=0x{subshift_val:02X} ({subshift_val})")
            time.sleep(STEP_DELAY)

        print("  [OK] All 10 valid flag positions sent (3 shift + 7 subshift)")
    finally:
        client.send_event("VKBShiftBitmap", {"shift": 0, "subshift": 0})
        client.disconnect()


@skip_if_no_real_server
def test_real_server_roll_cumulative_flags():
    """Cumulatively add each shift bit then subshift bit.

    Shift: build up bits 0-2 (0x01, 0x03, 0x07) then strip back.
    Subshift: build up bits 0-6 (Subshift1-7) then strip back.
    """
    print("Test: Cumulative flag build-up (Shift0-2, then Subshift1-7)")

    client = VKBClient(
        host=TEST_VKB_HOST,
        port=TEST_VKB_PORT,
        socket_timeout=5,
    )

    try:
        assert client.connect(), "Failed to connect"
        time.sleep(STEP_DELAY)

        # Build up shift bits 0-2
        print("  -- Shift build-up --")
        bitmap = 0
        for bit in range(3):
            bitmap |= (1 << bit)
            success = client.send_event("VKBShiftBitmap", {"shift": bitmap, "subshift": 0})
            assert success, f"Failed to send cumulative shift 0x{bitmap:02X}"
            print(f"  [OK] +Shift{bit}  -> shift=0x{bitmap:02X} (0b{bitmap:08b})")
            time.sleep(STEP_DELAY)

        # Strip shift bits
        print("  -- Shift strip --")
        for bit in range(3):
            bitmap &= ~(1 << bit)
            success = client.send_event("VKBShiftBitmap", {"shift": bitmap, "subshift": 0})
            assert success, f"Failed to send stripped shift 0x{bitmap:02X}"
            print(f"  [OK] -Shift{bit}  -> shift=0x{bitmap:02X} (0b{bitmap:08b})")
            time.sleep(STEP_DELAY)

        assert bitmap == 0

        # Build up subshift bits 0-6 (Subshift1-7)
        print("  -- Subshift build-up (Subshift1-7 -> bits 0-6) --")
        sub_bitmap = 0
        for code in range(1, 8):
            bit_pos = code - 1
            sub_bitmap |= (1 << bit_pos)
            success = client.send_event("VKBShiftBitmap", {"shift": 0, "subshift": sub_bitmap})
            assert success, f"Failed to send cumulative subshift 0x{sub_bitmap:02X}"
            print(f"  [OK] +Subshift{code} -> subshift=0x{sub_bitmap:02X} (0b{sub_bitmap:08b})")
            time.sleep(STEP_DELAY)

        # Strip subshift bits
        print("  -- Subshift strip --")
        for code in range(1, 8):
            bit_pos = code - 1
            sub_bitmap &= ~(1 << bit_pos)
            success = client.send_event("VKBShiftBitmap", {"shift": 0, "subshift": sub_bitmap})
            assert success, f"Failed to send stripped subshift 0x{sub_bitmap:02X}"
            print(f"  [OK] -Subshift{code} -> subshift=0x{sub_bitmap:02X} (0b{sub_bitmap:08b})")
            time.sleep(STEP_DELAY)

        assert sub_bitmap == 0
        print("  [OK] Cumulative roll complete")
    finally:
        client.send_event("VKBShiftBitmap", {"shift": 0, "subshift": 0})
        client.disconnect()


# ---------------------------------------------------------------------------
# EventHandler tests (no rules / with rules)
# ---------------------------------------------------------------------------

@skip_if_no_real_server
def test_real_server_event_handler():
    """Test EventHandler with real VKB hardware (no rules loaded)."""
    print("Test: EventHandler with real VKB hardware (no rules)")

    config = RealServerConfig()
    handler = EventHandler(config)
    handler.vkb_client.host = TEST_VKB_HOST
    handler.vkb_client.port = TEST_VKB_PORT

    try:
        success = handler.connect()
        assert success, "EventHandler failed to connect"
        time.sleep(STEP_DELAY)

        # Without rules, events won't send anything to VKB — which is correct.
        # Session events (LoadGame) trigger a shift reset (shift=0, subshift=0).
        handler.handle_event(
            "LoadGame",
            {"event": "LoadGame", "Commander": "TestCmdr", "GameMode": "Open"},
            source="journal",
            cmdr="TestCmdr",
            is_beta=False,
        )
        time.sleep(STEP_DELAY)
        print("  [OK] LoadGame session-reset sent (shift=0)")

    finally:
        handler.disconnect()


@skip_if_no_real_server
def test_real_server_rules_dashboard_flags():
    """Send dashboard Status events through the rule engine to real VKB.

    Uses rules_comprehensive.json which maps:
      - FlagsHardpointsDeployed -> Shift1
      - GuiFocusGalaxyMap -> Shift2
      - FlagsIsInDanger -> Subshift3 (bit 2)
    """
    print("Test: Rules engine -> real VKB server (dashboard flags)")

    handler = _make_handler_with_rules()
    assert handler.rule_engine is not None, "Rules failed to load"
    print(f"  Loaded {len(handler.rule_engine.rules)} rules")

    try:
        assert handler.connect(), "Failed to connect"
        time.sleep(STEP_DELAY)

        # reset
        handler._reset_shift_state()
        time.sleep(STEP_DELAY)

        # 1) Hardpoints deployed -> should set Shift1
        print("\n  -- Scenario: Hardpoints deployed --")
        handler.handle_event(
            "Status",
            {"event": "Status", "Flags": FLAGS["FlagsHardpointsDeployed"] | FLAGS["FlagsInMainShip"] | FLAGS["FlagsShieldsUp"], "Flags2": 0, "GuiFocus": 0},
            source="dashboard",
        )
        time.sleep(STEP_DELAY)
        assert handler._shift_bitmap & (1 << 0), "Shift1 should be set (hardpoints)"
        print(f"  [OK] Shift: 0b{handler._shift_bitmap:08b}  Subshift: 0b{handler._subshift_bitmap:08b} (Shift1 set)")

        # 2) Hardpoints retracted -> should clear Shift1 (else branch)
        print("  -- Scenario: Hardpoints retracted --")
        handler.handle_event(
            "Status",
            {"event": "Status", "Flags": FLAGS["FlagsInMainShip"] | FLAGS["FlagsShieldsUp"], "Flags2": 0, "GuiFocus": 0},
            source="dashboard",
        )
        time.sleep(STEP_DELAY)
        assert not (handler._shift_bitmap & (1 << 0)), "Shift1 should be cleared"
        print(f"  [OK] Shift: 0b{handler._shift_bitmap:08b}  Subshift: 0b{handler._subshift_bitmap:08b} (Shift1 cleared)")

        # 3) Galaxy map -> Shift2
        print("  -- Scenario: Galaxy Map open --")
        handler.handle_event(
            "Status",
            {"event": "Status", "Flags": FLAGS["FlagsInMainShip"], "Flags2": 0, "GuiFocus": 6},
            source="dashboard",
        )
        time.sleep(STEP_DELAY)
        assert handler._shift_bitmap & (1 << 1), "Shift2 should be set (galaxy map)"
        print(f"  [OK] Shift: 0b{handler._shift_bitmap:08b}  Subshift: 0b{handler._subshift_bitmap:08b} (Shift2 set)")

        # 4) In danger -> Subshift3 (bit 2)
        print("  -- Scenario: In danger --")
        handler.handle_event(
            "Status",
            {"event": "Status", "Flags": FLAGS["FlagsIsInDanger"] | FLAGS["FlagsInMainShip"], "Flags2": 0, "GuiFocus": 0},
            source="dashboard",
        )
        time.sleep(STEP_DELAY)
        assert handler._subshift_bitmap & (1 << 2), "Subshift3 should be set (danger) -> bit 2"
        print(f"  [OK] Shift: 0b{handler._shift_bitmap:08b}  Subshift: 0b{handler._subshift_bitmap:08b} (Subshift3 set)")

        # 5) All clear
        print("  -- Scenario: Neutral (all clear) --")
        handler.handle_event(
            "Status",
            {"event": "Status", "Flags": FLAGS["FlagsInMainShip"] | FLAGS["FlagsShieldsUp"], "Flags2": 0, "GuiFocus": 0},
            source="dashboard",
        )
        time.sleep(STEP_DELAY)
        print(f"  [OK] Shift: 0b{handler._shift_bitmap:08b}  Subshift: 0b{handler._subshift_bitmap:08b}")

    finally:
        handler._reset_shift_state()
        time.sleep(STEP_DELAY)
        handler.disconnect()


@skip_if_no_real_server
def test_real_server_rules_journal_events():
    """Send journal events through the rule engine to real VKB hardware.

    Uses rules_comprehensive.json which maps:
      - FSDJump with JumpDist > 5.0 -> Subshift1 (bit 0)
      - Location with StarSystem containing "Empire" -> Subshift2 (bit 1)
      - FSDJump / SupercruiseEntry / StartJump -> Subshift4 (bit 3)
    """
    print("Test: Rules engine -> real VKB server (journal events)")

    handler = _make_handler_with_rules()
    assert handler.rule_engine is not None, "Rules failed to load"

    try:
        assert handler.connect(), "Failed to connect"
        time.sleep(STEP_DELAY)
        handler._reset_shift_state()
        time.sleep(STEP_DELAY)

        # 1) Short FSD jump (< 5.0 ly) -- should NOT set Subshift1
        print("\n  -- Scenario: Short FSD jump (4.9 ly) --")
        handler.handle_event(
            "FSDJump",
            {"event": "FSDJump", "StarSystem": "Shinrarta Dezhra", "JumpDist": 4.9, "SystemAddress": 3932277478106},
            source="journal",
            cmdr="TestCmdr",
        )
        time.sleep(STEP_DELAY)
        print(f"  [OK] Shift: 0b{handler._shift_bitmap:08b}  Subshift: 0b{handler._subshift_bitmap:08b}")

        # 2) Far FSD jump (45.3 ly) -- SHOULD set Subshift1 (bit 0) and Subshift4 (bit 3)
        print("  -- Scenario: Far FSD jump (45.3 ly) --")
        handler.handle_event(
            "FSDJump",
            {"event": "FSDJump", "StarSystem": "Beagle Point", "JumpDist": 45.3, "SystemAddress": 29281278643457},
            source="journal",
            cmdr="TestCmdr",
        )
        time.sleep(STEP_DELAY)
        assert handler._subshift_bitmap & (1 << 0), "Subshift1 should be set (far jump) -> bit 0"
        assert handler._subshift_bitmap & (1 << 3), "Subshift4 should be set (FSDJump event list) -> bit 3"
        print(f"  [OK] Shift: 0b{handler._shift_bitmap:08b}  Subshift: 0b{handler._subshift_bitmap:08b} (Subshift1 + Subshift4 set)")

        # 3) Location in Empire system -> Subshift2 (bit 1)
        print("  -- Scenario: Location in Empire space --")
        handler.handle_event(
            "Location",
            {"event": "Location", "StarSystem": "Empire Prime", "SystemAddress": 10477373803},
            source="journal",
            cmdr="TestCmdr",
        )
        time.sleep(STEP_DELAY)
        assert handler._subshift_bitmap & (1 << 1), "Subshift2 should be set (Empire system) -> bit 1"
        print(f"  [OK] Shift: 0b{handler._shift_bitmap:08b}  Subshift: 0b{handler._subshift_bitmap:08b} (Subshift2 set)")

        # 4) Session reset via LoadGame -> clears everything
        print("  -- Scenario: LoadGame session reset --")
        handler.handle_event(
            "LoadGame",
            {"event": "LoadGame", "Commander": "TestCmdr"},
            source="journal",
            cmdr="TestCmdr",
        )
        time.sleep(STEP_DELAY)
        assert handler._shift_bitmap == 0, f"Shift should be 0 after reset, got {handler._shift_bitmap}"
        assert handler._subshift_bitmap == 0, f"Subshift should be 0 after reset, got {handler._subshift_bitmap}"
        print(f"  [OK] Shift: 0b{handler._shift_bitmap:08b}  Subshift: 0b{handler._subshift_bitmap:08b} (reset)")

    finally:
        handler._reset_shift_state()
        time.sleep(STEP_DELAY)
        handler.disconnect()


@skip_if_no_real_server
def test_real_server_rules_with_fixture_data():
    """Play back ALL fixture payloads from edmc_notifications.json through rules.

    This mirrors how test_rules_comprehensive.py tests work, but sends the
    actual VKBShiftBitmap packets to real hardware so you can see the state
    changes on the device.
    """
    print("Test: Fixture payloads -> rules engine -> real VKB server")

    handler = _make_handler_with_rules()
    assert handler.rule_engine is not None, "Rules failed to load"
    notifications = _load_notifications()

    try:
        assert handler.connect(), "Failed to connect"
        time.sleep(STEP_DELAY)
        handler._reset_shift_state()
        time.sleep(STEP_DELAY)

        # -- Journal events --
        print("\n  == Journal events ==")
        for name, payload in notifications.get("journal", {}).items():
            event_type = payload.get("event", "Unknown")
            handler.handle_event(event_type, payload, source="journal", cmdr="TestCmdr")
            time.sleep(STEP_DELAY)
            print(f"  [OK] {name:30s} -> shift=0b{handler._shift_bitmap:08b}  subshift=0b{handler._subshift_bitmap:08b}")

        # -- Dashboard / Status events --
        print("\n  == Dashboard (Status) events ==")
        for name, payload in notifications.get("status_dashboard", {}).items():
            handler.handle_event("Status", payload, source="dashboard")
            time.sleep(STEP_DELAY)
            print(f"  [OK] {name:30s} -> shift=0b{handler._shift_bitmap:08b}  subshift=0b{handler._subshift_bitmap:08b}")

        # -- CAPI events --
        if "capi" in notifications:
            print("\n  == CAPI events ==")
            for name, payload in notifications["capi"].items():
                handler.handle_event("CmdrData", payload, source="capi", cmdr="TestCmdr")
                time.sleep(STEP_DELAY)
                print(f"  [OK] {name:30s} -> shift=0b{handler._shift_bitmap:08b}  subshift=0b{handler._subshift_bitmap:08b}")

        print(f"\n  [OK] All fixture payloads sent to real hardware")

    finally:
        handler._reset_shift_state()
        time.sleep(STEP_DELAY)
        handler.disconnect()


@skip_if_no_real_server
def test_real_server_simulated_gameplay_session():
    """Simulate a realistic gameplay session through rules to real hardware.

    Scenario:
      1. LoadGame -> reset
      2. Undocked from station (Status: InMainShip+ShieldsUp)
      3. Supercruise (Status: Supercruise+InMainShip+ShieldsUp)
      4. FSD jump to far system (journal: FSDJump 45 ly)
      5. Arrive in Empire space (journal: Location)
      6. Drop to normal space, deploy hardpoints
      7. Danger! Being interdicted
      8. Open galaxy map
      9. Close galaxy map, retract hardpoints
     10. Dock at station -> reset
    """
    print("Test: Simulated gameplay session -> real VKB server")

    handler = _make_handler_with_rules()
    assert handler.rule_engine is not None, "Rules failed to load"

    try:
        assert handler.connect(), "Failed to connect"
        time.sleep(STEP_DELAY)

        steps = [
            ("LoadGame (session start)", "LoadGame",
             {"event": "LoadGame", "Commander": "TestCmdr", "GameMode": "Open"},
             "journal"),

            ("Undocked", "Status",
             {"event": "Status", "Flags": FLAGS["FlagsInMainShip"] | FLAGS["FlagsShieldsUp"], "Flags2": 0, "GuiFocus": 0},
             "dashboard"),

            ("Enter supercruise", "Status",
             {"event": "Status", "Flags": FLAGS["FlagsSupercruise"] | FLAGS["FlagsInMainShip"] | FLAGS["FlagsShieldsUp"], "Flags2": 0, "GuiFocus": 0},
             "dashboard"),

            ("FSD Jump (45 ly)", "FSDJump",
             {"event": "FSDJump", "StarSystem": "Empire Prime", "JumpDist": 45.3, "SystemAddress": 10477373803},
             "journal"),

            ("Arrive in Empire space", "Location",
             {"event": "Location", "StarSystem": "Empire Prime", "SystemAddress": 10477373803},
             "journal"),

            ("Drop + deploy hardpoints", "Status",
             {"event": "Status", "Flags": FLAGS["FlagsHardpointsDeployed"] | FLAGS["FlagsInMainShip"] | FLAGS["FlagsShieldsUp"], "Flags2": 0, "GuiFocus": 0},
             "dashboard"),

            ("Being interdicted!", "Status",
             {"event": "Status", "Flags": FLAGS["FlagsBeingInterdicted"] | FLAGS["FlagsIsInDanger"] | FLAGS["FlagsInMainShip"] | FLAGS["FlagsShieldsUp"], "Flags2": 0, "GuiFocus": 0},
             "dashboard"),

            ("Escaped - open galaxy map", "Status",
             {"event": "Status", "Flags": FLAGS["FlagsInMainShip"] | FLAGS["FlagsShieldsUp"], "Flags2": 0, "GuiFocus": 6},
             "dashboard"),

            ("Close map, retract hardpoints", "Status",
             {"event": "Status", "Flags": FLAGS["FlagsInMainShip"] | FLAGS["FlagsShieldsUp"], "Flags2": 0, "GuiFocus": 0},
             "dashboard"),

            ("Dock at station (session end)", "LoadGame",
             {"event": "LoadGame", "Commander": "TestCmdr"},
             "journal"),
        ]

        for i, (desc, event_type, payload, source) in enumerate(steps, 1):
            handler.handle_event(event_type, payload, source=source, cmdr="TestCmdr")
            time.sleep(STEP_DELAY * 2)  # Slower pace for visual inspection
            print(f"  [{i:2d}] {desc:40s} -> shift=0b{handler._shift_bitmap:08b}  subshift=0b{handler._subshift_bitmap:08b}")

        print(f"\n  [OK] Gameplay session complete")

    finally:
        handler._reset_shift_state()
        time.sleep(STEP_DELAY)
        handler.disconnect()


# ---------------------------------------------------------------------------
# Stability tests
# ---------------------------------------------------------------------------

@skip_if_no_real_server
def test_real_server_persistence():
    """Test connection persistence across multiple operations."""
    print("Test: Connection persistence on real hardware")

    client = VKBClient(
        host=TEST_VKB_HOST,
        port=TEST_VKB_PORT,
        socket_timeout=5,
    )

    try:
        assert client.connect(), "Failed to connect"
        time.sleep(STEP_DELAY)
        operations = 0
        for i in range(5):
            success = client.send_event("VKBShiftBitmap", {"shift": i % 3, "subshift": 0})
            if success:
                operations += 1
            time.sleep(0.3)

        assert client.connected, "Connection lost during operations"
        assert operations == 5, f"Only {operations}/5 operations succeeded"
        print(f"  [OK] Connection remained stable across {operations} operations")
    finally:
        client.send_event("VKBShiftBitmap", {"shift": 0, "subshift": 0})
        client.disconnect()


@skip_if_no_real_server
def test_real_server_rapid_messages():
    """Test rapid message transmission to real hardware."""
    print("Test: Rapid message transmission to hardware")

    client = VKBClient(
        host=TEST_VKB_HOST,
        port=TEST_VKB_PORT,
        socket_timeout=5,
    )

    try:
        assert client.connect(), "Failed to connect"
        time.sleep(STEP_DELAY)
        sent = 0
        for i in range(10):
            success = client.send_event(
                "VKBShiftBitmap",
                {"shift": i % 3, "subshift": i % 7},
            )
            if success:
                sent += 1
            time.sleep(STEP_DELAY)

        print(f"  [OK] Sent {sent}/10 messages with {STEP_DELAY}s delay")
        assert sent > 0, "No messages sent"
    finally:
        client.send_event("VKBShiftBitmap", {"shift": 0, "subshift": 0})
        time.sleep(STEP_DELAY)
        client.disconnect()


# ---------------------------------------------------------------------------
# CLI runner
# ---------------------------------------------------------------------------

def main():
    """Run real VKB server tests if configured."""
    print("\n" + "=" * 60)
    print("Real VKB Server Integration Tests")
    print("=" * 60)
    print(f"\nConfiguration:")
    print(f"  Host: {TEST_VKB_HOST}")
    print(f"  Port: {TEST_VKB_PORT}")
    print(f"  Enabled: {TEST_VKB_ENABLED}")
    print()

    if not TEST_VKB_ENABLED:
        print("Real VKB server tests are DISABLED.")
        print("To enable, set environment variable: TEST_VKB_ENABLED=1")
        print("\nExample:")
        print("  $env:TEST_VKB_ENABLED = '1'; python test_real_vkb_server.py")
        return 0

    if not check_server_available():
        print(f"ERROR: VKB server not available at {TEST_VKB_HOST}:{TEST_VKB_PORT}")
        return 1

    print(f"VKB server FOUND at {TEST_VKB_HOST}:{TEST_VKB_PORT}")
    print("Running real hardware tests...\n")

    tests = [
        ("Connection", test_real_server_connection),
        ("Send shift state", test_real_server_send_shift_state),
        ("Multiple shifts", test_real_server_multiple_shifts),
        ("Roll individual flags", test_real_server_roll_shift_flags),
        ("Roll cumulative flags", test_real_server_roll_cumulative_flags),
        ("EventHandler (no rules)", test_real_server_event_handler),
        ("Rules: dashboard flags", test_real_server_rules_dashboard_flags),
        ("Rules: journal events", test_real_server_rules_journal_events),
        ("Rules: fixture payloads", test_real_server_rules_with_fixture_data),
        ("Rules: gameplay session", test_real_server_simulated_gameplay_session),
        ("Persistence", test_real_server_persistence),
        ("Rapid messages", test_real_server_rapid_messages),
    ]

    passed = 0
    failed = 0

    for test_name, test_func in tests:
        try:
            print(f"\n{test_name}:")
            test_func()
            print(f"  PASS")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

