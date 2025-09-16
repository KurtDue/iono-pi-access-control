# Hardware Compatibility Guide

## 📟 **Supported Barcode Scanners**

### **✅ Verified Compatible Models:**

#### **USB HID Scanners (Plug & Play):**
- **Honeywell Voyager 1200g** - USB, 1D/2D codes
- **Symbol LS2208** - USB, laser scanner
- **Zebra DS2208** - USB, 2D imager
- **Datalogic QuickScan Lite QW2100** - USB, linear imager
- **Generic USB HID scanners** - Most work out of the box

#### **USB Serial Scanners:**
- **Honeywell MS5145 Eclipse** - USB-Serial adapter
- **Symbol LS1203** - With USB cable
- **Motorola/Zebra CS1504** - USB interface

#### **RS232/RS485 Serial:**
- **Honeywell MK5145** - Via USB-Serial converter
- **Metrologic MS9520** - Serial interface
- **Custom serial scanners** - 9600-115200 baud

### **Scanner Configuration Examples:**

#### **USB HID Scanner:**
```yaml
barcode_scanner:
  enabled: true
  device: "auto"  # Automatically detected
  baudrate: 9600
  timeout: 1.0
```

#### **USB Serial Scanner:**
```yaml
barcode_scanner:
  enabled: true
  device: "/dev/ttyUSB0"
  baudrate: 9600
  timeout: 1.0
  suffix: "\r\n"
```

#### **Testing Scanner:**
```bash
# For USB HID scanners
sudo cat /dev/hidraw0  # or /dev/hidraw1, etc.

# For USB Serial scanners  
sudo cat /dev/ttyUSB0

# Scan a barcode to see output
```

## 🚪 **Door Hardware Compatibility**

### **✅ Compatible Door Controls:**

#### **Electric Door Strikes:**
- **12V DC strikes** (most common)
- **24V DC strikes** 
- **Adams Rite 7140** series
- **HES 1006** series
- **Trine 4900** series

#### **Magnetic Locks:**
- **12V DC magnetic locks** (up to 600lbs)
- **24V DC magnetic locks** (up to 1200lbs)
- **Securitron M62** series
- **DynaLock 3101C** series

#### **Electronic Locks:**
- **12/24V DC deadbolts**
- **Von Duprin 6100** series
- **Schlage CO-100** series
- **ASSA Twin 6000** series

### **Relay Specifications:**
```
Iono Pi Relay Outputs:
- Voltage Rating: 250V AC / 30V DC
- Current Rating: 6A (resistive load)
- Contact Type: SPDT (Single Pole Double Throw)
- Switching: Up to 15A inrush current
```

### **Wiring Examples:**

#### **Door Strike Connection:**
```
Iono Pi Relay 1:
  Common (C) → +12V/24V Power Supply
  NO (Normally Open) → Door Strike Positive
  Door Strike Negative → Power Supply Ground
```

#### **Magnetic Lock Connection:**
```
Iono Pi Relay 1:
  Common (C) → +12V/24V Power Supply  
  NC (Normally Closed) → Mag Lock Positive
  Mag Lock Negative → Power Supply Ground
  
Note: NC keeps lock powered (secure) by default
```

## 🔍 **Door Sensors**

### **✅ Compatible Sensors:**

#### **Magnetic Reed Switches:**
- **Surface mount** contacts
- **Recessed mount** contacts  
- **Armored cable** versions
- **Normally Closed** (recommended)
- **Normally Open** variants

#### **PIR Motion Sensors:**
- **12V DC PIR sensors**
- **Request-to-Exit (REX)** sensors
- **Ceiling mount** detectors

#### **Proximity Sensors:**
- **Inductive proximity** switches
- **Capacitive proximity** switches
- **12-24V DC** operation

### **Sensor Wiring:**
```
Door Sensor to Digital Input:
  Sensor Output → Iono Pi Digital Input
  Sensor Ground → Iono Pi Ground
  Sensor Power → +12V/24V (if powered sensor)
```

## 🔌 **Power Requirements**

### **Iono Pi Power:**
- **Input Voltage**: 9-28V DC
- **Current Draw**: 2-4A (depending on Pi model)
- **Power Supply**: 60W recommended minimum
- **Protection**: Reverse polarity, surge protection

### **Total System Power Budget:**
```
Component               Power Draw
Iono Pi + Raspberry Pi   15W
Door Strike (12V)        6W (when activated)
Magnetic Lock (12V)      12W (continuous)
Barcode Scanner (USB)    2.5W
Door Sensors            1W
Margin                  10W
Total Recommended:      50W PSU minimum
```

### **Recommended Power Supplies:**
- **Mean Well DR-60-24** (60W, 24V, DIN rail)
- **TDK Lambda DPP60-24** (60W, 24V)  
- **Phoenix Contact QUINT-PS** series
- **12V/24V industrial supplies** (3A+)

## 🌐 **Network Requirements**

### **Ethernet (Recommended):**
- **10/100 Mbps** Ethernet connection
- **Power over Ethernet** (PoE) optional with PoE hat
- **Static IP** recommended for remote access

### **WiFi (Alternative):**
- **802.11n/ac** WiFi capability (Pi 3B+ / Pi 4)
- **2.4GHz or 5GHz** networks supported
- **WPA2/WPA3** security

### **Internet Connectivity:**
- **Required for remote database** verification
- **HTTPS/TLS** capability for secure API calls
- **Bandwidth**: 1Mbps sufficient for normal operation

## 🔧 **Installation Requirements**

### **Physical Mounting:**
- **DIN Rail** mounting (4 modules wide)
- **Wall mount** brackets available
- **Ventilation** requirements (convection cooling)
- **Environmental**: IP20 rating (indoor use)

### **Cable Requirements:**
- **Low voltage** wiring for door controls
- **CAT5/6** for network connection
- **USB cable** for barcode scanner
- **Shielded cables** recommended for long runs

### **Tools Needed:**
- **Screwdrivers** (Phillips, flathead)
- **Wire strippers** and crimpers
- **Multimeter** for testing
- **Label maker** for identification

## ⚠️ **Safety & Compliance**

### **Electrical Safety:**
- **Licensed electrician** for high voltage connections
- **Proper grounding** of all components
- **Circuit protection** (fuses/breakers)
- **Emergency override** capabilities

### **Code Compliance:**
- **Local building codes** compliance
- **Fire safety** regulations
- **ADA accessibility** requirements
- **Security system** certifications

### **Testing Checklist:**
- [ ] Power supply voltage/current verified
- [ ] Door hardware operation tested
- [ ] Sensor functionality confirmed
- [ ] Network connectivity validated
- [ ] Emergency procedures tested
- [ ] Fail-safe operation verified

This guide ensures you select compatible hardware for reliable operation!
