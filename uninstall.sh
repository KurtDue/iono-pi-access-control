#!/bin/bash

# Iono Pi Access Control System Uninstall Script

set -e

# Configuration
SERVICE_NAME="iono-access-control"
INSTALL_DIR="/opt/iono-access-control"
CONFIG_DIR="/etc/iono-access-control"
LOG_DIR="/var/log/iono-access-control"
DATA_DIR="/var/lib/iono-access-control"
USER="iono-access"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
if [[ $EUID -ne 0 ]]; then
    log_error "This script must be run as root (use sudo)"
    exit 1
fi

log_info "Uninstalling Iono Pi Access Control System..."

# Stop and disable service
if systemctl is-active --quiet "$SERVICE_NAME"; then
    log_info "Stopping service..."
    systemctl stop "$SERVICE_NAME"
fi

if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
    log_info "Disabling service..."
    systemctl disable "$SERVICE_NAME"
fi

# Remove service file
if [ -f "/etc/systemd/system/$SERVICE_NAME.service" ]; then
    log_info "Removing service file..."
    rm "/etc/systemd/system/$SERVICE_NAME.service"
    systemctl daemon-reload
fi

# Remove udev rules
if [ -f "/etc/udev/rules.d/99-iono-access-control.rules" ]; then
    log_info "Removing udev rules..."
    rm "/etc/udev/rules.d/99-iono-access-control.rules"
    udevadm control --reload-rules
fi

# Ask about data removal
echo
read -p "Remove configuration and data files? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -d "$CONFIG_DIR" ]; then
        log_info "Removing configuration directory..."
        rm -rf "$CONFIG_DIR"
    fi
    
    if [ -d "$DATA_DIR" ]; then
        log_info "Removing data directory..."
        rm -rf "$DATA_DIR"
    fi
    
    if [ -d "$LOG_DIR" ]; then
        log_info "Removing log directory..."
        rm -rf "$LOG_DIR"
    fi
else
    log_info "Keeping configuration and data files"
    log_info "Config: $CONFIG_DIR"
    log_info "Data: $DATA_DIR"
    log_info "Logs: $LOG_DIR"
fi

# Remove application directory
if [ -d "$INSTALL_DIR" ]; then
    log_info "Removing application directory..."
    rm -rf "$INSTALL_DIR"
fi

# Ask about user removal
echo
read -p "Remove system user '$USER'? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if id "$USER" &>/dev/null; then
        log_info "Removing user..."
        userdel "$USER" 2>/dev/null || true
    fi
else
    log_info "Keeping system user '$USER'"
fi

log_info "Uninstallation complete!"
