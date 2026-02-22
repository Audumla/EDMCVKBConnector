"""
Tests to ensure VKB-Link management logic consolidation is correctly implemented.
Verifies that load.py does not contain duplicate INI logic and that the system
properly delegates to VKBLinkManager.
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import load
from edmcruleengine.vkb_link_manager import VKBLinkManager

def test_load_py_does_not_have_update_ini_file():
    """Verify that _update_ini_file has been removed from load.py."""
    assert not hasattr(load, "_update_ini_file"), "load.py still contains _update_ini_file; it should have been removed."

def test_vkb_link_manager_is_source_of_truth_for_ini_patching():
    """Verify that VKBLinkManager contains the correct INI patching logic."""
    manager = VKBLinkManager(config=Mock(), plugin_dir=Path("/tmp"))
    
    # Test text that should be patched
    original_text = "[TCP]\nAdress=1.1.1.1\nPort=1111\n"
    new_host = "127.0.0.1"
    new_port = 50995
    
    patched_text = manager._patch_ini_text(original_text, new_host, new_port)
    
    assert f"Adress={new_host}" in patched_text
    assert f"Port={new_port}" in patched_text
    assert "Adress=1.1.1.1" not in patched_text
    # Ensure "Adress" typo is preserved as per VKB-Link requirements
    assert "Adress" in patched_text
    assert "Address" not in patched_text

@patch("load.logger")
def test_plugin_start_uses_vkb_link_manager(mock_logger, tmp_path, monkeypatch):
    """
    Verify that plugin_start3 correctly interacts with VKBLinkManager via EventHandler.
    """
    # Setup mocks
    mock_config = Mock()
    mock_config.get.side_effect = lambda key, default=None: {
        "vkb_host": "127.0.0.1",
        "vkb_port": 50995,
        "vkb_link_auto_manage": True,
    }.get(key, default)
    
    mock_manager = Mock()
    mock_manager.get_status.return_value = Mock(running=False, exe_path="/path/to/exe", install_dir="/path", version="1.0", managed=True)
    mock_manager.ensure_running.return_value = Mock(success=True, message="Started", action_taken="started", status=mock_manager.get_status.return_value)
    
    mock_handler = Mock()
    mock_handler.vkb_link_manager = mock_manager
    mock_handler.connect.return_value = True
    mock_handler.refresh_unregistered_events_against_catalog.return_value = 0
    
    # Mock dependencies in load.py
    monkeypatch.setattr("edmcruleengine.Config", lambda: mock_config)
    monkeypatch.setattr("edmcruleengine.EventHandler", lambda *args, **kwargs: mock_handler)
    monkeypatch.setattr("edmcruleengine.event_recorder.EventRecorder", Mock)
    monkeypatch.setattr(load, "_ensure_rules_file_exists", Mock())
    monkeypatch.setattr(load, "_restore_test_shift_state_from_config", Mock())
    
    # Mock threading to run synchronously for testing
    class SyncThread:
        def __init__(self, target, args=(), kwargs=None, daemon=False):
            self.target = target
            self.args = args
            self.kwargs = kwargs or {}
        def start(self):
            self.target(*self.args, **self.kwargs)
            
    monkeypatch.setattr("threading.Thread", SyncThread)
    
    # Run plugin_start3
    result = load.plugin_start3(str(tmp_path))
    
    assert result == "VKB Connector"
    # Verify manager was called
    mock_manager.ensure_running.assert_called_once()
    # Verify it was called with correct host/port from config
    args, kwargs = mock_manager.ensure_running.call_args
    assert kwargs["host"] == "127.0.0.1"
    assert kwargs["port"] == 50995

def test_vkb_link_manager_write_ini_delegates_to_patch_ini_text(tmp_path):
    """Verify that _write_ini correctly uses _patch_ini_text and writes to file."""
    manager = VKBLinkManager(config=Mock(), plugin_dir=tmp_path)
    ini_path = tmp_path / "test.ini"
    
    # Test creation
    manager._write_ini(ini_path, "127.0.0.1", 50995)
    content = ini_path.read_text(encoding="utf-8")
    assert "[TCP]" in content
    assert "Adress=127.0.0.1" in content
    
    # Test update preserving other content
    ini_path.write_text("[Other]\nKey=Value\n" + content, encoding="utf-8")
    manager._write_ini(ini_path, "10.0.0.1", 1234)
    
    updated_content = ini_path.read_text(encoding="utf-8")
    assert "[Other]" in updated_content
    assert "Key=Value" in updated_content
    assert "Adress=10.0.0.1" in updated_content
    assert "Port=1234" in updated_content
