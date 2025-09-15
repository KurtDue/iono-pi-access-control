"""
FastAPI web service for Iono Pi access control system
Provides REST API endpoints for remote access control
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

try:
    from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks
    from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel, Field
    from jose import JWTError, jwt
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    print("Warning: FastAPI dependencies not available. API functionality disabled.")

from .config import config
from .hardware import hardware
from .database import access_verifier, AccessLog
from .barcode_scanner import barcode_manager


# Pydantic models for API
class AccessRequest(BaseModel):
    """Request to open door via API"""
    reason: str = Field(..., description="Reason for access")
    duration: Optional[float] = Field(None, description="Override unlock duration in seconds")
    user_id: Optional[str] = Field(None, description="User ID for logging")


class BarcodeVerifyRequest(BaseModel):
    """Request to verify a barcode"""
    barcode: str = Field(..., description="Barcode to verify")


class SystemStatus(BaseModel):
    """System status response"""
    hardware: Dict[str, Any]
    scanner: Dict[str, Any]
    database: Dict[str, Any]
    uptime: str
    timestamp: datetime


class AccessLogResponse(BaseModel):
    """Access log entry response"""
    id: Optional[int]
    timestamp: datetime
    barcode: str
    granted: bool
    user_id: Optional[str]
    user_name: Optional[str]
    reason: str
    source: str


class TokenResponse(BaseModel):
    """Authentication token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AccessResponse(BaseModel):
    """Access control response"""
    success: bool
    message: str
    timestamp: datetime


# Security
security = HTTPBearer()


