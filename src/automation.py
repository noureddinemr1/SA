from playwright.async_api import async_playwright
import asyncio
from src.config import TARGET_URL, BRIGHT_DATA_USERNAME, BRIGHT_DATA_PASSWORD, TIMEOUT, CERTIFICATE_PATH, CERTIFICATE_PASSWORD
from src.captcha_solver import BrightDataCaptchaSolver
import base64
import os


class BrightDataFullAutomation:
    
    async def run(self):
        async with async_playwright() as playwright:
            for attempt in range(3):
                browser = None
                try:
                    print("\n" + "="*70)
                    print(f"🎉 FULL AUTOMATION - ATTEMPT {attempt + 1}/3 🎉")
                    print("="*70)
                    print("✅ Automatic hCaptcha solving (Bright Data)")
                    print("✅ Client certificate injection (Browser.addCertificate)")
                    print("✅ Auto-retry on 'Captcha inválido'")
                    print("="*70 + "\n")
                    
                    if not os.path.exists(CERTIFICATE_PATH):
                        print(f"❌ Certificate not found: {CERTIFICATE_PATH}")
                        return
                    
                    print("📜 Loading certificate...")
                    with open(CERTIFICATE_PATH, 'rb') as f:
                        cert_data = f.read()
                    
                    cert_base64 = base64.b64encode(cert_data).decode('utf-8')
                    
                    print(f"   ✅ Loaded: {CERTIFICATE_PATH}")
                    print(f"   Size: {len(cert_data)} bytes\n")
                    
                    print("🌐 Connecting to Bright Data...")
                    auth = f"{BRIGHT_DATA_USERNAME}:{BRIGHT_DATA_PASSWORD}"
                    endpoint_url = f"wss://{auth}@brd.superproxy.io:9222"
                    
                    browser = await playwright.chromium.connect_over_cdp(endpoint_url)
                    context = browser.contexts[0]
                    page = await context.new_page()
                    
                    cdp_session = await context.new_cdp_session(page)
                    captcha_solver = BrightDataCaptchaSolver(cdp_session)
                    print("   ✅ Connected\n")
                    
                    print("🔐 Injecting certificate via Browser.addCertificate...")
                    try:
                        result = await cdp_session.send('Browser.addCertificate', {
                            'cert': cert_base64,
                            'pass': CERTIFICATE_PASSWORD
                        })
                        print(f"   ✅ Certificate injected: {result}\n")
                    except Exception as e:
                        print(f"   ❌ Failed: {e}\n")
                        await browser.close()
                        continue
                    
                    print(f"📍 Navigating to {TARGET_URL}...")
                    await page.goto(TARGET_URL, wait_until='domcontentloaded', timeout=TIMEOUT)
                    await asyncio.sleep(3)
                    print(f"   ✅ Loaded\n")
                    
                    print("🔍 Clicking certificate button...")
                    try:
                        cert_button = page.locator('button:has-text("Seu certificado digital")').first
                        await cert_button.wait_for(state='visible', timeout=10000)
                        await cert_button.click()
                        print("   ✅ Clicked!\n")
                        await asyncio.sleep(3)
                    except Exception as e:
                        print(f"   ⚠️ Could not click: {e}\n")
                    
                    print("🤖 Solving hCaptcha with Bright Data...\n")
                    success = await captcha_solver.solve_with_retry(max_retries=2)
                    
                    if not success:
                        print("\n❌ Failed to solve captcha")
                        await browser.close()
                        continue
                    
                    print("\n✅ Captcha solved!")
                    print("⏳ Waiting for page response (10s)...\n")
                    await asyncio.sleep(10)
                    
                    print(f"📌 Current URL: {page.url}")
                    print(f"📌 Title: {await page.title()}\n")
                    
                    page_text = await page.evaluate("() => document.body.innerText")
                    
                    if 'Captcha inválido' in page_text or 'Tente novamente' in page_text:
                        print("⚠️ Website says: 'Captcha inválido. Tente novamente'")
                        print(f"   This is a temporary validation issue.")
                        print(f"   Retrying... (attempt {attempt + 1}/3)\n")
                        await browser.close()
                        await asyncio.sleep(3)
                        continue
                    
                    if 'certificado digital não encontrado' in page_text.lower():
                        print("❌ Certificate not recognized by website\n")
                        await browser.close()
                        continue
                    
                    print("="*70)
                    print("✅✅✅ SUCCESS! ✅✅✅")
                    print("="*70)
                    print(f"URL: {page.url}")
                    print(f"Title: {await page.title()}")
                    
                    if 'login' not in page.url.lower() and 'acesso.gov.br' not in page.url.lower():
                        print("\n🎉 FULLY AUTHENTICATED AND REDIRECTED!")
                    elif 'x509' not in page.url and 'captcha inválido' not in page_text.lower():
                        print("\n✅ Authentication successful (no errors detected)")
                    
                    print("\n📋 Page content preview:")
                    print(page_text[:500])
                    print("\n" + "="*70)
                    
                    print("\n🔍 Browser will stay open. Press Enter to close...")
                    input()
                    
                    await browser.close()
                    return
                    
                except Exception as e:
                    print(f"\n❌ ERROR on attempt {attempt + 1}: {e}")
                    import traceback
                    traceback.print_exc()
                    
                    if browser:
                        try:
                            await browser.close()
                        except:
                            pass
                    
                    if attempt < 2:
                        print(f"\n⏳ Retrying in 3 seconds...\n")
                        await asyncio.sleep(3)
                    else:
                        print("\n❌ All 3 attempts failed")
                        input("\nPress Enter to close...")


async def main():
    automation = BrightDataFullAutomation()
    await automation.run()


if __name__ == "__main__":
    asyncio.run(main())
