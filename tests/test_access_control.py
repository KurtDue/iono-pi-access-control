# Testing framework for the access control system

import pytest
import asyncio
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Mock hardware imports before importing our modules
import sys
sys.modules['RPi.GPIO'] = MagicMock()
sys.modules['serial'] = MagicMock()
sys.modules['httpx'] = MagicMock()
sys.modules['aiosqlite'] = MagicMock()

# Now import our modules
from src.config import Config
from src.hardware import IonoHardware
from src.barcode_scanner import BarcodeScanner
from src.database import AccessVerifier, AccessResult


class TestConfig:
    """Test configuration management"""
    
    def test_config_loading(self):
        """Test configuration loading"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("""
server:
  host: "127.0.0.1"
  port: 9000
hardware:
  relays:
    door_control: 5
""")
            config_file = f.name
        
        try:
            config = Config(config_file)
            assert config.server.host == "127.0.0.1"
            assert config.server.port == 9000
            assert config.hardware.relays.door_control == 5
        finally:
            os.unlink(config_file)
    
    def test_config_defaults(self):
        """Test default configuration values"""
        config = Config("nonexistent.yaml")
        assert config.server.host == "0.0.0.0"
        assert config.server.port == 8000
        assert config.hardware.relays.door_control == 4


class TestHardware:
    """Test hardware interface"""
    
    def test_hardware_initialization(self):
        """Test hardware initialization"""
        hardware = IonoHardware()
        assert hardware is not None
        assert hasattr(hardware, 'set_relay')
        assert hasattr(hardware, 'read_input')
    
    def test_relay_control(self):
        """Test relay control"""
        hardware = IonoHardware()
        
        # Test setting relay
        hardware.set_relay('door_control', True)
        # In mock mode, this should not raise an exception
        
        hardware.set_relay('door_control', False)
        # Test with duration
        hardware.set_relay('door_control', True, duration=1)
    
    def test_input_reading(self):
        """Test input reading"""
        hardware = IonoHardware()
        
        # Test reading inputs
        state = hardware.read_input('door_sensor')
        assert isinstance(state, bool)
        
        state = hardware.read_input('emergency_button')
        assert isinstance(state, bool)
    
    def test_door_operations(self):
        """Test door operations"""
        hardware = IonoHardware()
        
        # Test opening door
        hardware.open_door()
        hardware.open_door(duration=5)
        
        # Test door status
        is_open = hardware.is_door_open()
        assert isinstance(is_open, bool)
        
        # Test emergency override
        override_active = hardware.emergency_override_active()
        assert isinstance(override_active, bool)


class TestBarcodeScanner:
    """Test barcode scanner"""
    
    def test_scanner_initialization(self):
        """Test scanner initialization"""
        scanner = BarcodeScanner()
        assert scanner is not None
        assert hasattr(scanner, 'start')
        assert hasattr(scanner, 'stop')
    
    def test_scanner_lifecycle(self):
        """Test scanner start/stop"""
        scanner = BarcodeScanner()
        
        # Test starting
        result = scanner.start()
        assert isinstance(result, bool)
        
        # Test stopping
        scanner.stop()
        
        # Test connection status
        connected = scanner.is_connected()
        assert isinstance(connected, bool)
    
    def test_callback_registration(self):
        """Test callback registration"""
        scanner = BarcodeScanner()
        
        callback_called = False
        def test_callback(event):
            nonlocal callback_called
            callback_called = True
        
        scanner.set_callback(test_callback)
        # Callback should be registered without error


@pytest.mark.asyncio
class TestDatabase:
    """Test database functionality"""
    
    async def test_access_verification(self):
        """Test access verification"""
        verifier = AccessVerifier()
        
        # Test with mock barcode
        result = await verifier.verify_access("TEST123")
        assert isinstance(result, AccessResult)
        assert hasattr(result, 'granted')
        assert hasattr(result, 'barcode')
        assert hasattr(result, 'reason')
    
    async def test_access_result_structure(self):
        """Test access result structure"""
        result = AccessResult(
            granted=True,
            barcode="TEST123",
            user_id="user001",
            user_name="Test User",
            reason="Test access"
        )
        
        assert result.granted is True
        assert result.barcode == "TEST123"
        assert result.user_id == "user001"
        assert result.user_name == "Test User"
        assert result.reason == "Test access"


class TestIntegration:
    """Integration tests"""
    
    def test_system_components_integration(self):
        """Test that all components can be imported and initialized"""
        from src.hardware import hardware
        from src.barcode_scanner import barcode_manager
        from src.database import access_verifier
        
        # Components should be importable and have basic attributes
        assert hardware is not None
        assert barcode_manager is not None
        assert access_verifier is not None
    
    @pytest.mark.asyncio
    async def test_barcode_to_access_flow(self):
        """Test the flow from barcode scan to access decision"""
        from src.barcode_scanner import BarcodeEvent
        from src.database import access_verifier
        
        # Simulate a barcode scan event
        event = BarcodeEvent(
            barcode="TEST123",
            timestamp=datetime.now()
        )
        
        # Test verification
        result = await access_verifier.verify_access(event.barcode)
        
        # Should return a valid result
        assert isinstance(result, AccessResult)
        assert result.barcode == "TEST123"


def test_main_imports():
    """Test that main modules can be imported"""
    try:
        import src.config
        import src.hardware
        import src.barcode_scanner
        import src.database
        import src.api
        import src.logging_system
        assert True
    except ImportError as e:
        pytest.fail(f"Failed to import module: {e}")


# Test utilities
def create_test_config():
    """Create a test configuration"""
    return {
        'server': {'host': '127.0.0.1', 'port': 8001},
        'hardware': {
            'relays': {'door_control': 4},
            'inputs': {'door_sensor': 18}
        },
        'barcode_scanner': {'enabled': True, 'device': '/dev/ttyUSB0'},
        'database': {
            'local': {'path': ':memory:'},
            'remote': {'type': 'http'}
        }
    }


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
