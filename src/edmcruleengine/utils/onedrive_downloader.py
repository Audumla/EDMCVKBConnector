"""
OneDrive direct download helper for shared folders/files.
Converts a sharing URL into a direct download link using the sharing token method.
"""

from __future__ import annotations

import base64
import json
import re
import urllib.request
from pathlib import Path
from typing import Optional, List, Dict, TYPE_CHECKING

from .downloaders import Downloader, DownloadItem

if TYPE_CHECKING:
    from logging import Logger


class OneDriveDownloader(Downloader):
    """Downloader implementation for OneDrive shared folders."""

    def __init__(self, sharing_url: str, logger: Optional["Logger"] = None):
        self.sharing_url = sharing_url
        self.logger = logger
        self._version_re = re.compile(r"v(\d+\.\d+\.\d+)")

    def is_available(self) -> bool:
        return True # Always available (uses standard urllib)

    def list_items(self) -> List[DownloadItem]:
        items = list_shared_folder(self.sharing_url)
        results = []
        
        for item in items:
            name = item.get('name', '')
            if not name.endswith('.zip'):
                continue
                
            version_match = self._version_re.search(name)
            version = version_match.group(1) if version_match else "0.0.0"
            
            results.append(DownloadItem(
                version=version,
                filename=name,
                url=item.get('@content.downloadUrl', ''),
                provider_data={"id": item.get('id')}
            ))
            
        return results

    def download(self, item: DownloadItem, target_path: Path) -> bool:
        url = item.url
        if not url:
            url = get_direct_download_url(self.sharing_url, item.filename)
            if not url:
                return False
            
        try:
            urllib.request.urlretrieve(url, str(target_path))
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"OneDrive download failed: {e}")
            return False


def resolve_redirect(url: str) -> str:
    """Resolve 1drv.ms short links to their full OneDrive URLs."""
    req = urllib.request.Request(url, method='HEAD')
    try:
        with urllib.request.urlopen(req) as response:
            return response.geturl()
    except Exception:
        return url


def get_sharing_token(sharing_url: str) -> str:
    """
    Converts a OneDrive sharing URL into a sharing token used by MS Graph API.
    """
    # 1drv.ms links need to be resolved to full sharing URLs first
    full_url = resolve_redirect(sharing_url)
    
    # Use urlsafe_b64encode to handle +/- and /_ replacements automatically
    url_bytes = full_url.encode('utf-8')
    base64_bytes = base64.urlsafe_b64encode(url_bytes)
    base64_string = base64_bytes.decode('utf-8')
    
    # Standard transformation for sharing tokens: remove trailing =
    token = base64_string.rstrip('=')
    return "u!" + token


def list_shared_folder(sharing_url: str) -> List[Dict[str, Any]]:
    """
    Lists files in a shared OneDrive folder using the MS Graph API.
    """
    token = get_sharing_token(sharing_url)
    
    # expand=children is the key to getting the file list without separate auth
    endpoints = [
        f"https://graph.microsoft.com/v1.0/shares/{token}/driveItem?$expand=children",
        f"https://api.onedrive.com/v1.0/shares/{token}/root?$expand=children"
    ]
    
    for api_url in endpoints:
        try:
            print(f"DEBUG: Trying {api_url[:70]}...")
            req = urllib.request.Request(api_url)
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode('utf-8'))
                # The children are in the 'children' key when using $expand
                if 'children' in data:
                    return data['children']
                # Fallback for some API versions
                return data.get('value', [])
        except Exception as e:
            print(f"DEBUG: Endpoint {api_url[:30]} failed: {e}")
            continue
    return []


def get_direct_download_url(sharing_url: str, filename: Optional[str] = None) -> Optional[str]:
    """
    Returns a direct download URL for a file in a shared folder.
    Attempts multiple methods including URL transformation and Graph API.
    """
    # Method 1: URL Transformation (Personal OneDrive)
    # redir -> download
    try:
        full_url = resolve_redirect(sharing_url)
        if "onedrive.live.com/redir" in full_url:
            direct_url = full_url.replace("onedrive.live.com/redir", "onedrive.live.com/download")
            # If sharing_url was for a single file, this is likely already correct.
            if not filename:
                return direct_url
    except Exception as e:
        print(f"DEBUG: URL transformation failed: {e}")

    # Method 2: MS Graph API (for folder listings or single item metadata)
    token = get_sharing_token(sharing_url)
    
    if filename:
        items = list_shared_folder(sharing_url)
        for item in items:
            if item.get('name') == filename:
                return item.get('@content.downloadUrl')
        return None
    else:
        # Get metadata for the item itself
        api_url = f"https://api.onedrive.com/v1.0/shares/{token}/driveItem"
        try:
            with urllib.request.urlopen(api_url) as response:
                data = json.loads(response.read().decode('utf-8'))
                return data.get('@content.downloadUrl')
        except Exception:
            return None


def download_file(sharing_url: str, target_path: str, filename: Optional[str] = None) -> bool:
    """
    Downloads a file from a shared OneDrive link to target_path.
    """
    download_url = get_direct_download_url(sharing_url, filename)
    if not download_url:
        print(f"Could not find download URL for {filename or 'shared item'}")
        return False
    
    try:
        print(f"Downloading from: {download_url[:60]}...")
        urllib.request.urlretrieve(download_url, target_path)
        print(f"Successfully downloaded to {target_path}")
        return True
    except Exception as e:
        print(f"Download failed: {e}")
        return False


if __name__ == "__main__":
    import os
    
    # Test with the provided link
    SHARE_URL = "https://1drv.ms/f/s!AiXf55zyUARXbNlV11a4z3ce38g"
    TARGET_FILE = "VKB-Link v0.8.2.zip"
    TEMP_OUT = "vkb_link_test.zip"
    
    print(f"Checking for '{TARGET_FILE}' in shared folder...")
    success = download_file(SHARE_URL, TEMP_OUT, TARGET_FILE)
    
    if success:
        print(f"SUCCESS: File downloaded to {TEMP_OUT}")
        if os.path.exists(TEMP_OUT):
            print(f"Size: {os.path.getsize(TEMP_OUT)} bytes")
            # Cleanup
            os.remove(TEMP_OUT)
    else:
        print("FAILURE: File could not be downloaded using standard API methods.")
        print("OneDrive folder shares are increasingly difficult to access via direct URL without a browser session.")