class AuthenticationError(Exception):
    """Authentication error"""
    pass


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    if not FASTAPI_AVAILABLE:
        return None
    
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=config.security.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, config.security.secret_key, algorithm=config.security.algorithm)
    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    if not FASTAPI_AVAILABLE:
        raise HTTPException(status_code=500, detail="API not available")
    
    try:
        payload = jwt.decode(
            credentials.credentials, 
            config.security.secret_key, 
            algorithms=[config.security.algorithm]
        )
        username: str = payload.get("sub")
        if username is None:
            raise AuthenticationError("Invalid token")
        return username
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    if not FASTAPI_AVAILABLE:
        return None
    
    app = FastAPI(
        title="Iono Pi Access Control API",
        description="REST API for controlling access system on Iono Pi",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.server.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Store startup time for uptime calculation
    startup_time = datetime.now()
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize services on startup"""
        logger = logging.getLogger(__name__)
        logger.info("Starting Iono Pi Access Control API")
        
        # Start hardware monitoring
        hardware.start_monitoring()
        
        # Start barcode scanner
        barcode_manager.start()
        
        # Set up barcode callback for access control
        async def handle_barcode_access(barcode: str):
            """Handle barcode scan for access control"""
            try:
                result = await access_verifier.verify_access(barcode, source="barcode")
                if result.granted:
                    hardware.open_door()
                    logger.info(f"Door opened for barcode {barcode}")
                else:
                    logger.info(f"Access denied for barcode {barcode}: {result.reason}")
            except Exception as e:
                logger.error(f"Error processing barcode access: {e}")
        
        barcode_manager.set_access_callback(handle_barcode_access)
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Clean up on shutdown"""
        logger = logging.getLogger(__name__)
        logger.info("Shutting down Iono Pi Access Control API")
        
        hardware.cleanup()
        barcode_manager.stop()
        await access_verifier.close()
    
    # Authentication endpoint
    @app.post("/auth/token", response_model=TokenResponse)
    async def login(username: str, password: str):
        """Authenticate and get access token"""
        if username != config.security.admin_username or password != config.security.admin_password:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        access_token_expires = timedelta(minutes=config.security.access_token_expire_minutes)
        access_token = create_access_token(
            data={"sub": username}, expires_delta=access_token_expires
        )
        
        return TokenResponse(
            access_token=access_token,
            expires_in=config.security.access_token_expire_minutes * 60
        )
    
    # Access control endpoints
    @app.post("/access/open", response_model=AccessResponse)
    async def open_door(
        request: AccessRequest,
        background_tasks: BackgroundTasks,
        current_user: str = Depends(verify_token)
    ):
        """Open the door via API"""
        try:
            # Log the API access
            background_tasks.add_task(
                log_api_access,
                barcode="API",
                granted=True,
                user_id=request.user_id or current_user,
                reason=request.reason,
                source="api"
            )
            
            # Open the door
            hardware.open_door(duration=request.duration)
            
            return AccessResponse(
                success=True,
                message=f"Door opened: {request.reason}",
                timestamp=datetime.now()
            )
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to open door: {str(e)}")
    
    @app.post("/access/verify", response_model=Dict[str, Any])
    async def verify_barcode(
        request: BarcodeVerifyRequest,
        current_user: str = Depends(verify_token)
    ):
        """Verify a barcode without opening the door"""
        try:
            result = await access_verifier.verify_access(request.barcode, source="api")
            
            return {
                "barcode": result.barcode,
                "granted": result.granted,
                "user_id": result.user_id,
                "user_name": result.user_name,
                "reason": result.reason,
                "cached": result.cached,
                "timestamp": datetime.now()
            }
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")
    
    # Status and monitoring endpoints
    @app.get("/status", response_model=SystemStatus)
    async def get_status(current_user: str = Depends(verify_token)):
        """Get system status"""
        uptime = datetime.now() - startup_time
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds
        
        return SystemStatus(
            hardware={
                "relays": hardware.get_status().relays,
                "inputs": hardware.get_status().inputs,
                "door_open": hardware.is_door_open(),
                "emergency_override": hardware.emergency_override_active(),
                "system_ready": hardware.get_status().system_ready
            },
            scanner=barcode_manager.get_status(),
            database={"status": "connected"},  # Simplified
            uptime=uptime_str,
            timestamp=datetime.now()
        )
    
    @app.get("/status/hardware")
    async def get_hardware_status(current_user: str = Depends(verify_token)):
        """Get detailed hardware status"""
        status = hardware.get_status()
        return {
            "relays": status.relays,
            "inputs": status.inputs,
            "door_open": hardware.is_door_open(),
            "emergency_override": hardware.emergency_override_active(),
            "last_update": status.last_update,
            "system_ready": status.system_ready
        }
    
    @app.get("/logs/access", response_model=List[AccessLogResponse])
    async def get_access_logs(
        limit: int = 100,
        offset: int = 0,
        current_user: str = Depends(verify_token)
    ):
        """Get access logs"""
        try:
            logs = await access_verifier.get_access_logs(limit=limit, offset=offset)
            return [
                AccessLogResponse(
                    id=log.id,
                    timestamp=log.timestamp,
                    barcode=log.barcode,
                    granted=log.granted,
                    user_id=log.user_id,
                    user_name=log.user_name,
                    reason=log.reason,
                    source=log.source
                ) for log in logs
            ]
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get logs: {str(e)}")
    
    # Emergency endpoints
    @app.post("/emergency/override")
    async def emergency_override(
        reason: str = "Emergency override",
        current_user: str = Depends(verify_token)
    ):
        """Emergency door override"""
        try:
            # Log emergency access
            await log_api_access(
                barcode="EMERGENCY",
                granted=True,
                user_id=current_user,
                reason=reason,
                source="emergency"
            )
            
            # Open door immediately
            hardware.open_door(duration=30)  # Keep open longer for emergencies
            
            return AccessResponse(
                success=True,
                message=f"Emergency override activated: {reason}",
                timestamp=datetime.now()
            )
        
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Emergency override failed: {str(e)}")
    
    # Health check endpoint (no authentication required)
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "timestamp": datetime.now(),
            "uptime": str(datetime.now() - startup_time).split('.')[0]
        }
    
    return app


async def log_api_access(barcode: str, granted: bool, user_id: str, reason: str, source: str):
    """Helper function to log API access attempts"""
    try:
        log_entry = AccessLog(
            barcode=barcode,
            granted=granted,
            user_id=user_id,
            reason=reason,
            source=source
        )
        await access_verifier.local_db.log_access_attempt(log_entry)
    except Exception as e:
        logging.getLogger(__name__).error(f"Failed to log API access: {e}")


# Create the app instance
app = create_app() if FASTAPI_AVAILABLE else None
