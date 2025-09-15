"""
Database verification system for access control
Handles remote database verification and local caching
"""

import asyncio
import logging
import sqlite3
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path

try:
    import httpx
    import aiosqlite
    HTTP_AVAILABLE = True
except ImportError:
    HTTP_AVAILABLE = False
    print("Warning: httpx/aiosqlite not available. Database functionality limited.")

from .config import config


@dataclass
class AccessResult:
    """Result of access verification"""
    granted: bool
    barcode: str
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    reason: Optional[str] = None
    expires_at: Optional[datetime] = None
    permissions: List[str] = None
    cached: bool = False


@dataclass
class AccessLog:
    """Access attempt log entry"""
    id: Optional[int] = None
    timestamp: datetime = None
    barcode: str = ""
    granted: bool = False
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    reason: str = ""
    source: str = "barcode"  # "barcode", "api", "emergency"
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class LocalDatabase:
    """Local SQLite database for caching and logging"""
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self.logger = logging.getLogger(__name__)
        
        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        asyncio.create_task(self._init_database())
    
    async def _init_database(self):
        """Initialize database tables"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # Access cache table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS access_cache (
                        barcode TEXT PRIMARY KEY,
                        user_id TEXT,
                        user_name TEXT,
                        granted BOOLEAN,
                        permissions TEXT,
                        expires_at TIMESTAMP,
                        cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Access logs table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS access_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        barcode TEXT,
                        granted BOOLEAN,
                        user_id TEXT,
                        user_name TEXT,
                        reason TEXT,
                        source TEXT DEFAULT 'barcode'
                    )
                ''')
                
                # System events table
                await db.execute('''
                    CREATE TABLE IF NOT EXISTS system_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        event_type TEXT,
                        message TEXT,
                        details TEXT
                    )
                ''')
                
                await db.commit()
                self.logger.info("Local database initialized")
        
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
    
    async def cache_access_result(self, result: AccessResult):
        """Cache access verification result"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT OR REPLACE INTO access_cache 
                    (barcode, user_id, user_name, granted, permissions, expires_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    result.barcode,
                    result.user_id,
                    result.user_name,
                    result.granted,
                    json.dumps(result.permissions or []),
                    result.expires_at
                ))
                await db.commit()
        
        except Exception as e:
            self.logger.error(f"Failed to cache access result: {e}")
    
    async def get_cached_access(self, barcode: str) -> Optional[AccessResult]:
        """Get cached access result"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('''
                    SELECT barcode, user_id, user_name, granted, permissions, expires_at, cached_at
                    FROM access_cache WHERE barcode = ?
                ''', (barcode,)) as cursor:
                    row = await cursor.fetchone()
                    
                    if row:
                        # Check if cache entry is still valid
                        cached_at = datetime.fromisoformat(row[6])
                        cache_age = datetime.now() - cached_at
                        
                        # Cache valid for 1 hour
                        if cache_age < timedelta(hours=1):
                            permissions = json.loads(row[4]) if row[4] else []
                            expires_at = datetime.fromisoformat(row[5]) if row[5] else None
                            
                            return AccessResult(
                                barcode=row[0],
                                user_id=row[1],
                                user_name=row[2],
                                granted=row[3],
                                permissions=permissions,
                                expires_at=expires_at,
                                cached=True
                            )
        
        except Exception as e:
            self.logger.error(f"Failed to get cached access: {e}")
        
        return None
    
    async def log_access_attempt(self, log_entry: AccessLog):
        """Log access attempt"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO access_logs 
                    (timestamp, barcode, granted, user_id, user_name, reason, source)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    log_entry.timestamp,
                    log_entry.barcode,
                    log_entry.granted,
                    log_entry.user_id,
                    log_entry.user_name,
                    log_entry.reason,
                    log_entry.source
                ))
                await db.commit()
        
        except Exception as e:
            self.logger.error(f"Failed to log access attempt: {e}")
    
    async def get_access_logs(self, limit: int = 100, offset: int = 0) -> List[AccessLog]:
        """Get access logs"""
        logs = []
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('''
                    SELECT id, timestamp, barcode, granted, user_id, user_name, reason, source
                    FROM access_logs ORDER BY timestamp DESC LIMIT ? OFFSET ?
                ''', (limit, offset)) as cursor:
                    async for row in cursor:
                        logs.append(AccessLog(
                            id=row[0],
                            timestamp=datetime.fromisoformat(row[1]),
                            barcode=row[2],
                            granted=row[3],
                            user_id=row[4],
                            user_name=row[5],
                            reason=row[6],
                            source=row[7]
                        ))
        
        except Exception as e:
            self.logger.error(f"Failed to get access logs: {e}")
        
        return logs
    
    async def cleanup_old_cache(self, max_age_hours: int = 24):
        """Clean up old cache entries"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    DELETE FROM access_cache WHERE cached_at < ?
                ''', (cutoff_time,))
                await db.commit()
        
        except Exception as e:
            self.logger.error(f"Failed to cleanup cache: {e}")


class RemoteVerifier:
    """Remote database verification via HTTP API"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = config.database.remote
        self._client: Optional[Any] = None
    
    async def _get_client(self):
        """Get HTTP client instance"""
        if not HTTP_AVAILABLE:
            return None
        
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.config.http.timeout,
                verify=True
            )
        return self._client
    
    async def verify_barcode(self, barcode: str) -> Optional[AccessResult]:
        """Verify barcode against remote database"""
        if self.config.type != "http" or not self.config.http.base_url:
            return None
        
        client = await self._get_client()
        if not client:
            return None
        
        try:
            url = f"{self.config.http.base_url}{self.config.http.verify_endpoint}"
            headers = {}
            
            if self.config.http.auth_token:
                headers[self.config.http.auth_header] = self.config.http.auth_token
            
            # Prepare request data
            request_data = {
                "barcode": barcode,
                "timestamp": datetime.now().isoformat(),
                "device_id": "iono-pi-access-control"
            }
            
            response = await client.post(
                url,
                json=request_data,
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Parse response based on expected format
                return self._parse_verification_response(barcode, data)
            
            elif response.status_code == 404:
                # Barcode not found
                return AccessResult(
                    granted=False,
                    barcode=barcode,
                    reason="Barcode not found in database"
                )
            
            else:
                self.logger.warning(f"Remote verification failed: {response.status_code}")
                return None
        
        except Exception as e:
            self.logger.error(f"Remote verification error: {e}")
            return None
    
    def _parse_verification_response(self, barcode: str, data: Dict[str, Any]) -> AccessResult:
        """Parse verification response from remote API"""
        try:
            granted = data.get("access_granted", False)
            user_id = data.get("user_id")
            user_name = data.get("user_name", data.get("name"))
            reason = data.get("reason", "Access granted" if granted else "Access denied")
            permissions = data.get("permissions", [])
            
            # Parse expiration if provided
            expires_at = None
            if "expires_at" in data:
                try:
                    expires_at = datetime.fromisoformat(data["expires_at"])
                except:
                    pass
            
            return AccessResult(
                granted=granted,
                barcode=barcode,
                user_id=user_id,
                user_name=user_name,
                reason=reason,
                permissions=permissions,
                expires_at=expires_at
            )
        
        except Exception as e:
            self.logger.error(f"Failed to parse verification response: {e}")
            return AccessResult(
                granted=False,
                barcode=barcode,
                reason="Invalid response format"
            )
    
    async def close(self):
        """Close HTTP client"""
        if self._client:
            await self._client.aclose()
            self._client = None


class AccessVerifier:
    """Main access verification system"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.local_db = LocalDatabase(config.database.local.path)
        self.remote_verifier = RemoteVerifier()
        
        # Start cleanup task
        asyncio.create_task(self._periodic_cleanup())
    
    async def verify_access(self, barcode: str, source: str = "barcode") -> AccessResult:
        """
        Verify access for a barcode
        
        Args:
            barcode: Barcode to verify
            source: Source of the request ("barcode", "api", "emergency")
            
        Returns:
            AccessResult with verification details
        """
        try:
            # First, check local cache
            cached_result = await self.local_db.get_cached_access(barcode)
            if cached_result:
                self.logger.debug(f"Using cached access result for {barcode}")
                result = cached_result
            else:
                # Check remote database
                result = await self.remote_verifier.verify_barcode(barcode)
                
                if result:
                    # Cache the result
                    await self.local_db.cache_access_result(result)
                else:
                    # Fallback - deny access if remote verification fails
                    result = AccessResult(
                        granted=False,
                        barcode=barcode,
                        reason="Remote verification unavailable"
                    )
            
            # Log the access attempt
            log_entry = AccessLog(
                barcode=barcode,
                granted=result.granted,
                user_id=result.user_id,
                user_name=result.user_name,
                reason=result.reason or ("Access granted" if result.granted else "Access denied"),
                source=source
            )
            await self.local_db.log_access_attempt(log_entry)
            
            self.logger.info(
                f"Access {'granted' if result.granted else 'denied'} for barcode {barcode}: {result.reason}"
            )
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error verifying access for {barcode}: {e}")
            
            # Return denied access on error
            result = AccessResult(
                granted=False,
                barcode=barcode,
                reason="Verification error"
            )
            
            # Still try to log the attempt
            try:
                log_entry = AccessLog(
                    barcode=barcode,
                    granted=False,
                    reason=f"Verification error: {str(e)}",
                    source=source
                )
                await self.local_db.log_access_attempt(log_entry)
            except:
                pass
            
            return result
    
    async def get_access_logs(self, limit: int = 100, offset: int = 0) -> List[AccessLog]:
        """Get access logs"""
        return await self.local_db.get_access_logs(limit, offset)
    
    async def _periodic_cleanup(self):
        """Periodic cleanup of old cache entries"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                await self.local_db.cleanup_old_cache()
                self.logger.debug("Performed cache cleanup")
            except Exception as e:
                self.logger.error(f"Error in periodic cleanup: {e}")
    
    async def close(self):
        """Clean up resources"""
        await self.remote_verifier.close()


# Global access verifier instance
access_verifier = AccessVerifier()
