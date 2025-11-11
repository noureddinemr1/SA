from playwright.async_api import async_playwright, Page
import asyncio
from config import TARGET_URL


class SimpleGovBrAutomation:
    def __init__(self):
        self.page: Page = None
        self.browser = None
        
    async def run(self):
        async with async_playwright() as playwright:
            try:
                print("\n" + "="*60)
                print("GOV.BR SIMPLE AUTOMATION")
                print("="*60)
                print("\n✅ Certificate installed in Windows")
                print("⚠️  You will need to solve hCaptcha manually")
                print("="*60 + "\n")
                
                print("🌐 Launching browser (VISIBLE MODE)...")
                self.browser = await playwright.chromium.launch(
                    headless=False,
                    slow_mo=500
                )
                
                context = await self.browser.new_context(
                    viewport={'width': 1920, 'height': 1080},
                    ignore_https_errors=True
                )
                
                self.page = await context.new_page()
                print("   ✅ Browser opened\n")
                
                print(f"📍 Navigating to: {TARGET_URL}")
                await self.page.goto(TARGET_URL, wait_until='domcontentloaded')
                await asyncio.sleep(5)
                print(f"   ✅ Loaded: {self.page.url}\n")
                
                print("🔍 Looking for 'Seu certificado digital' button...")
                await asyncio.sleep(2)
                
                try:
                    cert_button = self.page.locator('button:has-text("Seu certificado digital")').first
                    await cert_button.wait_for(state='visible', timeout=10000)
                    print("   ✅ Found button!")
                    await cert_button.click()
                    print("   ✅ Clicked!\n")
                    await asyncio.sleep(5)
                except Exception as e:
                    print(f"   ⚠️  Button not found or not clickable: {e}")
                    print("   → Please click 'Seu certificado digital' manually in the browser\n")
                    await asyncio.sleep(10)
                
                print("📋 Current state:")
                print(f"   URL: {self.page.url}")
                print(f"   Title: {await self.page.title()}\n")
                
                captcha_present = await self.page.evaluate("""
                    () => {
                        const iframes = document.querySelectorAll('iframe');
                        for (const iframe of iframes) {
                            if (iframe.src && iframe.src.includes('hcaptcha')) {
                                return true;
                            }
                        }
                        return false;
                    }
                """)
                
                if captcha_present:
                    print("🤖 hCaptcha detected!")
                    print("\n" + "="*60)
                    print("PLEASE SOLVE THE CAPTCHA NOW")
                    print("="*60)
                    print("1. Look at the browser window")
                    print("2. Click the hCaptcha checkbox")
                    print("3. Complete any image challenges")
                    print("4. Wait for the green checkmark ✓")
                    print("\n⏱️  Waiting for you to complete it (max 3 minutes)...")
                    print("="*60 + "\n")
                    
                    start_url = self.page.url
                    for i in range(180):
                        await asyncio.sleep(1)
                        
                        current_url = self.page.url
                        if current_url != start_url:
                            print(f"\n✓ Page navigated to: {current_url}")
                            if 'x509' in current_url or 'certificate' in current_url.lower():
                                print("✓ Certificate page reached!")
                            break
                        
                        try:
                            token = await self.page.evaluate("""
                                () => {
                                    const field = document.querySelector('textarea[name="h-captcha-response"]');
                                    return field && field.value && field.value.length > 20;
                                }
                            """)
                            if token:
                                print(f"\n✓ hCaptcha solved!")
                                await asyncio.sleep(3)
                                print(f"✓ Current URL: {self.page.url}")
                                break
                        except:
                            pass
                        
                        if i % 30 == 0 and i > 0:
                            print(f"   ... still waiting ({i}s)")
                
                print("\n" + "="*60)
                print("CERTIFICATE AUTHENTICATION")
                print("="*60)
                print("The Windows certificate dialog should appear")
                print("Your certificate (cert2025.pfx) is installed")
                print("Windows will automatically select it")
                print("\n⏱️  Monitoring for 2 minutes...")
                print("="*60 + "\n")
                
                start_url = self.page.url
                for i in range(120):
                    await asyncio.sleep(1)
                    
                    current_url = self.page.url
                    if current_url != start_url:
                        if 'login' not in current_url.lower() and 'sso.acesso.gov.br' not in current_url.lower():
                            print(f"\n" + "="*60)
                            print("✅✅✅ SUCCESS! ✅✅✅")
                            print("="*60)
                            print(f"Authenticated and redirected to:")
                            print(f"{current_url}")
                            print("="*60 + "\n")
                            break
                    
                    if i % 20 == 0 and i > 0:
                        print(f"   ... waiting ({i}s) - Current: {self.page.url[:80]}")
                
                print("\n📌 Final Status:")
                print(f"   URL: {self.page.url}")
                print(f"   Title: {await self.page.title()}")
                
                print("\n\nBrowser will stay open for inspection.")
                print("Press Enter to close...")
                input()
                
            except Exception as e:
                print(f"\n❌ ERROR: {e}")
                import traceback
                traceback.print_exc()
                input("\nPress Enter to close...")
            finally:
                if self.browser:
                    await self.browser.close()


async def main():
    automation = SimpleGovBrAutomation()
    await automation.run()


if __name__ == "__main__":
    asyncio.run(main())
