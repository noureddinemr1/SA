import os
from dotenv import load_dotenv

load_dotenv()

BRIGHT_DATA_USERNAME = os.getenv("BRIGHT_DATA_USERNAME")
BRIGHT_DATA_PASSWORD = os.getenv("BRIGHT_DATA_PASSWORD")
CERTIFICATE_PATH = os.getenv("CERTIFICATE_PATH")
CERTIFICATE_PASSWORD = os.getenv("CERTIFICATE_PASSWORD")

TARGET_URL = "https://sso.acesso.gov.br/login"
TIMEOUT = 30000
