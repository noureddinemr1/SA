import time
from typing import Optional


class BrightDataCaptchaSolver:
    def __init__(self, cdp_session):
        self.cdp_session = cdp_session

    async def solve_hcaptcha(self, detect_timeout: int = 30000):
        try:
            print(f"🤖 Bright Data: Detecting and solving hCaptcha...")
            print(f"   Timeout: {detect_timeout/1000}s")
            
            result = await self.cdp_session.send('Captcha.waitForSolve', {
                'detectTimeout': detect_timeout
            })
            
            status = result.get('status', 'unknown')
            print(f"   Status: {status}")
            
            if status == 'solve_finished':
                print(f"   ✅ hCaptcha solved successfully by Bright Data!")
                return True
            elif status == 'solve_skipped':
                print(f"   ℹ No captcha detected (skipped)")
                return True
            else:
                print(f"   ⚠ Unexpected status: {status}")
                return False
                
        except Exception as e:
            print(f"   ❌ Error during captcha solve: {e}")
            return False

    async def solve_with_retry(self, max_retries: int = 2):
        print(f"\n🤖 BRIGHT DATA CAPTCHA SOLVER (CDP)")
        print(f"   Max attempts: {max_retries}")
        
        for attempt in range(max_retries):
            print(f"\n📍 Attempt {attempt + 1}/{max_retries}")
            
            success = await self.solve_hcaptcha(detect_timeout=45000)
            
            if success:
                print(f"\n✅ SUCCESS! Captcha handled by Bright Data")
                return True
            
            if attempt < max_retries - 1:
                print(f"   ⏳ Retrying in 3 seconds...")
                time.sleep(3)
        
        print(f"\n❌ Bright Data unable to solve captcha after {max_retries} attempts")
        return False
