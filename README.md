# Iono Pi Access Control System

A comprehensive access control system for the Iono Pi RTC that provides door control via relay outputs, barcode scanning support, and remote database verification.

## Features

- **Hardware Control**: Direct control of Iono Pi relay outputs for door control
- **Barcode Support**: Interface with USB/Serial barcode scanners
- **Remote Verification**: Verify access codes against remote databases
- **REST API**: Web service for remote access control commands
- **Real-time Logging**: Comprehensive audit trail with RTC timestamps
- **Security**: Token-based authentication and secure communication

## Hardware Setup

### Iono Pi Connections

- **Relay Output 1**: Door strike/magnetic lock control
- **Relay Output 2**: Door sensor feedback (optional)
- **Digital Input 1**: Door position sensor
- **Digital Input 2**: Emergency override button
- **TTL I/O**: Barcode scanner connection (USB recommended)

### Door Hardware

Connect your door control hardware to Relay Output 1:
- Electric door strike
- Magnetic door lock
- Electronic door lock mechanism

## Installation

1. Clone this repository on your Iono Pi
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy configuration template:
   ```bash
   cp config/config.example.yaml config/config.yaml
   ```
4. Edit configuration file with your settings
5. Install as system service:
   ```bash
   sudo ./install.sh
   ```

## Configuration

Edit `config/config.yaml` to configure:
- Database connection settings
- Hardware pin assignments
- Security settings
- Logging configuration

## API Usage

### Authentication
```bash
# Get access token
curl -X POST "http://your-iono-pi:8000/auth/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin&password=your_password"
```

### Open Door
```bash
# Via API
curl -X POST "http://your-iono-pi:8000/access/open" \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"reason": "Manual override", "duration": 5}'
```

### Check Status
```bash
curl -X GET "http://your-iono-pi:8000/status" \
     -H "Authorization: Bearer YOUR_TOKEN"
```

## License

MIT License - see LICENSE file for details
