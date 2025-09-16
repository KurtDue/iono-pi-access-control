# Iono Pi Access Control - Setup Prerequisites

## Operating System Setup

### 1. Raspberry Pi OS Installation

#### Download and Flash OS:
```bash
# Download Raspberry Pi Imager
# Flash Raspberry Pi OS Lite (64-bit) to SD card
# Enable SSH during imaging process
```

#### Initial Configuration:
```bash
# After first boot, update system
sudo apt update && sudo apt upgrade -y

# Configure timezone
sudo raspi-config
# Navigate to: Localisation Options > Timezone

# Enable I2C and SPI (for Iono Pi hardware)
sudo raspi-config
# Navigate to: Interface Options > I2C > Enable
# Navigate to: Interface Options > SPI > Enable

# Reboot to apply changes
sudo reboot
```

### 2. System Requirements

#### Minimum Hardware:
- **RAM**: 1GB (2GB+ recommended)
- **Storage**: 16GB SD card (32GB+ recommended)
- **CPU**: ARM Cortex-A53 or newer
- **Network**: Ethernet or WiFi capability

#### Required System Packages:
```bash
# Core development tools
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    git \
    curl \
    wget \
    sqlite3

# GPIO and hardware support
sudo apt install -y \
    python3-rpi.gpio \
    i2c-tools \
    spi-tools

# Network and security tools
sudo apt install -y \
    ufw \
    fail2ban \
    nginx \
    certbot

# Development tools (optional)
sudo apt install -y \
    vim \
    nano \
    htop \
    screen \
    tmux
```

## Hardware Configuration

### 1. Iono Pi Specific Setup

#### GPIO Access:
```bash
# Add user to gpio group
sudo usermod -a -G gpio,i2c,spi $USER

# Install Iono Pi specific libraries (if available)
pip3 install --user spidev smbus2
```

#### Serial Port Configuration:
```bash
# Disable serial console (if using serial barcode scanner)
sudo raspi-config
# Navigate to: Interface Options > Serial Port
# Select "No" for login shell over serial
# Select "Yes" for serial port hardware

# Check available serial ports
ls -la /dev/tty*
dmesg | grep tty
```

### 2. Network Configuration

#### Static IP (Recommended):
```bash
# Edit network configuration
sudo nano /etc/dhcpcd.conf

# Add these lines for static IP:
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1 8.8.8.8
```

#### Firewall Setup:
```bash
# Configure UFW firewall
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 8000  # API port
sudo ufw enable
```

## Barcode Scanner Setup

### USB Barcode Scanners:
```bash
# Check USB devices
lsusb

# Most USB barcode scanners work as HID devices
# No additional drivers needed for most models

# For serial/RS232 scanners:
sudo apt install -y setserial

# Check serial configuration
sudo dmesg | grep ttyUSB
```

### Supported Scanner Types:
- **USB HID**: Most plug-and-play barcode scanners
- **USB Serial**: RS232/RS485 scanners with USB adapter
- **Direct Serial**: Connected to Pi's UART pins

## Door Hardware Integration

### Relay Connections:
```bash
# Iono Pi Relay Outputs (GPIO controlled):
Relay 1 (GPIO 4)  -> Door Strike/Lock
Relay 2 (GPIO 17) -> Door Sensor Power (optional)
Relay 3 (GPIO 27) -> Auxiliary (alarm, light)
Relay 4 (GPIO 22) -> Spare
```

### Input Connections:
```bash
# Digital Inputs:
Input 1 (GPIO 18) -> Door Position Sensor
Input 2 (GPIO 23) -> Emergency Override Button
Input 3 (GPIO 24) -> Auxiliary Input
Input 4 (GPIO 25) -> Spare Input
```

## Remote Database Prerequisites

### 1. Database Server Requirements:
- **HTTP API endpoint** for barcode verification
- **Authentication token** or API key
- **JSON response format** support
- **HTTPS recommended** for security

### 2. Example Database Integration:
```python
# Your database API should respond to:
POST /api/access/verify
{
    "barcode": "123456789",
    "timestamp": "2025-09-16T10:30:00Z",
    "device_id": "iono-pi-001"
}

# Expected response:
{
    "access_granted": true,
    "user_id": "user001",
    "user_name": "John Doe", 
    "permissions": ["door_access"],
    "expires_at": "2025-12-31T23:59:59Z",
    "reason": "Access granted"
}
```

## Performance Considerations

### 1. System Optimization:
```bash
# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable hciuart

# Optimize boot time
sudo systemctl disable dphys-swapfile

# Configure log rotation
sudo nano /etc/logrotate.d/access-control
```

### 2. Storage Management:
```bash
# Use industrial-grade SD card or USB storage
# Enable log rotation to prevent disk filling
# Consider external storage for database
```

## Security Hardening

### 1. System Security:
```bash
# Change default passwords
sudo passwd pi
sudo passwd root

# Disable password authentication for SSH
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
# Set: PubkeyAuthentication yes

# Install fail2ban
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

### 2. Application Security:
```bash
# Use strong JWT secret keys
# Enable HTTPS with Let's Encrypt
# Implement rate limiting
# Regular security updates
```

## Installation Checklist

- [ ] Raspberry Pi OS installed and updated
- [ ] GPIO/I2C/SPI interfaces enabled
- [ ] Required packages installed
- [ ] Static IP configured
- [ ] Firewall configured
- [ ] Iono Pi hardware connected
- [ ] Barcode scanner connected and tested
- [ ] Door hardware connected
- [ ] Network connectivity verified
- [ ] Remote database API accessible
- [ ] SSH keys configured
- [ ] Security hardening applied

## Troubleshooting Common Issues

### 1. GPIO Permissions:
```bash
# If GPIO access denied:
sudo usermod -a -G gpio $USER
sudo reboot
```

### 2. Serial Port Issues:
```bash
# Check port permissions
ls -la /dev/ttyUSB0
sudo chmod 666 /dev/ttyUSB0

# Or add user to dialout group
sudo usermod -a -G dialout $USER
```

### 3. Network Connectivity:
```bash
# Test API connectivity
curl -X GET https://your-database-api.com/health
ping google.com
```

This setup guide ensures your Iono Pi will be properly configured for the access control system!
