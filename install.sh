#!/bin/bash

# Iono Pi Access Control System Installation Script
# This script installs and configures the access control system

set -e

# Configuration
SERVICE_NAME="iono-access-control"
INSTALL_DIR="/opt/iono-access-control"
CONFIG_DIR="/etc/iono-access-control"
LOG_DIR="/var/log/iono-access-control"
DATA_DIR="/var/lib/iono-access-control"
USER="iono-access"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging functions
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
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Check system requirements
check_requirements() {
    log_info "Checking system requirements..."
    
    # Check if we're on a Raspberry Pi
    if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        log_warn "This doesn't appear to be a Raspberry Pi. Hardware features may not work."
    fi
    
    # Check Python version
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    python_version=$(python3 -c "import sys; print('.'.join(map(str, sys.version_info[:2])))")
    log_info "Found Python $python_version"
    
    # Check pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 is required but not installed"
        exit 1
    fi
}

# Install system packages
install_system_packages() {
    log_info "Installing system packages..."
    
    apt-get update
    apt-get install -y \
        python3-dev \
        python3-pip \
        python3-venv \
        git \
        sqlite3 \
        udev \
        systemd
    
    log_info "System packages installed"
}

# Create system user
create_user() {
    log_info "Creating system user..."
    
    if ! id "$USER" &>/dev/null; then
        useradd --system --shell /bin/false --home-dir "$DATA_DIR" --create-home "$USER"
        log_info "Created user $USER"
    else
        log_info "User $USER already exists"
    fi
    
    # Add user to GPIO group for hardware access
    usermod -a -G gpio,dialout "$USER"
}

# Create directories
create_directories() {
    log_info "Creating directories..."
    
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$CONFIG_DIR"
    mkdir -p "$LOG_DIR"
    mkdir -p "$DATA_DIR"
    
    # Set ownership
    chown "$USER:$USER" "$LOG_DIR" "$DATA_DIR"
    chmod 755 "$INSTALL_DIR" "$CONFIG_DIR"
    chmod 750 "$LOG_DIR" "$DATA_DIR"
    
    log_info "Directories created"
}

# Install application
install_application() {
    log_info "Installing application..."
    
    # Copy application files
    cp -r . "$INSTALL_DIR/"
    
    # Set ownership
    chown -R root:root "$INSTALL_DIR"
    chmod 755 "$INSTALL_DIR/main.py"
    
    # Create virtual environment
    python3 -m venv "$INSTALL_DIR/venv"
    
    # Install Python dependencies
    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip
    "$INSTALL_DIR/venv/bin/pip" install -r "$INSTALL_DIR/requirements.txt"
    
    log_info "Application installed"
}

# Configure application
configure_application() {
    log_info "Configuring application..."
    
    # Copy configuration file if it doesn't exist
    if [ ! -f "$CONFIG_DIR/config.yaml" ]; then
        cp "$INSTALL_DIR/config/config.example.yaml" "$CONFIG_DIR/config.yaml"
        log_info "Configuration file created at $CONFIG_DIR/config.yaml"
        log_warn "Please edit $CONFIG_DIR/config.yaml with your settings"
    else
        log_info "Configuration file already exists"
    fi
    
    # Update paths in the application to use system directories
    sed -i "s|data/access_control.db|$DATA_DIR/access_control.db|g" "$CONFIG_DIR/config.yaml"
    sed -i "s|logs/access_control.log|$LOG_DIR/access_control.log|g" "$CONFIG_DIR/config.yaml"
    
    # Set permissions
    chown root:$USER "$CONFIG_DIR/config.yaml"
    chmod 640 "$CONFIG_DIR/config.yaml"
}

# Create systemd service
create_service() {
    log_info "Creating systemd service..."
    
    cat > "/etc/systemd/system/$SERVICE_NAME.service" << EOF
[Unit]
Description=Iono Pi Access Control System
After=network.target
Wants=network.target

[Service]
Type=simple
User=$USER
Group=$USER
WorkingDirectory=$INSTALL_DIR
Environment=PYTHONPATH=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=$LOG_DIR $DATA_DIR $CONFIG_DIR
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd
    systemctl daemon-reload
    
    log_info "Systemd service created"
}

# Setup udev rules for USB devices
setup_udev_rules() {
    log_info "Setting up udev rules..."
    
    cat > "/etc/udev/rules.d/99-iono-access-control.rules" << EOF
# USB barcode scanners
SUBSYSTEM=="tty", ATTRS{idVendor}=="*", ATTRS{idProduct}=="*", MODE="0666", GROUP="dialout"

# USB serial devices
KERNEL=="ttyUSB*", MODE="0666", GROUP="dialout"
KERNEL=="ttyACM*", MODE="0666", GROUP="dialout"
EOF
    
    # Reload udev rules
    udevadm control --reload-rules
    udevadm trigger
    
    log_info "Udev rules configured"
}

# Enable and start service
enable_service() {
    log_info "Enabling and starting service..."
    
    systemctl enable "$SERVICE_NAME"
    systemctl start "$SERVICE_NAME"
    
    # Wait a moment and check status
    sleep 2
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_info "Service started successfully"
    else
        log_error "Service failed to start. Check: systemctl status $SERVICE_NAME"
        exit 1
    fi
}

# Show status and next steps
show_status() {
    log_info "Installation complete!"
    echo
    echo "Service status:"
    systemctl status "$SERVICE_NAME" --no-pager
    echo
    echo "Next steps:"
    echo "1. Edit configuration: sudo nano $CONFIG_DIR/config.yaml"
    echo "2. Restart service: sudo systemctl restart $SERVICE_NAME"
    echo "3. View logs: sudo journalctl -u $SERVICE_NAME -f"
    echo "4. Check API: curl http://localhost:8000/health"
    echo
    echo "Useful commands:"
    echo "  Start:   sudo systemctl start $SERVICE_NAME"
    echo "  Stop:    sudo systemctl stop $SERVICE_NAME"
    echo "  Restart: sudo systemctl restart $SERVICE_NAME"
    echo "  Status:  sudo systemctl status $SERVICE_NAME"
    echo "  Logs:    sudo journalctl -u $SERVICE_NAME"
    echo
}

# Main installation process
main() {
    log_info "Starting Iono Pi Access Control System installation..."
    
    check_root
    check_requirements
    install_system_packages
    create_user
    create_directories
    install_application
    configure_application
    create_service
    setup_udev_rules
    enable_service
    show_status
    
    log_info "Installation completed successfully!"
}

# Run if called directly
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
