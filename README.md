# Gov.br Authentication Automation

Automated login for Brazilian government portal using Bright Data for captcha solving and certificate authentication.

## Prerequisites
- Python 3.8+
- Bright Data account (KYC-verified)
- Valid .pfx certificate

## Setup
1. Install: pip install -r requirements.txt && playwright install chromium
2. Copy .env.example to .env and add credentials
3. Run: python main.py

## Features
- Automatic hCaptcha solving
- Client certificate authentication
- Auto-retry on errors
- Zero manual intervention

## Config (.env)
BRIGHT_DATA_USERNAME=your-username
BRIGHT_DATA_PASSWORD=your-password
CERTIFICATE_PATH=cert2025.pfx
CERTIFICATE_PASSWORD=your-cert-password
