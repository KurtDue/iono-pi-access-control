# Example Remote Database API Server
# This is a simple Flask server that simulates a remote database
# for barcode verification

from flask import Flask, request, jsonify
from datetime import datetime, timedelta
import json

app = Flask(__name__)

# Simulated database of valid barcodes
VALID_BARCODES = {
    "123456789": {
        "user_id": "user001",
        "user_name": "John Doe",
        "permissions": ["door_access", "elevator"],
        "expires_at": "2025-12-31T23:59:59"
    },
    "987654321": {
        "user_id": "user002", 
        "user_name": "Jane Smith",
        "permissions": ["door_access"],
        "expires_at": "2025-06-30T23:59:59"
    },
    "555666777": {
        "user_id": "user003",
        "user_name": "Bob Wilson",
        "permissions": ["door_access", "admin"],
        "expires_at": "2025-12-31T23:59:59"
    },
    "TEST001": {
        "user_id": "test001",
        "user_name": "Test User",
        "permissions": ["door_access"],
        "expires_at": "2025-12-31T23:59:59"
    }
}

# API token for authentication
VALID_API_TOKEN = "Bearer your-api-token-here"

@app.route('/api/access/verify', methods=['POST'])
def verify_access():
    """Verify barcode access"""
    
    # Check authentication
    auth_header = request.headers.get('Authorization')
    if auth_header != VALID_API_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    
    # Get request data
    data = request.get_json()
    if not data or 'barcode' not in data:
        return jsonify({"error": "Missing barcode"}), 400
    
    barcode = data['barcode']
    
    # Log the request
    app.logger.info(f"Verification request for barcode: {barcode}")
    
    # Check if barcode exists
    if barcode in VALID_BARCODES:
        user_data = VALID_BARCODES[barcode]
        
        # Check expiration
        expires_at = datetime.fromisoformat(user_data['expires_at'])
        if expires_at < datetime.now():
            return jsonify({
                "access_granted": False,
                "barcode": barcode,
                "reason": "Access expired",
                "expires_at": user_data['expires_at']
            })
        
        # Access granted
        return jsonify({
            "access_granted": True,
            "barcode": barcode,
            "user_id": user_data['user_id'],
            "user_name": user_data['user_name'],
            "permissions": user_data['permissions'],
            "expires_at": user_data['expires_at'],
            "reason": "Access granted"
        })
    
    else:
        # Barcode not found
        return jsonify({
            "access_granted": False,
            "barcode": barcode,
            "reason": "Barcode not found in database"
        }), 404

@app.route('/api/users', methods=['GET'])
def list_users():
    """List all users (for admin)"""
    auth_header = request.headers.get('Authorization')
    if auth_header != VALID_API_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    
    users = []
    for barcode, user_data in VALID_BARCODES.items():
        users.append({
            "barcode": barcode,
            "user_id": user_data['user_id'],
            "user_name": user_data['user_name'],
            "permissions": user_data['permissions'],
            "expires_at": user_data['expires_at']
        })
    
    return jsonify({"users": users})

@app.route('/api/users', methods=['POST'])
def add_user():
    """Add a new user"""
    auth_header = request.headers.get('Authorization')
    if auth_header != VALID_API_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    
    data = request.get_json()
    required_fields = ['barcode', 'user_id', 'user_name']
    
    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing required fields"}), 400
    
    barcode = data['barcode']
    if barcode in VALID_BARCODES:
        return jsonify({"error": "Barcode already exists"}), 409
    
    # Set defaults
    permissions = data.get('permissions', ['door_access'])
    expires_at = data.get('expires_at', '2025-12-31T23:59:59')
    
    VALID_BARCODES[barcode] = {
        "user_id": data['user_id'],
        "user_name": data['user_name'],
        "permissions": permissions,
        "expires_at": expires_at
    }
    
    return jsonify({"message": "User added successfully"}), 201

@app.route('/api/users/<barcode>', methods=['DELETE'])
def delete_user(barcode):
    """Delete a user"""
    auth_header = request.headers.get('Authorization')
    if auth_header != VALID_API_TOKEN:
        return jsonify({"error": "Unauthorized"}), 401
    
    if barcode not in VALID_BARCODES:
        return jsonify({"error": "User not found"}), 404
    
    del VALID_BARCODES[barcode]
    return jsonify({"message": "User deleted successfully"})

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "total_users": len(VALID_BARCODES)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
