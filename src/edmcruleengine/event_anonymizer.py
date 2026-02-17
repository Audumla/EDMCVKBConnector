"""
Event anonymization module for EDMC VKB Connector.

Anonymizes Elite Dangerous events by replacing commander-specific and
system-specific information with mock data while maintaining event validity.
"""

import re
from typing import Any, Dict, List

from . import plugin_logger

logger = plugin_logger(__name__)


class EventAnonymizer:
    """
    Anonymizes Elite Dangerous events by replacing identifying information.
    
    Replaces:
    - Commander names, FIDs, and ship identifiers
    - System paths (drives, folders)
    - Network addresses and ports
    - Other identifying information
    
    Maintains event validity and structure.
    """
    
    # Fields that contain commander-specific information
    COMMANDER_FIELDS = {
        "Commander", "Name", "PlayerName", "commanderName",
        "FID", "commanderId", "PlayerId",
    }
    
    # Fields that contain ship information
    SHIP_FIELDS = {
        "ShipName", "ShipIdent", "UserShipName", "UserShipId",
    }
    
    # Fields that may contain file paths
    PATH_FIELDS = {
        "Path", "Directory", "Folder", "File", "Filename",
    }
    
    # Fields that may contain network information
    NETWORK_FIELDS = {
        "IP", "IPAddress", "Host", "Port",
    }
    
    def __init__(
        self,
        mock_commander_name: str = "TestCommander",
        mock_ship_name: str = "TestShip",
        mock_ship_ident: str = "TEST-01",
    ):
        """
        Initialize the event anonymizer.
        
        Args:
            mock_commander_name: Mock commander name to use
            mock_ship_name: Mock ship name to use
            mock_ship_ident: Mock ship identifier to use
        """
        self.mock_commander_name = mock_commander_name
        self.mock_ship_name = mock_ship_name
        self.mock_ship_ident = mock_ship_ident
        
        # Compile regex patterns for path detection
        self.windows_path_pattern = re.compile(r'[A-Z]:\\[^"\'<>|]*')
        self.unix_path_pattern = re.compile(r'/[^\s"\'<>|]*')
        
        # Pattern for IP addresses
        self.ip_pattern = re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b')
    
    def anonymize_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Anonymize an event by replacing identifying information.
        
        Args:
            event_data: Original event data
            
        Returns:
            Anonymized copy of event data
        """
        # Create a deep copy to avoid modifying the original
        anonymized = self._deep_copy_dict(event_data)
        
        # Recursively anonymize the event
        self._anonymize_dict(anonymized)
        
        return anonymized
    
    def _deep_copy_dict(self, data: Any) -> Any:
        """Create a deep copy of data structures."""
        if isinstance(data, dict):
            return {k: self._deep_copy_dict(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._deep_copy_dict(item) for item in data]
        else:
            return data
    
    def _anonymize_dict(self, data: Dict[str, Any]) -> None:
        """
        Recursively anonymize a dictionary in-place.
        
        Args:
            data: Dictionary to anonymize
        """
        for key, value in list(data.items()):
            # Handle nested structures
            if isinstance(value, dict):
                self._anonymize_dict(value)
            elif isinstance(value, list):
                self._anonymize_list(value)
            elif isinstance(value, str):
                # Anonymize string values based on field name
                data[key] = self._anonymize_string_field(key, value)
    
    def _anonymize_list(self, data: List[Any]) -> None:
        """
        Recursively anonymize a list in-place.
        
        Args:
            data: List to anonymize
        """
        for i, item in enumerate(data):
            if isinstance(item, dict):
                self._anonymize_dict(item)
            elif isinstance(item, list):
                self._anonymize_list(item)
            elif isinstance(item, str):
                data[i] = self._anonymize_string_value(item)
    
    def _anonymize_string_field(self, field_name: str, value: str) -> str:
        """
        Anonymize a string value based on the field name.
        
        Args:
            field_name: Name of the field
            value: String value to anonymize
            
        Returns:
            Anonymized string value
        """
        # Commander fields
        if field_name in self.COMMANDER_FIELDS:
            return self.mock_commander_name
        
        # Ship fields
        if field_name in self.SHIP_FIELDS:
            if "Ident" in field_name or "Id" in field_name:
                return self.mock_ship_ident
            return self.mock_ship_name
        
        # Path fields
        if field_name in self.PATH_FIELDS:
            return self._anonymize_path(value)
        
        # Network fields
        if field_name in self.NETWORK_FIELDS:
            if "Port" in field_name:
                return "12345"
            return "127.0.0.1"
        
        # For other fields, check for embedded paths and IPs
        return self._anonymize_string_value(value)
    
    def _anonymize_string_value(self, value: str) -> str:
        """
        Anonymize a string value by removing embedded paths and IPs.
        
        Args:
            value: String value to anonymize
            
        Returns:
            Anonymized string value
        """
        # Replace Windows paths
        value = self.windows_path_pattern.sub(r'C:\\MockPath', value)
        
        # Replace Unix paths (but not URLs)
        if not value.startswith(('http://', 'https://', 'ftp://')):
            value = self.unix_path_pattern.sub(r'/mock/path', value)
        
        # Replace IP addresses
        value = self.ip_pattern.sub('127.0.0.1', value)
        
        return value
    
    def _anonymize_path(self, path: str) -> str:
        """
        Anonymize a file path.
        
        Args:
            path: File path to anonymize
            
        Returns:
            Anonymized path
        """
        if not path:
            return path
        
        # Windows path
        if self.windows_path_pattern.match(path):
            return r'C:\MockPath\file.ext'
        
        # Unix path
        if path.startswith('/'):
            return '/mock/path/file.ext'
        
        # Relative path
        return 'mock/path/file.ext'
