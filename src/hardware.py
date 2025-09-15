"""
Hardware interface for Iono Pi RTC
Provides control for relays, digital inputs/outputs, and hardware monitoring
"""

import time
import threading
import logging
from typing import Dict, Callable, Optional, Any
from dataclasses import dataclass
from datetime import datetime

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    print("Warning: RPi.GPIO not available. Running in simulation mode.")

from .config import config


@dataclass
class HardwareStatus:
    """Status information for hardware components"""
    relays: Dict[str, bool]
    inputs: Dict[str, bool]
    last_update: datetime
    system_ready: bool


class MockGPIO:
    """Mock GPIO class for development/testing on non-Raspberry Pi systems"""
    
    BCM = "BCM"
    OUT = "OUT"
    IN = "IN"
    PUD_UP = "PUD_UP"
    PUD_DOWN = "PUD_DOWN"
    HIGH = 1
    LOW = 0
    RISING = "RISING"
    FALLING = "FALLING"
    BOTH = "BOTH"
    
    _pin_states = {}
    _pin_modes = {}
    _callbacks = {}
    
    @classmethod
    def setmode(cls, mode):
        pass
    
    @classmethod
    def setup(cls, pin, mode, pull_up_down=None):
        cls._pin_modes[pin] = mode
        if mode == cls.OUT:
            cls._pin_states[pin] = cls.LOW
    
    @classmethod
    def output(cls, pin, state):
        cls._pin_states[pin] = state
        print(f"Mock GPIO: Pin {pin} set to {state}")
    
    @classmethod
    def input(cls, pin):
        return cls._pin_states.get(pin, cls.LOW)
    
    @classmethod
    def add_event_detect(cls, pin, edge, callback=None, bouncetime=None):
        if callback:
            cls._callbacks[pin] = callback
    
    @classmethod
    def cleanup(cls):
        cls._pin_states.clear()
        cls._pin_modes.clear()
        cls._callbacks.clear()


