import os
from dotenv import load_dotenv

load_dotenv()

BRIGHT_DATA_USERNAME = os.getenv("BRIGHT_DATA_USERNAME")
BRIGHT_DATA_PASSWORD = os.getenv("BRIGHT_DATA_PASSWORD")
CERTIFICATE_PATH = os.getenv("CERTIFICATE_PATH")
CERTIFICATE_PASSWORD = os.getenv("CERTIFICATE_PASSWORD")

TARGET_URL = "https://sso.acesso.gov.br/login"
TIMEOUT = 30000

# Timing configuration for captcha validation
# These are optimized values based on hCaptcha's validation requirements
# Only adjust if you experience consistent failures
CAPTCHA_POST_SOLVE_WAIT = int(os.getenv("CAPTCHA_POST_SOLVE_WAIT", "10"))  # Seconds to wait after captcha solve
CAPTCHA_SUBMIT_DELAY = int(os.getenv("CAPTCHA_SUBMIT_DELAY", "8"))  # Seconds to wait before form submission
