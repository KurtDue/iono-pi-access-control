"""
Barcode scanner interface for USB/Serial barcode readers
Supports various barcode scanner types and communication protocols
"""

import asyncio
import logging
import threading
import time
from typing import Callable, Optional, Any
from dataclasses import dataclass
from datetime import datetime

try:
    import serial
    import serial.tools.list_ports
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("Warning: pyserial not available. Barcode scanner functionality disabled.")

from .config import config


@dataclass
class BarcodeEvent:
    """Represents a scanned barcode event"""
    barcode: str
    timestamp: datetime
    scanner_id: Optional[str] = None
    raw_data: Optional[str] = None


class MockSerial:
    """Mock serial interface for testing"""
    
    def __init__(self, port, baudrate, timeout=None):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.is_open = False
        self._test_barcodes = ["123456789", "TEST001", "ACCESS123"]
        self._test_index = 0
    
    def open(self):
        self.is_open = True
        print(f"Mock serial port {self.port} opened")
    
    def close(self):
        self.is_open = False
        print(f"Mock serial port {self.port} closed")
    
    def read_until(self, terminator=b'\n'):
        """Simulate reading a barcode"""
        if not self.is_open:
            return b""
        
        # Simulate occasional barcode scans
        time.sleep(5)  # Wait 5 seconds between simulated scans
        
        if self._test_index < len(self._test_barcodes):
            barcode = self._test_barcodes[self._test_index]
            self._test_index = (self._test_index + 1) % len(self._test_barcodes)
            return (barcode + "\r\n").encode()
        
        return b""
    
    def readline(self):
        return self.read_until()
    
    def write(self, data):
        pass
    
    def flush(self):
        pass


