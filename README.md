# uni-wifi-login-client

A lightweight macOS utility that automatically connects and authenticates to university campus Wi-Fi without manual logins or popups.

## ⬇️ Download & Install

### Option 1: Direct Download (Easiest)
1. **[Download uni-wifi-login-client (ZIP)](https://github.com/AzimAbdulla10/uni-wifi-login-client/archive/refs/heads/main.zip)**
2. Unzip the downloaded folder.
3. Double-click **`Install.command`** (or run `./setup.sh` in Terminal).
4. A popup will ask for your University ID and password once. That's it!

### Option 2: 1-Line Terminal Install
Open Terminal and paste:
```bash
curl -fsSL https://raw.githubusercontent.com/AzimAbdulla10/uni-wifi-login-client/main/setup.sh | bash
```

---

## Features

- **Zero-Touch Login**: Automatically connects and authenticates whenever you join the campus Wi-Fi.
- **No Captive Popups**: Bypasses and dismisses the login window in the background.
- **Keychain Encrypted**: Your credentials are encrypted directly inside your macOS Keychain.
- **Lightweight**: Zero external dependencies, native macOS background service.

## Usage

Once installed, it runs completely automatically whenever you connect to Wi-Fi.

You can also use the terminal command anytime:
```bash
vit-wifi                 # Manually trigger login
vit-wifi status          # Check connection & credential status
vit-wifi set-credentials # Update your saved credentials
```

### Uninstallation
To remove the background service:
```bash
./setup.sh --uninstall
```
