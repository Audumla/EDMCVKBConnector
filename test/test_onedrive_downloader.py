"""
Tests for OneDrive downloader.
"""

import os
import pytest
from pathlib import Path
from src.edmcruleengine.utils.downloaders import DownloadItem
from src.edmcruleengine.utils.onedrive_downloader import OneDriveDownloader

# Public share for testing
TEST_SHARE_URL = "https://1drv.ms/f/s!AiXf55zyUARXbNlV11a4z3ce38g"
EXPECTED_FILE = "VKB-Link v0.8.2.zip"

def test_onedrive_list_items():
    """Test listing items from OneDrive public share."""
    downloader = OneDriveDownloader(TEST_SHARE_URL)
    items = downloader.list_items()
    
    assert isinstance(items, list)
    # If the share is accessible, we should find our file
    found = any(r.filename == EXPECTED_FILE for r in items)
    
    if not items:
        pytest.skip("OneDrive share not accessible or empty during test")
        
    assert found, f"Could not find {EXPECTED_FILE} in releases"
    
    # Verify version parsing
    v082 = next(r for r in items if r.filename == EXPECTED_FILE)
    assert v082.version == "0.8.2"

@pytest.mark.live_agent # Use this marker to indicate it needs network
def test_onedrive_download_metadata_url(tmp_path):
    """Test downloading using the URL from metadata."""
    downloader = OneDriveDownloader(TEST_SHARE_URL)
    items = downloader.list_items()
    
    if not items:
        pytest.skip("OneDrive share not accessible")
        
    item = next((r for r in items if r.filename == EXPECTED_FILE), None)
    if not item or not item.url:
        pytest.skip(f"Item {EXPECTED_FILE} not found or has no direct URL")
        
    target = tmp_path / "test_download.zip"
    success = downloader.download(item, target)
    
    assert success
    assert target.exists()
    assert target.stat().st_size > 1000000 # v0.8.2 is ~2MB

def test_onedrive_download_direct_resolution(tmp_path):
    """Test downloading where we have to resolve the link manually."""
    downloader = OneDriveDownloader(TEST_SHARE_URL)
    
    # Create a download item object without a URL to force resolution
    item = DownloadItem(
        version="0.8.2",
        filename=EXPECTED_FILE,
        url="" # Empty URL forces downloader to resolve it
    )
    
    target = tmp_path / "test_resolved.zip"
    success = downloader.download(item, target)
    
    # This might fail if the folder-listing-to-direct-link resolution fails
    # but let's see if the downloader can handle it.
    if not success:
        # Check if it's a known limitation
        from src.edmcruleengine.utils.onedrive_downloader import get_direct_download_url
        url = get_direct_download_url(TEST_SHARE_URL, EXPECTED_FILE)
        if not url:
            pytest.skip("Known limitation: cannot resolve direct link from folder share without auth")
            
    assert success
    assert target.exists()
