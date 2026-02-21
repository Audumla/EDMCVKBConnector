"""
Test VKB-Link INI file update functionality.
"""

import os
import sys
import tempfile

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Import the function (we need to temporarily set up the environment)
import load


def test_ini_file_creation():
    """Test creating a new INI file with TCP section."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
        ini_path = f.name
    
    try:
        # Create new INI file
        result = load._update_ini_file(ini_path, "192.168.1.100", "50995")
        assert result, "Failed to create INI file"
        
        # Verify contents
        with open(ini_path, 'r') as f:
            contents = f.read()
        
        assert "[TCP]" in contents, "TCP section not found"
        assert "Adress = 192.168.1.100" in contents or "Adress=192.168.1.100" in contents, "Adress not set correctly"
        assert "Port = 50995" in contents or "Port=50995" in contents, "Port not set correctly"
        print("✓ INI file creation works")
        print(f"  Created contents:\n{contents}")
    
    finally:
        if os.path.exists(ini_path):
            os.unlink(ini_path)


def test_ini_file_update():
    """Test updating an existing INI file."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
        # Write initial content
        f.write("[General]\n")
        f.write("Setting1 = Value1\n")
        f.write("\n")
        f.write("[TCP]\n")
        f.write("Adress = 127.0.0.1\n")
        f.write("Port = 12345\n")
        ini_path = f.name
    
    try:
        # Update existing INI file
        result = load._update_ini_file(ini_path, "10.0.0.1", "54321")
        assert result, "Failed to update INI file"
        
        # Verify contents
        with open(ini_path, 'r') as f:
            contents = f.read()
        
        assert "[General]" in contents, "General section lost"
        assert "Setting1 = Value1" in contents or "Setting1=Value1" in contents, "Existing settings lost"
        assert "Adress = 10.0.0.1" in contents or "Adress=10.0.0.1" in contents, "Adress not updated"
        assert "Port = 54321" in contents or "Port=54321" in contents, "Port not updated"
        print("✓ INI file update works")
        print(f"  Updated contents:\n{contents}")
    
    finally:
        if os.path.exists(ini_path):
            os.unlink(ini_path)


def test_ini_file_typo_preserved():
    """Test that the 'Adress' typo is preserved (as per spec)."""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.ini', delete=False) as f:
        ini_path = f.name
    
    try:
        result = load._update_ini_file(ini_path, "localhost", "8080")
        assert result, "Failed to create INI file"
        
        with open(ini_path, 'r') as f:
            contents = f.read()
        
        # Verify that "Adress" (with typo) is used, not "Address"
        assert "Adress" in contents, "'Adress' (with typo) not found"
        assert "Address =" not in contents, "Found 'Address' instead of 'Adress' - typo not preserved!"
        print("✓ 'Adress' typo preserved correctly")
    
    finally:
        if os.path.exists(ini_path):
            os.unlink(ini_path)


if __name__ == "__main__":
    print("Testing VKB-Link INI file update functionality...")
    test_ini_file_creation()
    test_ini_file_update()
    test_ini_file_typo_preserved()
    print("\n✅ All INI file tests passed!")