class BarcodeScanner:
    """
    Interface for USB/Serial barcode scanners
    Handles communication with various barcode scanner types
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.serial_module = serial if SERIAL_AVAILABLE else None
        self._serial_connection: Optional[Any] = None
        self._running = False
        self._reader_thread: Optional[threading.Thread] = None
        self._callback: Optional[Callable[[BarcodeEvent], None]] = None
        
        self.config = config.barcode_scanner
        self.logger.info("BarcodeScanner initialized")
    
    def set_callback(self, callback: Callable[[BarcodeEvent], None]):
        """Set callback function for barcode scan events"""
        self._callback = callback
        self.logger.debug("Barcode scan callback registered")
    
    def start(self) -> bool:
        """
        Start the barcode scanner
        
        Returns:
            True if started successfully, False otherwise
        """
        if not self.config.enabled:
            self.logger.info("Barcode scanner disabled in configuration")
            return False
        
        if self._running:
            self.logger.warning("Barcode scanner already running")
            return True
        
        try:
            self._connect()
            self._running = True
            self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
            self._reader_thread.start()
            
            self.logger.info(f"Barcode scanner started on {self.config.device}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start barcode scanner: {e}")
            return False
    
    def stop(self):
        """Stop the barcode scanner"""
        if not self._running:
            return
        
        self._running = False
        
        if self._reader_thread:
            self._reader_thread.join(timeout=5)
        
        self._disconnect()
        self.logger.info("Barcode scanner stopped")
    
    def _connect(self):
        """Establish connection to barcode scanner"""
        if not SERIAL_AVAILABLE:
            # Use mock serial for testing
            self._serial_connection = MockSerial(
                self.config.device,
                self.config.baudrate,
                self.config.timeout
            )
        else:
            # Real serial connection
            self._serial_connection = serial.Serial(
                port=self.config.device,
                baudrate=self.config.baudrate,
                timeout=self.config.timeout,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS
            )
        
        if hasattr(self._serial_connection, 'open'):
            self._serial_connection.open()
        
        self.logger.debug(f"Connected to barcode scanner at {self.config.device}")
    
    def _disconnect(self):
        """Disconnect from barcode scanner"""
        if self._serial_connection:
            try:
                self._serial_connection.close()
                self.logger.debug("Disconnected from barcode scanner")
            except Exception as e:
                self.logger.error(f"Error disconnecting from scanner: {e}")
            finally:
                self._serial_connection = None
    
    def _read_loop(self):
        """Main reading loop for barcode data"""
        self.logger.debug("Barcode reader loop started")
        
        while self._running and self._serial_connection:
            try:
                # Read data from scanner
                if SERIAL_AVAILABLE:
                    # Real serial reading
                    data = self._serial_connection.readline()
                else:
                    # Mock reading
                    data = self._serial_connection.read_until(self.config.suffix.encode())
                
                if data:
                    self._process_barcode_data(data)
                    
            except Exception as e:
                if self._running:  # Only log if we're supposed to be running
                    self.logger.error(f"Error reading from barcode scanner: {e}")
                    time.sleep(1)  # Brief pause before retrying
        
        self.logger.debug("Barcode reader loop ended")
    
    def _process_barcode_data(self, data: bytes):
        """Process raw barcode data"""
        try:
            # Decode data
            raw_string = data.decode('utf-8', errors='ignore').strip()
            
            if not raw_string:
                return
            
            # Remove configured prefix and suffix
            barcode = raw_string
            
            if self.config.prefix and barcode.startswith(self.config.prefix):
                barcode = barcode[len(self.config.prefix):]
            
            if self.config.suffix and barcode.endswith(self.config.suffix.strip()):
                barcode = barcode[:-len(self.config.suffix.strip())]
            
            # Clean up the barcode
            barcode = barcode.strip()
            
            if barcode:
                # Create barcode event
                event = BarcodeEvent(
                    barcode=barcode,
                    timestamp=datetime.now(),
                    raw_data=raw_string
                )
                
                self.logger.info(f"Barcode scanned: {barcode}")
                
                # Call callback if registered
                if self._callback:
                    try:
                        self._callback(event)
                    except Exception as e:
                        self.logger.error(f"Error in barcode callback: {e}")
        
        except Exception as e:
            self.logger.error(f"Error processing barcode data: {e}")
    
    def is_connected(self) -> bool:
        """Check if scanner is connected and running"""
        return self._running and self._serial_connection is not None
    
    def test_connection(self) -> bool:
        """Test connection to barcode scanner"""
        try:
            if not SERIAL_AVAILABLE:
                return True  # Mock connection always works
            
            # Try to open and close connection
            test_serial = serial.Serial(
                port=self.config.device,
                baudrate=self.config.baudrate,
                timeout=1
            )
            test_serial.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Scanner connection test failed: {e}")
            return False
    
    @staticmethod
    def list_available_ports():
        """List available serial ports for scanner connection"""
        if not SERIAL_AVAILABLE:
            return ["/dev/ttyUSB0", "/dev/ttyUSB1", "COM1", "COM2"]  # Mock ports
        
        ports = []
        for port in serial.tools.list_ports.comports():
            ports.append({
                'device': port.device,
                'description': port.description,
                'manufacturer': getattr(port, 'manufacturer', 'Unknown')
            })
        
        return ports
    
    def send_command(self, command: str) -> bool:
        """
        Send a command to the barcode scanner (for programmable scanners)
        
        Args:
            command: Command string to send
            
        Returns:
            True if command sent successfully
        """
        if not self._serial_connection or not self._running:
            return False
        
        try:
            command_bytes = command.encode() + b'\r\n'
            
            if hasattr(self._serial_connection, 'write'):
                self._serial_connection.write(command_bytes)
                self._serial_connection.flush()
            
            self.logger.debug(f"Sent command to scanner: {command}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error sending command to scanner: {e}")
            return False
    
    def __enter__(self):
        """Context manager entry"""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.stop()


class BarcodeManager:
    """
    High-level barcode management class
    Handles multiple scanners and barcode processing logic
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.scanner = BarcodeScanner()
        self._access_callback: Optional[Callable[[str], None]] = None
        
        # Set up scanner callback
        self.scanner.set_callback(self._on_barcode_scanned)
    
    def set_access_callback(self, callback: Callable[[str], None]):
        """Set callback for access control when barcode is scanned"""
        self._access_callback = callback
    
    def start(self) -> bool:
        """Start barcode scanning"""
        return self.scanner.start()
    
    def stop(self):
        """Stop barcode scanning"""
        self.scanner.stop()
    
    def _on_barcode_scanned(self, event: BarcodeEvent):
        """Handle barcode scan events"""
        self.logger.info(f"Processing barcode: {event.barcode}")
        
        # Validate barcode format if needed
        if self._is_valid_barcode(event.barcode):
            # Call access control callback
            if self._access_callback:
                try:
                    self._access_callback(event.barcode)
                except Exception as e:
                    self.logger.error(f"Error in access callback: {e}")
        else:
            self.logger.warning(f"Invalid barcode format: {event.barcode}")
    
    def _is_valid_barcode(self, barcode: str) -> bool:
        """Validate barcode format"""
        # Basic validation - can be customized based on your barcode format
        if not barcode or len(barcode) < 3:
            return False
        
        # Check for valid characters (alphanumeric)
        if not barcode.replace(' ', '').replace('-', '').isalnum():
            return False
        
        return True
    
    def is_running(self) -> bool:
        """Check if barcode scanning is active"""
        return self.scanner.is_connected()
    
    def get_status(self) -> dict:
        """Get barcode scanner status"""
        return {
            'enabled': config.barcode_scanner.enabled,
            'connected': self.scanner.is_connected(),
            'device': config.barcode_scanner.device,
            'running': self.scanner._running
        }


# Global barcode manager instance
barcode_manager = BarcodeManager()
