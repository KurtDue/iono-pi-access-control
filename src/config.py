"""
Configuration management for Iono Pi Access Control System
"""

import os
import yaml
from typing import Dict, Any, Optional
from pydantic import BaseSettings, Field
from pydantic_settings import SettingsConfigDict


class ServerConfig(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    cors_origins: list = ["*"]


class SecurityConfig(BaseSettings):
    secret_key: str = "your-secret-key-change-this"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    admin_username: str = "admin"
    admin_password: str = "admin123"


class HardwareConfig(BaseSettings):
    class RelayConfig(BaseSettings):
        door_control: int = 4
        auxiliary: int = 17
        spare1: int = 27
        spare2: int = 22
    
    class InputConfig(BaseSettings):
        door_sensor: int = 18
        emergency_button: int = 23
        aux_input1: int = 24
        aux_input2: int = 25
    
    class DoorConfig(BaseSettings):
        unlock_duration: int = 5
        sensor_normally_closed: bool = True
    
    relays: RelayConfig = RelayConfig()
    inputs: InputConfig = InputConfig()
    door: DoorConfig = DoorConfig()


class BarcodeScannerConfig(BaseSettings):
    enabled: bool = True
    device: str = "/dev/ttyUSB0"
    baudrate: int = 9600
    timeout: float = 1.0
    prefix: str = ""
    suffix: str = "\r\n"


class DatabaseConfig(BaseSettings):
    class LocalConfig(BaseSettings):
        path: str = "data/access_control.db"
    
    class RemoteConfig(BaseSettings):
        type: str = "http"  # "http", "postgresql", "mysql"
        
        class HttpConfig(BaseSettings):
            base_url: str = ""
            verify_endpoint: str = "/access/verify"
            auth_header: str = "Authorization"
            auth_token: str = ""
            timeout: float = 5.0
        
        http: HttpConfig = HttpConfig()
    
    local: LocalConfig = LocalConfig()
    remote: RemoteConfig = RemoteConfig()


class LoggingConfig(BaseSettings):
    level: str = "INFO"
    format: str = "json"
    
    class FileConfig(BaseSettings):
        enabled: bool = True
        path: str = "logs/access_control.log"
        max_size_mb: int = 10
        backup_count: int = 5
    
    file: FileConfig = FileConfig()


class MonitoringConfig(BaseSettings):
    health_check_interval: int = 60
    hardware_check_interval: int = 10


class Config:
    """Main configuration class for the access control system"""
    
    def __init__(self, config_file: str = "config/config.yaml"):
        self.config_file = config_file
        self._config_data = self._load_config()
        
        # Initialize configuration sections
        self.server = ServerConfig(**self._config_data.get("server", {}))
        self.security = SecurityConfig(**self._config_data.get("security", {}))
        self.hardware = HardwareConfig(**self._config_data.get("hardware", {}))
        self.barcode_scanner = BarcodeScannerConfig(**self._config_data.get("barcode_scanner", {}))
        self.database = DatabaseConfig(**self._config_data.get("database", {}))
        self.logging = LoggingConfig(**self._config_data.get("logging", {}))
        self.monitoring = MonitoringConfig(**self._config_data.get("monitoring", {}))
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_file, 'r') as file:
                return yaml.safe_load(file) or {}
        except FileNotFoundError:
            print(f"Configuration file {self.config_file} not found. Using defaults.")
            return {}
        except yaml.YAMLError as e:
            print(f"Error parsing configuration file: {e}")
            return {}
    
    def reload(self):
        """Reload configuration from file"""
        self._config_data = self._load_config()
        self.__init__(self.config_file)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dot notation key"""
        keys = key.split('.')
        value = self._config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value


# Global configuration instance
config = Config()
