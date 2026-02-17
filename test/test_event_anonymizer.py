"""
Test event anonymization functionality.
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from edmcruleengine.event_anonymizer import EventAnonymizer


def test_anonymizer_basic():
    """Test basic anonymization functionality."""
    anonymizer = EventAnonymizer(
        mock_commander_name="TestCMDR",
        mock_ship_name="TestShip",
        mock_ship_ident="TEST-01"
    )
    
    # Test commander name anonymization
    event = {
        "event": "Commander",
        "Name": "CMDR RealName",
        "FID": "F123456",
    }
    
    anonymized = anonymizer.anonymize_event(event)
    
    assert anonymized["Name"] == "TestCMDR", f"Expected 'TestCMDR', got {anonymized['Name']}"
    assert anonymized["FID"] == "TestCMDR", f"Expected 'TestCMDR', got {anonymized['FID']}"
    print("✓ Commander name anonymization works")


def test_anonymizer_ship():
    """Test ship name anonymization."""
    anonymizer = EventAnonymizer(
        mock_commander_name="TestCMDR",
        mock_ship_name="TestShip",
        mock_ship_ident="TEST-01"
    )
    
    event = {
        "event": "Loadout",
        "ShipName": "My Real Ship",
        "ShipIdent": "ABC-123",
    }
    
    anonymized = anonymizer.anonymize_event(event)
    
    assert anonymized["ShipName"] == "TestShip", f"Expected 'TestShip', got {anonymized['ShipName']}"
    assert anonymized["ShipIdent"] == "TEST-01", f"Expected 'TEST-01', got {anonymized['ShipIdent']}"
    print("✓ Ship name anonymization works")


def test_anonymizer_paths():
    """Test path anonymization."""
    anonymizer = EventAnonymizer()
    
    # Test Windows path
    event = {
        "Path": r"C:\Users\Player\Documents\file.txt"
    }
    anonymized = anonymizer.anonymize_event(event)
    assert "Player" not in anonymized["Path"], f"Path still contains identifying info: {anonymized['Path']}"
    print(f"✓ Windows path anonymized: {anonymized['Path']}")
    
    # Test Unix path
    event = {
        "Path": "/home/player/documents/file.txt"
    }
    anonymized = anonymizer.anonymize_event(event)
    assert "player" not in anonymized["Path"], f"Path still contains identifying info: {anonymized['Path']}"
    print(f"✓ Unix path anonymized: {anonymized['Path']}")


def test_anonymizer_nested():
    """Test nested structure anonymization."""
    anonymizer = EventAnonymizer(mock_commander_name="TestCMDR")
    
    event = {
        "event": "Loadout",
        "Commander": "RealCMDR",
        "Modules": [
            {"Item": "Module1"},
            {"Item": "Module2", "Commander": "RealCMDR"}
        ]
    }
    
    anonymized = anonymizer.anonymize_event(event)
    
    assert anonymized["Commander"] == "TestCMDR"
    assert anonymized["Modules"][1]["Commander"] == "TestCMDR"
    print("✓ Nested structure anonymization works")


def test_anonymizer_ip_addresses():
    """Test IP address anonymization."""
    anonymizer = EventAnonymizer()
    
    event = {
        "IPAddress": "192.168.1.100",
        "ServerIP": "10.0.0.5",
        "text": "Connected to 192.168.1.100"
    }
    
    anonymized = anonymizer.anonymize_event(event)
    
    assert anonymized["IPAddress"] == "127.0.0.1"
    assert anonymized["ServerIP"] == "127.0.0.1"
    assert "192.168.1.100" not in anonymized["text"]
    print("✓ IP address anonymization works")


if __name__ == "__main__":
    print("Testing EventAnonymizer...")
    test_anonymizer_basic()
    test_anonymizer_ship()
    test_anonymizer_paths()
    test_anonymizer_nested()
    test_anonymizer_ip_addresses()
    print("\n✅ All tests passed!")
