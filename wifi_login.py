#!/usr/bin/env python3
"""
Clean, Lightweight Wi-Fi Login Client for Campus Wi-Fi
Automates captive portal authentication with zero-popup background execution.
Prompts first-time users via native macOS dialogs and encrypts in Keychain.
"""

import time
import subprocess
import urllib.request
import urllib.parse
import ssl
import re
import sys
import os

KEYCHAIN_SERVICE = "VIT-WiFi"
PORTAL_ENDPOINTS = [
    "http://172.16.1.1/cgi-bin/authlogin?URI=http://captive.apple.com/hotspot-detect.html",
    "http://phc.prontonetworks.com/cgi-bin/authlogin?URI=http://captive.apple.com/hotspot-detect.html",
]
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/128.0.0.0 Safari/537.36"


def log_message(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def send_notification(message, title="VIT Wi-Fi"):
    try:
        safe_msg = message.replace('"', '\\"')
        safe_title = title.replace('"', '\\"')
        apple_script = f'display notification "{safe_msg}" with title "{safe_title}"'
        subprocess.run(["osascript", "-e", apple_script], capture_output=True)
    except Exception:
        pass


def dismiss_cna_popup():
    """Instantly terminates the macOS Captive Network Assistant popup window."""
    try:
        subprocess.run(["killall", "-9", "Captive Network Assistant"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def save_credentials(username, password):
    """Encrypts and stores credentials in macOS Keychain."""
    try:
        cmd = [
            "security", "add-generic-password",
            "-U",
            "-s", KEYCHAIN_SERVICE,
            "-a", username,
            "-w", password
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        return res.returncode == 0
    except Exception:
        return False


def prompt_gui_text(prompt_text, title="University Wi-Fi Setup", hidden=False):
    """Prompts the user with a native macOS input dialog using AppleScript."""
    hidden_clause = "with hidden answer " if hidden else ""
    as_script = f'''
    tell current application
        activate
        set dlg to display dialog "{prompt_text}" default answer "" {hidden_clause}with title "{title}" with icon note buttons {{"Cancel", "OK"}} default button "OK"
        return text returned of dlg
    end tell
    '''
    try:
        res = subprocess.run(["osascript", "-e", as_script], capture_output=True, text=True)
        if res.returncode == 0:
            val = res.stdout.strip()
            return val if val else None
    except Exception:
        pass
    return None


def prompt_credentials_gui():
    """Shows native macOS popup dialogs to enter username and password on first run."""
    user = prompt_gui_text("Enter your University Reg / User ID (e.g. 23BCE1234):", title="University Wi-Fi Setup")
    if not user:
        return None, None
    pwd = prompt_gui_text("Enter your Wi-Fi Portal Password:", title="University Wi-Fi Setup", hidden=True)
    if not pwd:
        return None, None

    if save_credentials(user, pwd):
        log_message(f"Credentials successfully saved to macOS Keychain for '{user}'.")
        send_notification(f"Credentials saved for {user} in Keychain")
        return user, pwd
    return None, None


def get_credentials(prompt_if_missing=True):
    """
    Retrieves credentials from macOS Keychain.
    If missing and prompt_if_missing is True, displays a native GUI popup.
    """
    try:
        res_user = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE], capture_output=True, text=True)
        if res_user.returncode == 0:
            match = re.search(r'"acct"<blob>="([^"]+)"', res_user.stdout + res_user.stderr)
            username = match.group(1) if match else None
            res_pass = subprocess.run(["security", "find-generic-password", "-s", KEYCHAIN_SERVICE, "-w"], capture_output=True, text=True)
            password = res_pass.stdout.strip() if res_pass.returncode == 0 else None
            if username and password:
                return username, password
    except Exception:
        pass

    if prompt_if_missing:
        return prompt_credentials_gui()

    return None, None


def is_campus_network():
    """Detects if connected to the campus network using IP subnet."""
    try:
        res = subprocess.run(["ipconfig", "getifaddr", "en0"], capture_output=True, text=True)
        ip = res.stdout.strip()
        if ip.startswith("172.16.") or ip.startswith("172.") or ip.startswith("10."):
            return True
    except Exception:
        pass
    return False


def is_internet_active():
    """Checks if Apple's hotspot test returns Success."""
    try:
        req = urllib.request.Request("http://captive.apple.com/hotspot-detect.html", headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=1.5) as response:
            return "Success" in response.read().decode("utf-8", errors="ignore")
    except Exception:
        return False


def do_login():
    """Rapidly fires the login payload until the network routes it."""
    username, password = get_credentials(prompt_if_missing=True)
    if not username or not password:
        log_message("Error: Credentials not configured.")
        return False

    if is_internet_active():
        log_message("Internet is already active.")
        dismiss_cna_popup()
        return True

    log_message(f"Authenticating as '{username}'...")

    post_data = urllib.parse.urlencode({
        "userId": username,
        "password": password,
        "serviceName": "ProntoAuthentication",
        "Submit22": "Login"
    }).encode("utf-8")

    headers = {
        "User-Agent": USER_AGENT,
        "Content-Type": "application/x-www-form-urlencoded",
        "Host": "phc.prontonetworks.com",
    }

    ctx = ssl._create_unverified_context()
    login_ok = False
    start_time = time.time()

    # Aggressively attempt POST for up to 20 seconds to cover wake-from-sleep delay
    while time.time() - start_time < 20:
        dismiss_cna_popup()  # Suppress captive popup window while connecting
        for endpoint in PORTAL_ENDPOINTS:
            try:
                req = urllib.request.Request(endpoint, data=post_data, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=1.5, context=ctx) as response:
                    if response.getcode() == 200:
                        log_message(f"HTTP POST Success on {endpoint}")
                        login_ok = True
                        break
            except Exception:
                pass

        if login_ok:
            break
        time.sleep(1.0)

    dismiss_cna_popup()

    # Verify connection
    if is_internet_active():
        log_message(f"SUCCESS: Connected to internet as {username}")
        send_notification(f"Connected to internet as {username}")
        return True

    log_message("Failed to connect.")
    return False


def run_daemon():
    """Background daemon that monitors campus Wi-Fi association."""
    log_message("🚀 Wi-Fi Daemon Active. Waiting for campus connection...")
    was_on_campus = False

    while True:
        on_campus = is_campus_network()

        if on_campus and not was_on_campus:
            log_message("⚡ Campus Wi-Fi detected! Triggering login...")
            do_login()

        was_on_campus = on_campus
        time.sleep(2.0)


def print_status():
    """Prints current Wi-Fi and credential status."""
    user, _ = get_credentials(prompt_if_missing=False)
    on_campus = is_campus_network()
    internet = is_internet_active()
    print("\n" + "=" * 56)
    print("             University Wi-Fi Automation Status")
    print("=" * 56)
    print(f"  Campus Network  : {'✅ Connected' if on_campus else '❌ Not detected'}")
    print(f"  Internet Access : {'✅ Active' if internet else '❌ Inactive / Blocked'}")
    print(f"  Credentials     : {'✅ Configured for ' + user if user else '❌ Not configured'}")
    print("=" * 56 + "\n")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "watch"

    if cmd == "login":
        success = do_login()
        sys.exit(0 if success else 1)
    elif cmd in ("watch", "daemon"):
        run_daemon()
    elif cmd == "status":
        print_status()
    elif cmd in ("set-credentials", "setup"):
        user_arg = None
        pass_arg = None
        if "-u" in sys.argv:
            idx = sys.argv.index("-u")
            if idx + 1 < len(sys.argv):
                user_arg = sys.argv[idx + 1]
        if "-p" in sys.argv:
            idx = sys.argv.index("-p")
            if idx + 1 < len(sys.argv):
                pass_arg = sys.argv[idx + 1]

        if user_arg and pass_arg:
            if save_credentials(user_arg, pass_arg):
                print(f"✅ Credentials saved to macOS Keychain for '{user_arg}'.")
            else:
                print("❌ Failed to save credentials.")
                sys.exit(1)
        else:
            u, p = prompt_credentials_gui()
            if u and p:
                print(f"✅ Credentials configured for '{u}'.")
            else:
                print("❌ Setup cancelled.")
                sys.exit(1)
    elif cmd in ("--help", "-h", "help"):
        print("Usage: vit-wifi [login|status|set-credentials|watch]")
    else:
        run_daemon()
