# BisdakWallet
Web XRP/XAH wallet. Securely access your XRP wallet anywhere.

<img src="https://github.com/lilmond/BisdakWallet/blob/main/static/img/wallet_preview.png?raw=true"/>

# Installation
Windows 10
```
python -m venv venv
venv\Scripts\activate.bat
pip install -r requirements.txt
python app.py
```

# Usage
- Edit config/seeds.txt and PASSWORD in config/config.toml
- Open (127.0.0.1:8080), you can access this on your mobile since the app is listening to (0.0.0.0). Just make sure you type the correct IP address and have port forwarding on in your router.
