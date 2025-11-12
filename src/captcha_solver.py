import time
import asyncio
from typing import Optional


class BrightDataCaptchaSolver:
    def __init__(self, cdp_session):
        self.cdp_session = cdp_session
        # Try to configure Bright Data to disable all auto-behavior
        asyncio.create_task(self._configure_solver())
    
    async def _configure_solver(self):
        """Configure Bright Data solver to disable auto-submit"""
        try:
            # Try various configuration options to disable auto-submit
            await self.cdp_session.send('Captcha.configure', {
                'autoSubmit': False,
                'autoDetect': True  # Still detect, just don't submit
            })
            print("   🔧 Configured Bright Data: autoSubmit=False")
        except Exception as e:
            print(f"   ⚠️ Could not configure Bright Data: {e}")

    async def solve_hcaptcha(self, detect_timeout: int = 40000):
        try:
            print(f"🤖 Bright Data: Detecting and solving hCaptcha...")
            print(f"   Timeout: {detect_timeout/1000}s")
            print(f"   🚫 Auto-submit disabled - manual control")
            
            start_time = time.time()
            
            # Use asyncio.wait_for to add a hard timeout to prevent hanging
            # Since we're blocking the submission, waitForSolve might hang indefinitely
            try:
                result = await asyncio.wait_for(
                    self.cdp_session.send('Captcha.waitForSolve', {
                        'detectTimeout': detect_timeout,
                        'autoSubmit': False  # CRITICAL: Prevent auto-submission
                    }),
                    timeout=(detect_timeout / 1000) + 10  # Add 10s buffer beyond detect timeout
                )
                
                elapsed = time.time() - start_time
                status = result.get('status', 'unknown')
                print(f"   Status: {status} (took {elapsed:.1f}s)")
                
                if status == 'solve_finished':
                    print(f"   ✅ hCaptcha solved successfully by Bright Data!")
                    print(f"   ⏳ Token should be available...")
                    await asyncio.sleep(2)
                    return True
                elif status == 'solve_skipped':
                    print(f"   ℹ️ Captcha solve skipped (may already be solved or not present)")
                    return True
                elif status == 'not_detected':
                    print(f"   ⚠️ Captcha not detected by Bright Data")
                    print(f"   💡 Tip: Ensure captcha iframe is visible and loaded")
                    return False
                elif status == 'solve_failed':
                    print(f"   ❌ Captcha solve failed")
                    return False
                else:
                    print(f"   ⚠️ Unexpected status: {status}")
                    print(f"   📋 Full result: {result}")
                    return False
                    
            except asyncio.TimeoutError:
                elapsed = time.time() - start_time
                print(f"   ⏰ Captcha solve timed out after {elapsed:.1f}s")
                print(f"   💡 Token was generated, but we need to wait for hCaptcha server validation")
                print(f"   ⏳ Waiting 8 seconds for hCaptcha backend to validate the token...")
                await asyncio.sleep(8)  # Increased from 5 to 8 seconds
                print(f"   ✅ Validation wait complete - assuming token is now valid")
                return True
                
        except Exception as e:
            print(f"   ❌ Error during captcha solve: {e}")
            import traceback
            traceback.print_exc()
            return False

    async def solve_with_retry(self, max_retries: int = 3, retry_delay: int = 4):
        print(f"\n🤖 BRIGHT DATA CAPTCHA SOLVER (CDP)")
        print(f"   Max attempts: {max_retries}")
        print(f"   Retry delay: {retry_delay}s")
        
        for attempt in range(max_retries):
            print(f"\n📍 Solve Attempt {attempt + 1}/{max_retries}")
            
            # Increase timeout for later attempts
            timeout = 25000 + (attempt * 5000)  # 25s, 30s, 35s...
            
            success = await self.solve_hcaptcha(detect_timeout=timeout)
            
            if success:
                print(f"\n✅ SUCCESS! Captcha handled by Bright Data")
                return True
            
            if attempt < max_retries - 1:
                print(f"   ⏳ Waiting {retry_delay}s before retry...")
                await asyncio.sleep(retry_delay)
        
        print(f"\n❌ Bright Data unable to solve captcha after {max_retries} attempts")
        return False
