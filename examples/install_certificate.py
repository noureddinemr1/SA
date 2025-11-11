import subprocess
import os
from config import CERTIFICATE_PATH, CERTIFICATE_PASSWORD


def install_certificate_to_windows():
    if not CERTIFICATE_PATH or not os.path.exists(CERTIFICATE_PATH):
        print(f"❌ Certificate not found: {CERTIFICATE_PATH}")
        return False
    
    abs_cert_path = os.path.abspath(CERTIFICATE_PATH)
    
    print(f"📜 Installing certificate to Windows...")
    print(f"   Path: {abs_cert_path}")
    
    try:
        cmd = f'certutil -f -user -p "{CERTIFICATE_PASSWORD}" -importpfx "{abs_cert_path}" NoRoot'
        
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 or "command completed successfully" in result.stdout.lower():
            print(f"   ✅ Certificate installed successfully!")
            print(f"   The browser will now automatically use this certificate")
            return True
        else:
            print(f"   ⚠ Certificate might already be installed or:")
            print(f"   {result.stdout}")
            if "already exists" in result.stdout.lower():
                print(f"   ✅ Certificate is already installed")
                return True
            return False
            
    except Exception as e:
        print(f"   ❌ Error installing certificate: {e}")
        return False


def uninstall_certificate():
    print(f"📜 Removing certificate from Windows...")
    try:
        cmd = f'certutil -delstore -user My "$(certutil -user -store My | findstr /C:"Issuer")"'
        subprocess.run(cmd, shell=True)
        print(f"   ✅ Certificate removed (if it was installed)")
    except Exception as e:
        print(f"   ⚠ Note: {e}")


if __name__ == "__main__":
    print("\n" + "="*60)
    print("CERTIFICATE INSTALLER")
    print("="*60 + "\n")
    
    install_certificate_to_windows()
    
    print("\n" + "="*60)
    print("ℹ️  To remove the certificate later, run:")
    print(f"   certutil -delstore -user My <certificate_name>")
    print("="*60)
