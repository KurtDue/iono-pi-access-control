"""
Logging and monitoring system for Iono Pi access control
Provides structured logging, audit trails, and system monitoring
"""

import logging
import logging.handlers
import json
import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    STRUCTLOG_AVAILABLE = False
    print("Warning: structlog not available. Using standard logging.")

from .config import config


@dataclass
class SystemEvent:
    """System event for monitoring"""
    timestamp: datetime
    event_type: str
    component: str
    message: str
    level: str
    details: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = asdict(self)
        data['timestamp'] = self.timestamp.isoformat()
        return data


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_entry = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_entry.update(record.extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


class AccessControlLogger:
    """Custom logger for access control system"""
    
    def __init__(self):
        self.config = config.logging
        self._setup_logging()
        self.logger = logging.getLogger('access_control')
        
        # System events buffer for monitoring
        self._events_buffer = []
        self._max_buffer_size = 1000
    
    def _setup_logging(self):
        """Setup logging configuration"""
        # Create logs directory
        if self.config.file.enabled:
            log_path = Path(self.config.file.path)
            log_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, self.config.level))
        
        # Clear existing handlers
        root_logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler()
        
        if self.config.format == "json":
            console_formatter = JSONFormatter()
        else:
            console_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # File handler with rotation
        if self.config.file.enabled:
            file_handler = logging.handlers.RotatingFileHandler(
                self.config.file.path,
                maxBytes=self.config.file.max_size_mb * 1024 * 1024,
                backupCount=self.config.file.backup_count
            )
            file_handler.setFormatter(console_formatter)
            root_logger.addHandler(file_handler)
    
    def log_access_event(self, barcode: str, granted: bool, user_id: str = None, 
                        reason: str = None, source: str = "barcode"):
        """Log access control event"""
        event_data = {
            'barcode': barcode,
            'granted': granted,
            'user_id': user_id,
            'reason': reason,
            'source': source
        }
        
        level = "INFO" if granted else "WARNING"
        message = f"Access {'granted' if granted else 'denied'} for barcode {barcode}"
        
        self._log_event("ACCESS", "access_control", message, level, event_data)
    
    def log_hardware_event(self, component: str, action: str, details: Dict[str, Any] = None):
        """Log hardware event"""
        message = f"Hardware {component}: {action}"
        self._log_event("HARDWARE", component, message, "INFO", details)
    
    def log_system_event(self, component: str, message: str, level: str = "INFO", 
                        details: Dict[str, Any] = None):
        """Log general system event"""
        self._log_event("SYSTEM", component, message, level, details)
    
    def log_security_event(self, event_type: str, message: str, details: Dict[str, Any] = None):
        """Log security-related event"""
        self._log_event("SECURITY", "security", message, "WARNING", details)
    
    def log_error(self, component: str, error: Exception, context: str = None):
        """Log error with context"""
        message = f"Error in {component}: {str(error)}"
        if context:
            message += f" (Context: {context})"
        
        details = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context
        }
        
        self._log_event("ERROR", component, message, "ERROR", details)
    
    def _log_event(self, event_type: str, component: str, message: str, 
                   level: str, details: Dict[str, Any] = None):
        """Internal method to log events"""
        # Create system event
        event = SystemEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            component=component,
            message=message,
            level=level,
            details=details
        )
        
        # Add to buffer
        self._events_buffer.append(event)
        if len(self._events_buffer) > self._max_buffer_size:
            self._events_buffer.pop(0)
        
        # Log using standard logger
        log_level = getattr(logging, level)
        
        # Create log record with extra fields
        record_dict = {
            'extra_fields': {
                'event_type': event_type,
                'component': component,
                'details': details or {}
            }
        }
        
        self.logger.log(log_level, message, extra=record_dict)
    
    def get_recent_events(self, limit: int = 100, event_type: str = None) -> list:
        """Get recent system events"""
        events = self._events_buffer[-limit:] if not event_type else [
            e for e in self._events_buffer[-limit:] if e.event_type == event_type
        ]
        return [event.to_dict() for event in events]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get logging statistics"""
        if not self._events_buffer:
            return {}
        
        # Count events by type and level
        type_counts = {}
        level_counts = {}
        
        for event in self._events_buffer:
            type_counts[event.event_type] = type_counts.get(event.event_type, 0) + 1
            level_counts[event.level] = level_counts.get(event.level, 0) + 1
        
        return {
            'total_events': len(self._events_buffer),
            'events_by_type': type_counts,
            'events_by_level': level_counts,
            'buffer_size': self._max_buffer_size
        }


class SystemMonitor:
    """System monitoring and health checks"""
    
    def __init__(self, logger: AccessControlLogger):
        self.logger = logger
        self.monitoring_config = config.monitoring
        self._running = False
        self._monitor_task = None
        
        # Health check results
        self._health_status = {
            'overall': 'unknown',
            'components': {},
            'last_check': None
        }
    
    async def start_monitoring(self):
        """Start system monitoring"""
        if self._running:
            return
        
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitoring_loop())
        self.logger.log_system_event("monitor", "System monitoring started")
    
    async def stop_monitoring(self):
        """Stop system monitoring"""
        if not self._running:
            return
        
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        self.logger.log_system_event("monitor", "System monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self._running:
            try:
                await self._perform_health_check()
                await asyncio.sleep(self.monitoring_config.health_check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.log_error("monitor", e, "Health check loop")
                await asyncio.sleep(10)  # Brief pause on error
    
    async def _perform_health_check(self):
        """Perform comprehensive health check"""
        try:
            from .hardware import hardware
            from .barcode_scanner import barcode_manager
            
            health_status = {
                'overall': 'healthy',
                'components': {},
                'last_check': datetime.now()
            }
            
            # Check hardware
            try:
                hw_status = hardware.get_status()
                if hw_status.system_ready:
                    health_status['components']['hardware'] = 'healthy'
                else:
                    health_status['components']['hardware'] = 'unhealthy'
                    health_status['overall'] = 'degraded'
            except Exception as e:
                health_status['components']['hardware'] = 'error'
                health_status['overall'] = 'unhealthy'
                self.logger.log_error("hardware", e, "Health check")
            
            # Check barcode scanner
            try:
                if barcode_manager.is_running():
                    health_status['components']['scanner'] = 'healthy'
                else:
                    health_status['components']['scanner'] = 'stopped'
                    health_status['overall'] = 'degraded'
            except Exception as e:
                health_status['components']['scanner'] = 'error'
                health_status['overall'] = 'degraded'
                self.logger.log_error("scanner", e, "Health check")
            
            # Check database connectivity
            try:
                # Simple database check would go here
                health_status['components']['database'] = 'healthy'
            except Exception as e:
                health_status['components']['database'] = 'error'
                health_status['overall'] = 'degraded'
                self.logger.log_error("database", e, "Health check")
            
            # Check disk space
            try:
                disk_usage = self._check_disk_space()
                if disk_usage > 90:
                    health_status['components']['disk'] = 'warning'
                    health_status['overall'] = 'degraded'
                    self.logger.log_system_event(
                        "system", 
                        f"Low disk space: {disk_usage}%", 
                        "WARNING"
                    )
                else:
                    health_status['components']['disk'] = 'healthy'
            except Exception as e:
                health_status['components']['disk'] = 'error'
                self.logger.log_error("system", e, "Disk space check")
            
            # Update health status
            self._health_status = health_status
            
            # Log health status changes
            if health_status['overall'] != 'healthy':
                self.logger.log_system_event(
                    "monitor", 
                    f"System health: {health_status['overall']}", 
                    "WARNING", 
                    health_status['components']
                )
        
        except Exception as e:
            self.logger.log_error("monitor", e, "Health check")
    
    def _check_disk_space(self) -> float:
        """Check disk space usage percentage"""
        try:
            statvfs = os.statvfs('/')
            total = statvfs.f_frsize * statvfs.f_blocks
            available = statvfs.f_frsize * statvfs.f_available
            used = total - available
            return (used / total) * 100
        except:
            return 0.0
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get current health status"""
        return self._health_status.copy()
    
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system metrics"""
        try:
            import psutil
            
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Load average (Linux/Unix)
            try:
                load_avg = os.getloadavg()
            except:
                load_avg = [0, 0, 0]
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_mb': memory.available // (1024 * 1024),
                'load_average': load_avg,
                'disk_usage_percent': self._check_disk_space()
            }
        except ImportError:
            return {
                'cpu_percent': 0,
                'memory_percent': 0,
                'memory_available_mb': 0,
                'load_average': [0, 0, 0],
                'disk_usage_percent': 0
            }


# Global instances
access_logger = AccessControlLogger()
system_monitor = SystemMonitor(access_logger)


def setup_logging():
    """Setup logging for the entire application"""
    access_logger._setup_logging()


def get_logger(name: str = None) -> logging.Logger:
    """Get logger instance"""
    return logging.getLogger(name or 'access_control')


# Export commonly used functions
def log_access(barcode: str, granted: bool, **kwargs):
    """Log access event"""
    access_logger.log_access_event(barcode, granted, **kwargs)


def log_hardware(component: str, action: str, **kwargs):
    """Log hardware event"""
    access_logger.log_hardware_event(component, action, **kwargs)


def log_error(component: str, error: Exception, context: str = None):
    """Log error"""
    access_logger.log_error(component, error, context)
