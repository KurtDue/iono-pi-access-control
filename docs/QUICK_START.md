# Quick Start Installation Guide

## 🚀 **Fast Track Setup** (30 minutes)

### **1. Prepare Raspberry Pi OS**
```bash
# Flash Raspberry Pi OS Lite to SD card
# Boot Pi and connect to network
# SSH into the Pi:
ssh pi@your-pi-ip-address

# Update system
sudo apt update && sudo apt upgrade -y
```

### **2. Enable Required Interfaces**
```bash
sudo raspi-config
# Interface Options → I2C → Enable
# Interface Options → SPI → Enable
# Interface Options → SSH → Enable
# Finish and reboot
```

### **3. Install System Dependencies**
```bash
# Essential packages
sudo apt install -y python3-pip python3-venv git sqlite3 i2c-tools

# Add user to hardware groups
sudo usermod -a -G gpio,i2c,spi,dialout $USER
sudo reboot
```

### **4. Clone and Install Access Control System**
```bash
# Clone repository
git clone https://github.com/KurtDue/iono-pi-access-control.git
cd iono-pi-access-control

# Run automated installation
sudo chmod +x install.sh
sudo ./install.sh
```

### **5. Configure Your System**
```bash
# Edit configuration
sudo nano /etc/iono-access-control/config.yaml

# Key settings to update:
# - Database API URL and token
# - Admin password
# - Barcode scanner device path
# - GPIO pin assignments (if different)
```

### **6. Start and Test**
```bash
# Start service
sudo systemctl start iono-access-control

# Check status
sudo systemctl status iono-access-control

# Test API
curl http://localhost:8000/health
```

## 🔧 **Hardware Connections**

### **Minimal Setup:**
1. **Power**: Connect 12-24V DC to Iono Pi power input
2. **Door**: Connect door strike/lock to Relay 1 output
3. **Scanner**: Plug USB barcode scanner into Pi USB port
4. **Network**: Connect Ethernet cable or configure WiFi

### **Optional Additions:**
- Door sensor to Digital Input 1
- Emergency button to Digital Input 2
- LED indicators to additional relay outputs

## ⚡ **Quick Test Procedure**

### **1. Verify Hardware**
```bash
# Check GPIO access
python3 -c "import RPi.GPIO as GPIO; print('GPIO OK')"

# Check barcode scanner
ls /dev/ttyUSB* || lsusb | grep -i barcode
```

### **2. Test API Access**
```bash
# Get authentication token
curl -X POST "http://localhost:8000/auth/token" \
     -H "Content-Type: application/x-www-form-urlencoded" \
     -d "username=admin&password=admin123"

# Test door control (replace TOKEN)
curl -X POST "http://localhost:8000/access/open" \
     -H "Authorization: Bearer TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"reason": "Test", "duration": 3}'
```

### **3. Monitor Logs**
```bash
# Real-time logs
sudo journalctl -u iono-access-control -f

# Recent logs
sudo journalctl -u iono-access-control --since "1 hour ago"
```

## 🛠️ **Common Issues & Quick Fixes**

### **Service Won't Start:**
```bash
# Check logs
sudo journalctl -u iono-access-control

# Common fixes:
sudo chown iono-access:iono-access /var/lib/iono-access-control
sudo chmod 640 /etc/iono-access-control/config.yaml
```

### **Barcode Scanner Not Working:**
```bash
# Check device
lsusb | grep -i scanner
ls -la /dev/ttyUSB*

# Fix permissions
sudo usermod -a -G dialout iono-access
sudo systemctl restart iono-access-control
```

### **GPIO Access Denied:**
```bash
# Fix permissions
sudo usermod -a -G gpio iono-access
sudo reboot
```

## 📱 **Mobile App Integration**

The API is ready for mobile app integration:

**Base URL**: `http://your-pi-ip:8000`

**Key Endpoints:**
- `POST /auth/token` - Get access token
- `POST /access/open` - Open door remotely  
- `GET /status` - Check system status
- `GET /logs/access` - View access history

## 🔒 **Security Notes**

**⚠️ Change These Defaults:**
- Admin password in config.yaml
- JWT secret key
- Enable HTTPS in production
- Configure firewall rules

**🔐 Production Checklist:**
- [ ] Strong passwords set
- [ ] Firewall configured
- [ ] HTTPS enabled
- [ ] Regular backups scheduled
- [ ] Log monitoring set up

This should get you up and running quickly! The automated installer handles most of the complexity.