class IonoHardware:
    """
    Hardware interface for Iono Pi RTC
    Manages relays, digital inputs, and hardware monitoring
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.gpio = GPIO if GPIO_AVAILABLE else MockGPIO
        self._running = False
        self._monitor_thread = None
        self._input_callbacks: Dict[str, Callable] = {}
        self._last_input_states: Dict[str, bool] = {}
        
        # Initialize hardware
        self._setup_gpio()
        self._status = HardwareStatus(
            relays={},
            inputs={},
            last_update=datetime.now(),
            system_ready=False
        )
        
        self.logger.info("IonoHardware initialized")
    
    def _setup_gpio(self):
        """Initialize GPIO pins for Iono Pi"""
        try:
            self.gpio.setmode(self.gpio.BCM)
            
            # Setup relay outputs
            relay_pins = [
                config.hardware.relays.door_control,
                config.hardware.relays.auxiliary,
                config.hardware.relays.spare1,
                config.hardware.relays.spare2
            ]
            
            for pin in relay_pins:
                self.gpio.setup(pin, self.gpio.OUT)
                self.gpio.output(pin, self.gpio.LOW)  # Relays off by default
            
            # Setup digital inputs
            input_pins = [
                config.hardware.inputs.door_sensor,
                config.hardware.inputs.emergency_button,
                config.hardware.inputs.aux_input1,
                config.hardware.inputs.aux_input2
            ]
            
            for pin in input_pins:
                self.gpio.setup(pin, self.gpio.IN, pull_up_down=self.gpio.PUD_UP)
                # Add event detection for input changes
                self.gpio.add_event_detect(
                    pin, 
                    self.gpio.BOTH, 
                    callback=self._input_callback,
                    bouncetime=200
                )
            
            self.logger.info("GPIO pins configured successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to setup GPIO: {e}")
            raise
    
    def start_monitoring(self):
        """Start hardware monitoring thread"""
        if not self._running:
            self._running = True
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
            self.logger.info("Hardware monitoring started")
    
    def stop_monitoring(self):
        """Stop hardware monitoring"""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5)
        self.logger.info("Hardware monitoring stopped")
    
    def _monitor_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                self._update_status()
                time.sleep(config.monitoring.hardware_check_interval)
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}")
                time.sleep(1)
    
    def _update_status(self):
        """Update hardware status"""
        # Read all input states
        inputs = {
            'door_sensor': self.read_input('door_sensor'),
            'emergency_button': self.read_input('emergency_button'),
            'aux_input1': self.read_input('aux_input1'),
            'aux_input2': self.read_input('aux_input2')
        }
        
        # Read all relay states
        relays = {
            'door_control': self.get_relay_state('door_control'),
            'auxiliary': self.get_relay_state('auxiliary'),
            'spare1': self.get_relay_state('spare1'),
            'spare2': self.get_relay_state('spare2')
        }
        
        # Update status
        self._status.inputs = inputs
        self._status.relays = relays
        self._status.last_update = datetime.now()
        self._status.system_ready = True
    
    def _input_callback(self, pin):
        """Callback for GPIO input changes"""
        try:
            state = self.gpio.input(pin)
            pin_name = self._get_pin_name(pin)
            
            if pin_name and pin_name in self._input_callbacks:
                self._input_callbacks[pin_name](pin_name, state)
                
            self.logger.debug(f"Input {pin_name} ({pin}) changed to {state}")
            
        except Exception as e:
            self.logger.error(f"Error in input callback: {e}")
    
    def _get_pin_name(self, pin: int) -> Optional[str]:
        """Get input name from pin number"""
        pin_map = {
            config.hardware.inputs.door_sensor: 'door_sensor',
            config.hardware.inputs.emergency_button: 'emergency_button',
            config.hardware.inputs.aux_input1: 'aux_input1',
            config.hardware.inputs.aux_input2: 'aux_input2'
        }
        return pin_map.get(pin)
    
    def set_relay(self, relay_name: str, state: bool, duration: Optional[float] = None):
        """
        Control a relay output
        
        Args:
            relay_name: Name of relay ('door_control', 'auxiliary', 'spare1', 'spare2')
            state: True to activate, False to deactivate
            duration: If specified, relay will be deactivated after this many seconds
        """
        pin_map = {
            'door_control': config.hardware.relays.door_control,
            'auxiliary': config.hardware.relays.auxiliary,
            'spare1': config.hardware.relays.spare1,
            'spare2': config.hardware.relays.spare2
        }
        
        if relay_name not in pin_map:
            raise ValueError(f"Unknown relay: {relay_name}")
        
        pin = pin_map[relay_name]
        gpio_state = self.gpio.HIGH if state else self.gpio.LOW
        
        try:
            self.gpio.output(pin, gpio_state)
            self.logger.info(f"Relay {relay_name} set to {state}")
            
            # If duration specified, schedule deactivation
            if duration and state:
                def deactivate():
                    time.sleep(duration)
                    self.gpio.output(pin, self.gpio.LOW)
                    self.logger.info(f"Relay {relay_name} auto-deactivated after {duration}s")
                
                threading.Thread(target=deactivate, daemon=True).start()
                
        except Exception as e:
            self.logger.error(f"Failed to set relay {relay_name}: {e}")
            raise
    
    def get_relay_state(self, relay_name: str) -> bool:
        """Get current state of a relay"""
        pin_map = {
            'door_control': config.hardware.relays.door_control,
            'auxiliary': config.hardware.relays.auxiliary,
            'spare1': config.hardware.relays.spare1,
            'spare2': config.hardware.relays.spare2
        }
        
        if relay_name not in pin_map:
            return False
        
        # Note: We can't actually read relay state from GPIO output pins
        # In a real implementation, you might track state internally
        return False
    
    def read_input(self, input_name: str) -> bool:
        """
        Read a digital input
        
        Args:
            input_name: Name of input ('door_sensor', 'emergency_button', 'aux_input1', 'aux_input2')
            
        Returns:
            Current state of the input
        """
        pin_map = {
            'door_sensor': config.hardware.inputs.door_sensor,
            'emergency_button': config.hardware.inputs.emergency_button,
            'aux_input1': config.hardware.inputs.aux_input1,
            'aux_input2': config.hardware.inputs.aux_input2
        }
        
        if input_name not in pin_map:
            raise ValueError(f"Unknown input: {input_name}")
        
        pin = pin_map[input_name]
        
        try:
            state = self.gpio.input(pin)
            return bool(state)
        except Exception as e:
            self.logger.error(f"Failed to read input {input_name}: {e}")
            return False
    
    def register_input_callback(self, input_name: str, callback: Callable[[str, bool], None]):
        """Register a callback for input state changes"""
        self._input_callbacks[input_name] = callback
        self.logger.debug(f"Registered callback for input {input_name}")
    
    def unregister_input_callback(self, input_name: str):
        """Unregister input callback"""
        if input_name in self._input_callbacks:
            del self._input_callbacks[input_name]
            self.logger.debug(f"Unregistered callback for input {input_name}")
    
    def get_status(self) -> HardwareStatus:
        """Get current hardware status"""
        return self._status
    
    def open_door(self, duration: Optional[float] = None):
        """
        Open the door using the door control relay
        
        Args:
            duration: How long to keep door unlocked (uses config default if None)
        """
        unlock_duration = duration or config.hardware.door.unlock_duration
        
        self.logger.info(f"Opening door for {unlock_duration} seconds")
        self.set_relay('door_control', True, unlock_duration)
    
    def is_door_open(self) -> bool:
        """
        Check if door is open based on door sensor
        
        Returns:
            True if door is open, False if closed
        """
        sensor_state = self.read_input('door_sensor')
        
        # Interpret sensor state based on normally closed/open configuration
        if config.hardware.door.sensor_normally_closed:
            return not sensor_state  # Door open when sensor circuit is broken
        else:
            return sensor_state  # Door open when sensor is active
    
    def emergency_override_active(self) -> bool:
        """Check if emergency override button is pressed"""
        return not self.read_input('emergency_button')  # Assuming button pulls low when pressed
    
    def cleanup(self):
        """Clean up GPIO resources"""
        self.stop_monitoring()
        try:
            self.gpio.cleanup()
            self.logger.info("GPIO cleanup completed")
        except Exception as e:
            self.logger.error(f"Error during GPIO cleanup: {e}")
    
    def __enter__(self):
        """Context manager entry"""
        self.start_monitoring()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()


# Global hardware instance
hardware = IonoHardware()
