"""
Main application entry point for Iono Pi Access Control System
"""

import asyncio
import signal
import sys
import os
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    import uvicorn
    UVICORN_AVAILABLE = True
except ImportError:
    UVICORN_AVAILABLE = False

from src.config import config
from src.logging_system import setup_logging, get_logger, system_monitor
from src.hardware import hardware
from src.barcode_scanner import barcode_manager
from src.database import access_verifier
from src.api import app


class AccessControlSystem:
    """Main access control system coordinator"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        self._running = False
        self._shutdown_event = asyncio.Event()
    
    async def start(self):
        """Start the access control system"""
        if self._running:
            return
        
        self.logger.info("Starting Iono Pi Access Control System")
        
        try:
            # Start hardware monitoring
            hardware.start_monitoring()
            self.logger.info("Hardware monitoring started")
            
            # Start barcode scanner
            if barcode_manager.start():
                self.logger.info("Barcode scanner started")
            else:
                self.logger.warning("Barcode scanner failed to start")
            
            # Set up barcode callback for access control
            def handle_barcode_access(barcode: str):
                """Handle barcode scan for access control"""
                asyncio.create_task(self._process_barcode_access(barcode))
            
            barcode_manager.set_access_callback(handle_barcode_access)
            
            # Start system monitoring
            await system_monitor.start_monitoring()
            self.logger.info("System monitoring started")
            
            self._running = True
            self.logger.info("Access control system started successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to start access control system: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """Stop the access control system"""
        if not self._running:
            return
        
        self.logger.info("Stopping access control system")
        
        try:
            # Stop monitoring
            await system_monitor.stop_monitoring()
            
            # Stop barcode scanner
            barcode_manager.stop()
            
            # Stop hardware
            hardware.cleanup()
            
            # Close database connections
            await access_verifier.close()
            
            self._running = False
            self._shutdown_event.set()
            
            self.logger.info("Access control system stopped")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")
    
    async def _process_barcode_access(self, barcode: str):
        """Process barcode access request"""
        try:
            self.logger.info(f"Processing barcode access: {barcode}")
            
            # Verify access
            result = await access_verifier.verify_access(barcode, source="barcode")
            
            if result.granted:
                # Open the door
                hardware.open_door()
                self.logger.info(f"Access granted for {barcode}: {result.reason}")
            else:
                self.logger.warning(f"Access denied for {barcode}: {result.reason}")
        
        except Exception as e:
            self.logger.error(f"Error processing barcode access: {e}")
    
    async def wait_for_shutdown(self):
        """Wait for shutdown signal"""
        await self._shutdown_event.wait()
    
    def is_running(self) -> bool:
        """Check if system is running"""
        return self._running


async def main():
    """Main application entry point"""
    # Setup logging first
    setup_logging()
    logger = get_logger(__name__)
    
    logger.info("Initializing Iono Pi Access Control System")
    
    # Create system instance
    system = AccessControlSystem()
    
    # Setup signal handlers
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}")
        asyncio.create_task(system.stop())
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Start the system
        await system.start()
        
        # Start the web API if available
        if app and UVICORN_AVAILABLE:
            logger.info("Starting web API server")
            
            # Create uvicorn server
            server_config = uvicorn.Config(
                app,
                host=config.server.host,
                port=config.server.port,
                log_level="info",
                access_log=True
            )
            server = uvicorn.Server(server_config)
            
            # Run server in background
            server_task = asyncio.create_task(server.serve())
            
            try:
                # Wait for shutdown signal
                await system.wait_for_shutdown()
            finally:
                # Stop the server
                server.should_exit = True
                await server_task
        else:
            logger.warning("Web API not available, running in standalone mode")
            
            # Just wait for shutdown
            await system.wait_for_shutdown()
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        await system.stop()
        logger.info("Application shutdown complete")


def run_standalone():
    """Run system without web API"""
    import time
    
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    logger.info("Starting Iono Pi Access Control System (Standalone Mode)")
    
    try:
        # Start hardware
        hardware.start_monitoring()
        logger.info("Hardware monitoring started")
        
        # Start barcode scanner
        if barcode_manager.start():
            logger.info("Barcode scanner started")
            
            # Set up simple barcode callback
            def handle_barcode(barcode: str):
                logger.info(f"Barcode scanned: {barcode}")
                # In standalone mode, just open the door for any barcode
                # In production, you'd want proper verification
                hardware.open_door()
                logger.info("Door opened")
            
            barcode_manager.set_access_callback(handle_barcode)
        
        logger.info("System running. Press Ctrl+C to stop.")
        
        # Keep running until interrupted
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        # Cleanup
        barcode_manager.stop()
        hardware.cleanup()
        logger.info("Standalone mode shutdown complete")


if __name__ == "__main__":
    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--standalone":
        # Run in standalone mode without async
        run_standalone()
    else:
        # Run full async application
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            print("\nShutdown requested by user")
        except Exception as e:
            print(f"Fatal error: {e}")
            sys.exit(1)
