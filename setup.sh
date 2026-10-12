#!/bin/bash
# ==========================================================
# Setup Script for Automatic Campus Wi-Fi Login on macOS
# ==========================================================

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
INSTALL_DIR="$HOME/.vitwifi"
PLIST_NAME="com.user.vitwifi.plist"
TARGET_PLIST="$HOME/Library/LaunchAgents/$PLIST_NAME"
PYTHON_BIN="$(which python3 || echo '/usr/bin/python3')"
USER_ID_NUM=$(id -u)
RAW_REPO_BASE="https://raw.githubusercontent.com/AzimAbdulla10/uni-wifi-login-client/main"

echo ""
echo "=========================================================="
echo "         🎓 University Wi-Fi Auto-Login Setup"
echo "=========================================================="
echo ""

# Handle --uninstall
if [ "$1" = "--uninstall" ] || [ "$1" = "uninstall" ]; then
    echo "Stopping and removing background LaunchAgent..."
    launchctl bootout "gui/$USER_ID_NUM" "$TARGET_PLIST" 2>/dev/null || true
    rm -f "$TARGET_PLIST"
    rm -rf "$INSTALL_DIR"
    rm -f "$HOME/.local/bin/vit-wifi"
    echo "✅ Background LaunchAgent and files removed."
    echo ""
    echo "To remove saved credentials from Keychain (optional):"
    echo "  security delete-generic-password -s 'VIT-WiFi'"
    echo ""
    echo "Uninstallation complete."
    exit 0
fi

# Step 1: Deploy wifi_login.py
mkdir -p "$INSTALL_DIR"
if [ -f "$DIR/wifi_login.py" ]; then
    cp "$DIR/wifi_login.py" "$INSTALL_DIR/wifi_login.py"
else
    echo "Downloading latest wifi_login.py..."
    curl -fsSL "$RAW_REPO_BASE/wifi_login.py" -o "$INSTALL_DIR/wifi_login.py"
fi
chmod +x "$INSTALL_DIR/wifi_login.py"

# Step 2: Configure Credentials
echo "Checking credentials in macOS Keychain..."
if "$PYTHON_BIN" -c 'import sys, subprocess, re; r=subprocess.run(["security","find-generic-password","-s","VIT-WiFi"],capture_output=True,text=True); sys.exit(0 if (r.returncode==0 and re.search(r"\"acct\"<blob>=\"[^\"]+\"", r.stdout+r.stderr)) else 1)' 2>/dev/null; then
    echo "✅ Existing credentials found in macOS Keychain."
else
    echo "Opening setup window to enter credentials..."
    "$PYTHON_BIN" "$INSTALL_DIR/wifi_login.py" set-credentials
fi

# Step 3: Install LaunchAgent (Active Background Daemon)
echo ""
echo "Installing Background Watcher Service..."
mkdir -p "$HOME/Library/LaunchAgents"

cat << PLIST_EOF > "$TARGET_PLIST"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.vitwifi</string>
    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON_BIN</string>
        <string>$INSTALL_DIR/wifi_login.py</string>
        <string>watch</string>
    </array>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$HOME/Library/Logs/vitwifi.log</string>
    <key>StandardErrorPath</key>
    <string>$HOME/Library/Logs/vitwifi.log</string>
</dict>
</plist>
PLIST_EOF

# Reload LaunchAgent
launchctl bootout "gui/$USER_ID_NUM" "$TARGET_PLIST" 2>/dev/null || true
launchctl bootstrap "gui/$USER_ID_NUM" "$TARGET_PLIST" 2>/dev/null || launchctl load -w "$TARGET_PLIST"
echo "✅ Background service installed and active!"

# Step 4: Install helper terminal command 'vit-wifi'
mkdir -p "$HOME/.local/bin"
cat << 'WRAPPER_EOF' > "$HOME/.local/bin/vit-wifi"
#!/bin/bash
exec /usr/bin/python3 "$HOME/.vitwifi/wifi_login.py" "${@:-login}"
WRAPPER_EOF
chmod +x "$HOME/.local/bin/vit-wifi"

echo ""
echo "=========================================================="
echo "🎉 Setup Complete!"
echo "=========================================================="
echo ""
"$PYTHON_BIN" "$INSTALL_DIR/wifi_login.py" status

echo "Next steps:"
echo "• When you connect to campus Wi-Fi, it connects automatically in the background!"
echo "• Test manually anytime: vit-wifi"
echo "• Check status:          vit-wifi status"
echo "• Change credentials:    vit-wifi set-credentials"
echo "• View activity log:     tail -f ~/Library/Logs/vitwifi.log"
echo ""
