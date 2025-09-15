# Example API Client for Iono Pi Access Control System

import requests
import json
from datetime import datetime

class IonoAccessClient:
    """Client for Iono Pi Access Control API"""
    
    def __init__(self, base_url: str, username: str = None, password: str = None):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.token = None
        
        if username and password:
            self.login(username, password)
    
    def login(self, username: str, password: str) -> bool:
        """Authenticate and get access token"""
        try:
            response = self.session.post(
                f"{self.base_url}/auth/token",
                data={
                    "username": username,
                    "password": password
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                self.token = data["access_token"]
                self.session.headers.update({
                    "Authorization": f"Bearer {self.token}"
                })
                return True
            else:
                print(f"Login failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Login error: {e}")
            return False
    
    def open_door(self, reason: str, duration: float = None, user_id: str = None) -> bool:
        """Open the door via API"""
        try:
            data = {"reason": reason}
            if duration:
                data["duration"] = duration
            if user_id:
                data["user_id"] = user_id
            
            response = self.session.post(
                f"{self.base_url}/access/open",
                json=data
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"Success: {result['message']}")
                return True
            else:
                print(f"Failed to open door: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Error opening door: {e}")
            return False
    
    def verify_barcode(self, barcode: str) -> dict:
        """Verify a barcode"""
        try:
            response = self.session.post(
                f"{self.base_url}/access/verify",
                json={"barcode": barcode}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Verification failed: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"Verification error: {e}")
            return {}
    
    def get_status(self) -> dict:
        """Get system status"""
        try:
            response = self.session.get(f"{self.base_url}/status")
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Status request failed: {response.status_code}")
                return {}
                
        except Exception as e:
            print(f"Status error: {e}")
            return {}
    
    def get_access_logs(self, limit: int = 100) -> list:
        """Get access logs"""
        try:
            response = self.session.get(
                f"{self.base_url}/logs/access",
                params={"limit": limit}
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Logs request failed: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"Logs error: {e}")
            return []
    
    def emergency_override(self, reason: str = "Emergency override") -> bool:
        """Trigger emergency override"""
        try:
            response = self.session.post(
                f"{self.base_url}/emergency/override",
                params={"reason": reason}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"Emergency override: {result['message']}")
                return True
            else:
                print(f"Emergency override failed: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"Emergency override error: {e}")
            return False


# Example usage
if __name__ == "__main__":
    # Configure your Iono Pi details
    IONO_PI_URL = "http://192.168.1.100:8000"  # Replace with your Iono Pi IP
    USERNAME = "admin"
    PASSWORD = "admin123"  # Replace with your password
    
    # Create client
    client = IonoAccessClient(IONO_PI_URL)
    
    # Login
    if client.login(USERNAME, PASSWORD):
        print("Login successful!")
        
        # Get system status
        status = client.get_status()
        if status:
            print("\nSystem Status:")
            print(f"Hardware ready: {status.get('hardware', {}).get('system_ready', 'Unknown')}")
            print(f"Door open: {status.get('hardware', {}).get('door_open', 'Unknown')}")
            print(f"Scanner running: {status.get('scanner', {}).get('running', 'Unknown')}")
            print(f"Uptime: {status.get('uptime', 'Unknown')}")
        
        # Example: Open door
        if client.open_door("Remote access test", duration=3):
            print("\nDoor opened successfully!")
        
        # Example: Verify a barcode
        test_barcode = "123456789"
        verification = client.verify_barcode(test_barcode)
        if verification:
            print(f"\nBarcode verification for {test_barcode}:")
            print(f"Granted: {verification.get('granted', 'Unknown')}")
            print(f"Reason: {verification.get('reason', 'Unknown')}")
        
        # Get recent access logs
        logs = client.get_access_logs(limit=5)
        if logs:
            print(f"\nRecent access logs ({len(logs)} entries):")
            for log in logs:
                timestamp = log.get('timestamp', 'Unknown')
                barcode = log.get('barcode', 'Unknown')
                granted = log.get('granted', False)
                reason = log.get('reason', 'Unknown')
                print(f"  {timestamp}: {barcode} - {'GRANTED' if granted else 'DENIED'} ({reason})")
    
    else:
        print("Login failed!")
