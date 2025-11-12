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
- Automatic hCaptcha solving with optimized timing
- Client certificate authentication with validation
- Auto-retry on errors
- Zero manual intervention
- Comprehensive error diagnostics

## Recent Improvements
✅ **Certificate Verification** - Validates certificate before login attempt  
✅ **Enhanced Timing** - 18+ second wait for hCaptcha validation (prevents "Captcha inválido")  
✅ **Form Validation** - Verifies all required fields before submission  
✅ **Better Diagnostics** - Specific error messages for each failure type  

See [FIXES_SUMMARY.md](FIXES_SUMMARY.md) for detailed changes and [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for issue resolution.

## Config (.env)
BRIGHT_DATA_USERNAME=your-username
BRIGHT_DATA_PASSWORD=your-password
CERTIFICATE_PATH=cert2025.pfx
CERTIFICATE_PASSWORD=your-cert-password

## Troubleshooting
If you encounter issues, check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for:
- Certificate authentication problems
- Captcha validation failures
- Form submission errors
- Server-side error handling
