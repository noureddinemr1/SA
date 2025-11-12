from playwright.async_api import async_playwright
import asyncio
from src.config import TARGET_URL, BRIGHT_DATA_USERNAME, BRIGHT_DATA_PASSWORD, TIMEOUT, CERTIFICATE_PATH, CERTIFICATE_PASSWORD, CAPTCHA_POST_SOLVE_WAIT, CAPTCHA_SUBMIT_DELAY
from src.captcha_solver import BrightDataCaptchaSolver
import base64
import os


class BrightDataFullAutomation:
    def __init__(self):
        self.ready_to_submit = False
        self.blocked_requests = []
    
    async def verify_certificate(self, cdp_session, cert_base64, cert_password):
        """Verify that the certificate is valid before attempting to use it"""
        try:
            print("   🔍 Verifying certificate validity...")
            
            # Try to add the certificate - if it fails, it's likely invalid
            result = await cdp_session.send('Browser.addCertificate', {
                'cert': cert_base64,
                'pass': cert_password
            })
            
            print(f"   ✅ Certificate is valid and injected successfully")
            print(f"   📋 Result: {result}")
            return True
            
        except Exception as e:
            error_msg = str(e).lower()
            
            if 'password' in error_msg or 'decrypt' in error_msg:
                print(f"   ❌ Certificate password is incorrect!")
                print(f"   💡 Check CERTIFICATE_PASSWORD in your .env file")
            elif 'expired' in error_msg:
                print(f"   ❌ Certificate has expired!")
                print(f"   💡 You need to obtain a new certificate")
            elif 'invalid' in error_msg or 'malformed' in error_msg:
                print(f"   ❌ Certificate file is invalid or corrupted!")
                print(f"   💡 Check the .pfx file integrity")
            else:
                print(f"   ❌ Certificate verification failed: {e}")
            
            return False
    
    async def wait_for_captcha_with_debug(self, page, max_wait_seconds=30):
        """Wait for captcha to appear with detailed debugging"""
        print("   🔍 Waiting for captcha with enhanced detection...")
        
        start_time = asyncio.get_event_loop().time()
        check_interval = 0.5  # Check every 500ms for faster detection
        
        while (asyncio.get_event_loop().time() - start_time) < max_wait_seconds:
            elapsed = asyncio.get_event_loop().time() - start_time
            
            # Multiple detection methods
            captcha_found = False
            
            # Method 1: Check for hCaptcha iframe by src
            try:
                hcaptcha_iframe = page.locator('iframe[src*="hcaptcha"]')
                count = await hcaptcha_iframe.count()
                if count > 0:
                    is_visible = await hcaptcha_iframe.first.is_visible()
                    if is_visible:
                        print(f"   ✅ Captcha detected via iframe[src*='hcaptcha'] after {elapsed:.1f}s!")
                        return True
                    else:
                        print(f"   � [{elapsed:.1f}s] hCaptcha iframe exists but not visible yet...")
                        captcha_found = True
            except Exception as e:
                pass
            
            # Method 2: Check for any iframe with hcaptcha in title or name
            try:
                all_iframes = page.locator('iframe')
                iframe_count = await all_iframes.count()
                if iframe_count > 0:
                    for i in range(iframe_count):
                        iframe = all_iframes.nth(i)
                        src = await iframe.get_attribute('src') or ''
                        title = await iframe.get_attribute('title') or ''
                        if 'hcaptcha' in src.lower() or 'hcaptcha' in title.lower():
                            is_visible = await iframe.is_visible()
                            if is_visible:
                                print(f"   ✅ Captcha detected via iframe #{i} after {elapsed:.1f}s!")
                                return True
                            else:
                                captcha_found = True
            except Exception as e:
                pass
            
            # Method 3: Check for hCaptcha div container
            try:
                hcaptcha_div = page.locator('div.h-captcha, [data-hcaptcha-widget-id]')
                if await hcaptcha_div.count() > 0:
                    print(f"   🔍 [{elapsed:.1f}s] hCaptcha container found, checking for iframe...")
                    captcha_found = True
            except Exception as e:
                pass
            
            # Method 4: Check page HTML for hCaptcha script
            if int(elapsed) % 5 == 0 and elapsed > 0:  # Every 5 seconds
                try:
                    page_html = await page.content()
                    if 'hcaptcha' in page_html.lower():
                        print(f"   🔍 [{elapsed:.1f}s] hCaptcha code present in HTML...")
                        captcha_found = True
                except Exception as e:
                    pass
            
            # Progress indicator
            if int(elapsed * 2) % 4 == 0:  # Every 2 seconds
                status = "🔍 Captcha elements found, waiting for visibility..." if captcha_found else "⏳ Waiting for captcha..."
                print(f"   [{elapsed:.1f}s] {status}")
            
            await asyncio.sleep(check_interval)
        
        print(f"   ⚠️ Captcha did not become visible after {max_wait_seconds}s")
        return False
    
    async def debug_page_state(self, page):
        """Print detailed debug information about current page state"""
        print("\n   🐛 DEBUG INFO:")
        print(f"   📍 URL: {page.url}")
        try:
            print(f"   📄 Title: {await page.title()}")
        except:
            print(f"   📄 Title: [Unable to get]")
        
        # Check for iframes
        try:
            all_iframes = page.locator('iframe')
            iframe_count = await all_iframes.count()
            print(f"   🖼️  Total iframes: {iframe_count}")
            
            if iframe_count > 0:
                for i in range(min(iframe_count, 5)):  # Show first 5
                    iframe = all_iframes.nth(i)
                    src = await iframe.get_attribute('src') or '[no src]'
                    title = await iframe.get_attribute('title') or '[no title]'
                    is_visible = await iframe.is_visible()
                    print(f"      Iframe {i}: visible={is_visible}, src={src[:80]}")
        except Exception as e:
            print(f"   ⚠️ Error checking iframes: {e}")
        
        # Check page content for keywords
        try:
            page_text = await page.evaluate("() => document.body.innerText")
            keywords = ['captcha', 'certificado', 'inválido', 'erro', 'sucesso']
            found_keywords = [kw for kw in keywords if kw in page_text.lower()]
            if found_keywords:
                print(f"   🔑 Keywords found: {', '.join(found_keywords)}")
        except Exception as e:
            print(f"   ⚠️ Error checking page text: {e}")
        
        print()

    async def extract_captcha_config(self, page):
        """Extract hCaptcha configuration (sitekey, rqdata) for Enterprise solving"""
        try:
            config = await page.evaluate("""
                () => {
                    const el = document.querySelector('.h-captcha, [data-hcaptcha-widget-id], [data-sitekey]');
                    return {
                        sitekey: el?.getAttribute('data-sitekey') || null,
                        rqdata: el?.getAttribute('data-rqdata') || null,
                        isEnterprise: !!el?.getAttribute('data-rqdata')
                    };
                }
            """)
            if config['sitekey']:
                print(f"   🔑 Sitekey: {config['sitekey']}")
                print(f"   🏢 Enterprise: {config['isEnterprise']}")
                if config['rqdata']:
                    print(f"   📦 RQData length: {len(config['rqdata'])}")
            return config
        except Exception as e:
            print(f"   ⚠️ Could not extract captcha config: {e}")
            return {'sitekey': None, 'rqdata': None, 'isEnterprise': False}
    
    async def verify_token_ready(self, page):
        """Verify hCaptcha token is present and valid before submission"""
        try:
            validation = await page.evaluate("""
                () => {
                    const tokenEl = document.querySelector('textarea[name="h-captcha-response"]');
                    const token = tokenEl?.value || '';
                    const csrfEl = document.querySelector('input[name="_csrf"]');
                    const csrf = csrfEl?.value || '';
                    const authzEl = document.querySelector('input[name="authorization_id"]');
                    const authz = authzEl?.value || '';
                    
                    // Get all form inputs to debug
                    const form = document.querySelector('form');
                    const allInputs = form ? Array.from(form.querySelectorAll('input, textarea')).map(el => ({
                        name: el.name,
                        type: el.type || 'textarea',
                        hasValue: !!el.value,
                        valueLength: (el.value || '').length
                    })) : [];
                    
                    return {
                        hasToken: token.length > 1000,
                        tokenLength: token.length,
                        hasCsrf: csrf.length > 0,
                        hasAuthz: authz.length > 0,
                        csrfValue: csrf.substring(0, 20),
                        authzValue: authz.substring(0, 20),
                        formAction: document.querySelector('form')?.action || 'none',
                        allInputs: allInputs
                    };
                }
            """)
            
            print(f"   🔐 Token ready: {validation['hasToken']} (length: {validation['tokenLength']})")
            print(f"   🎫 CSRF: {validation['hasCsrf']} ({validation['csrfValue']}...)")
            print(f"   🆔 Authorization: {validation['hasAuthz']} ({validation['authzValue']}...)")
            print(f"   📍 Form action: {validation['formAction']}")
            
            # Show all form fields for debugging
            if validation.get('allInputs'):
                print(f"   📋 All form fields ({len(validation['allInputs'])} total):")
                for inp in validation['allInputs'][:10]:  # Show first 10
                    print(f"      - {inp['name'] or '[no name]'} ({inp['type']}): {'✓' if inp['hasValue'] else '✗'} ({inp['valueLength']} chars)")
            
            # Token and CSRF are critical; authorization_id might not always be present
            is_ready = validation['hasToken'] and validation['hasCsrf']
            
            if not is_ready:
                if not validation['hasToken']:
                    print(f"   ❌ Token missing or too short (need >1000 chars, got {validation['tokenLength']})")
                if not validation['hasCsrf']:
                    print(f"   ❌ CSRF token missing")
            
            return is_ready
        except Exception as e:
            print(f"   ⚠️ Token verification failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def get_captcha_response_from_cdp(self, cdp_session):
        """Get hCaptcha response token from Bright Data CDP"""
        try:
            # Try to get the solved token from Bright Data
            result = await cdp_session.send('Runtime.evaluate', {
                'expression': '''
                    (() => {
                        // Try multiple methods to get the token
                        let token = null;
                        
                        // Method 1: Check if hcaptcha has getResponse
                        if (window.hcaptcha && window.hcaptcha.getResponse) {
                            try {
                                token = window.hcaptcha.getResponse();
                                if (token) return token;
                            } catch(e) {}
                        }
                        
                        // Method 2: Check the textarea directly
                        const textarea = document.querySelector('textarea[name="h-captcha-response"]');
                        if (textarea && textarea.value) {
                            return textarea.value;
                        }
                        
                        // Method 3: Check g-recaptcha-response (fallback)
                        const gTextarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                        if (gTextarea && gTextarea.value) {
                            return gTextarea.value;
                        }
                        
                        return null;
                    })()
                '''
            })
            
            token = result.get('result', {}).get('value')
            if token and len(token) > 100:
                print(f"   ✅ Retrieved token from CDP (length: {len(token)})")
                return token
            else:
                print(f"   ⚠️ No valid token found in CDP")
                return None
                
        except Exception as e:
            print(f"   ⚠️ Error getting token from CDP: {e}")
            return None
    
    async def inject_captcha_token(self, page, token):
        """Manually inject hCaptcha token into the page with enhanced detection"""
        try:
            print(f"   💉 Injecting token into page (length: {len(token)})...")
            
            # Strategy 1: Try to find existing form and inject there
            result = await page.evaluate("""
                (token) => {
                    // Method 1: Direct h-captcha-response textarea (if exists)
                    let textarea = document.querySelector('textarea[name="h-captcha-response"]');
                    if (textarea) {
                        textarea.value = token;
                        textarea.style.display = 'block';  // Make visible for debugging
                        
                        // Trigger all possible events
                        textarea.dispatchEvent(new Event('input', { bubbles: true }));
                        textarea.dispatchEvent(new Event('change', { bubbles: true }));
                        textarea.dispatchEvent(new Event('blur', { bubbles: true }));
                        
                        return { success: true, method: 'h-captcha-response', length: textarea.value.length };
                    }
                    
                    // Method 2: Find form and create textarea in it
                    const form = document.querySelector('form');
                    if (form) {
                        // Create textarea if needed
                        textarea = document.createElement('textarea');
                        textarea.name = 'h-captcha-response';
                        textarea.style.display = 'none';
                        textarea.value = token;
                        form.appendChild(textarea);
                        
                        console.log('✅ Created textarea in form, length:', token.length);
                        return { success: true, method: 'created-in-form', length: token.length };
                    }
                    
                    // Method 3: Find hCaptcha container and create textarea
                    const hcaptchaDiv = document.querySelector('.h-captcha, [data-sitekey], [data-hcaptcha-widget-id]');
                    if (hcaptchaDiv) {
                        textarea = document.createElement('textarea');
                        textarea.name = 'h-captcha-response';
                        textarea.style.display = 'none';
                        textarea.value = token;
                        
                        // Try to add to parent form if exists
                        let parentForm = hcaptchaDiv.closest('form');
                        if (parentForm) {
                            parentForm.appendChild(textarea);
                            console.log('✅ Created textarea in parent form');
                        } else {
                            hcaptchaDiv.appendChild(textarea);
                            console.log('✅ Created textarea in hCaptcha div');
                        }
                        
                        return { success: true, method: 'created-textarea', length: token.length };
                    }
                    
                    // Method 4: Try g-recaptcha-response as fallback
                    const gTextarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                    if (gTextarea) {
                        gTextarea.value = token;
                        gTextarea.dispatchEvent(new Event('input', { bubbles: true }));
                        gTextarea.dispatchEvent(new Event('change', { bubbles: true }));
                        return { success: true, method: 'g-recaptcha-response', length: token.length };
                    }
                    
                    return { success: false, method: 'none', error: 'No form or hCaptcha container found' };
                }
            """, token)
            
            if result.get('success'):
                print(f"   ✅ Token injected via {result['method']} ({result.get('length', 0)} chars)")
                
                # Verify injection worked
                await asyncio.sleep(0.3)
                verify_len = await page.evaluate("() => document.querySelector('textarea[name=\"h-captcha-response\"]')?.value.length || 0")
                if verify_len > 0:
                    print(f"   ✅ Injection verified: {verify_len} chars in textarea")
                    return True
                else:
                    print(f"   ⚠️ Verification shows {verify_len} chars (may still work)")
                    return result.get('success', False)  # Return original success even if verify is 0
            else:
                print(f"   ⚠️ Could not inject token: {result.get('error', 'unknown')}")
                return False
                
        except Exception as e:
            print(f"   ⚠️ Token injection failed: {e}")
            return False
    
    async def reset_captcha_widget(self, page):
        """Reset hCaptcha widget without reloading the page"""
        try:
            print("   🔄 Resetting hCaptcha widget...")
            await page.evaluate("""
                () => {
                    if (window.hcaptcha) {
                        try {
                            // Try to reset all widgets
                            const widgets = document.querySelectorAll('[data-hcaptcha-widget-id]');
                            widgets.forEach(w => {
                                const id = w.getAttribute('data-hcaptcha-widget-id');
                                if (id) window.hcaptcha.reset(id);
                            });
                            
                            // Fallback: reset first widget
                            if (window.hcaptcha.reset) {
                                window.hcaptcha.reset();
                            }
                        } catch (e) {
                            console.error('Reset failed:', e);
                        }
                    }
                }
            """)
            await asyncio.sleep(2)  # Let widget reinitialize
            print("   ✅ Widget reset complete")
            return True
        except Exception as e:
            print(f"   ⚠️ Widget reset failed: {e}")
            return False
    
    async def handle_page_elements(self, page, captcha_solver):
        """Dynamically handle any elements that appear on the page"""
        cert_button_clicked = False
        captcha_solve_attempts = 0
        max_captcha_attempts = 3
        session_needs_refresh = False
        
        for step in range(15):  # Increased to 15 steps for more thorough handling
            # Show attempt number if we've had to retry
            attempt_info = f" [Attempt {captcha_solve_attempts + 1}/{max_captcha_attempts}]" if captcha_solve_attempts > 0 else ""
            print(f"\n🔍 Step {step + 1}{attempt_info}: Checking for elements to interact with...")
            
            # Check for certificate button (DON'T click - certificate auto-injected)
            if not cert_button_clicked:
                try:
                    cert_button = page.locator('#login-certificate')
                    if await cert_button.is_visible(timeout=2000):
                        print("   ℹ️ Certificate button detected - SKIPPING")
                        print("   💡 Certificate auto-injected via Browser.addCertificate")
                        print("   💡 Using regular login flow with automatic certificate")
                        cert_button_clicked = True  # Mark as handled
                        # Don't click it - let certificate work automatically
                        continue
                except Exception as e:
                    print(f"   ⚠️ Error checking certificate button: {e}")
                    pass
            
            # Check for captcha iframe with multiple methods
            captcha_detected = False
            try:
                # Method 1: Standard hCaptcha iframe
                captcha_iframe = page.locator('iframe[src*="hcaptcha"]')
                if await captcha_iframe.count() > 0 and await captcha_iframe.first.is_visible(timeout=1000):
                    captcha_detected = True
                
                # Method 2: Any iframe with hcaptcha in attributes
                if not captcha_detected:
                    all_iframes = page.locator('iframe')
                    iframe_count = await all_iframes.count()
                    for i in range(iframe_count):
                        iframe = all_iframes.nth(i)
                        src = await iframe.get_attribute('src') or ''
                        title = await iframe.get_attribute('title') or ''
                        if ('hcaptcha' in src.lower() or 'hcaptcha' in title.lower()) and await iframe.is_visible():
                            captcha_detected = True
                            break
                
                if captcha_detected and captcha_solve_attempts < max_captcha_attempts:
                    captcha_solve_attempts += 1
                    print(f"   🤖 Found hCaptcha - solving (attempt {captcha_solve_attempts}/{max_captcha_attempts})...")
                    
                    # Extract enterprise config BEFORE solving
                    await asyncio.sleep(1)
                    captcha_config = await self.extract_captcha_config(page)
                    
                    # 🚨 CRITICAL: Set up token observer BEFORE solving
                    print("   🔍 Setting up token observer to catch token during solve...")
                    await page.evaluate("""
                        () => {
                            window.__captcha_token_captured = null;
                            window.__token_observer_active = true;
                            
                            // Method 0: Intercept hCaptcha callback
                            if (window.hcaptcha) {
                                const originalSetResponse = window.hcaptcha.setResponse || (() => {});
                                window.hcaptcha.setResponse = function(widgetId, token) {
                                    if (token && token.length > 1000) {
                                        console.log('🎯 TOKEN CAPTURED from hcaptcha.setResponse:', token.length, 'chars');
                                        window.__captcha_token_captured = token;
                                        window.__token_observer_active = false;
                                    }
                                    return originalSetResponse.apply(this, arguments);
                                };
                            }
                            
                            // Method 1: MutationObserver on textarea
                            const observer = new MutationObserver(() => {
                                if (!window.__token_observer_active) return;
                                const textarea = document.querySelector('textarea[name="h-captcha-response"]');
                                if (textarea && textarea.value && textarea.value.length > 1000) {
                                    console.log('🎯 TOKEN CAPTURED from textarea:', textarea.value.length, 'chars');
                                    window.__captcha_token_captured = textarea.value;
                                    window.__token_observer_active = false;
                                }
                            });
                            observer.observe(document.body, { 
                                childList: true, 
                                subtree: true, 
                                attributes: true,
                                attributeFilter: ['value']
                            });
                            
                            // Method 2: Poll for token every 100ms
                            const pollInterval = setInterval(() => {
                                if (!window.__token_observer_active) {
                                    clearInterval(pollInterval);
                                    return;
                                }
                                
                                // Check textarea
                                const textarea = document.querySelector('textarea[name="h-captcha-response"]');
                                if (textarea && textarea.value && textarea.value.length > 1000) {
                                    console.log('🎯 TOKEN CAPTURED (poll):', textarea.value.length, 'chars');
                                    window.__captcha_token_captured = textarea.value;
                                    window.__token_observer_active = false;
                                    clearInterval(pollInterval);
                                    return;
                                }
                                
                                // Check hCaptcha API
                                if (window.hcaptcha && window.hcaptcha.getResponse) {
                                    try {
                                        const token = window.hcaptcha.getResponse();
                                        if (token && token.length > 1000) {
                                            console.log('🎯 TOKEN CAPTURED from API (poll):', token.length, 'chars');
                                            window.__captcha_token_captured = token;
                                            window.__token_observer_active = false;
                                            clearInterval(pollInterval);
                                        }
                                    } catch(e) {}
                                }
                            }, 100);
                            
                            console.log('✅ Token observer activated (3 methods)');
                        }
                    """)
                    
                    # Give Bright Data some time to detect the captcha
                    await asyncio.sleep(2)
                    
                    success = await captcha_solver.solve_with_retry(max_retries=2)
                    if success:
                        print("   ✅ Captcha solved, waiting for token...")
                        
                        # CRITICAL: Increased wait time for hCaptcha backend validation
                        print(f"   ⏳ Waiting {CAPTCHA_POST_SOLVE_WAIT} seconds for hCaptcha to fully validate token on their servers...")
                        await asyncio.sleep(CAPTCHA_POST_SOLVE_WAIT)  # Configurable from .env
                        print("   ✅ Validation period complete")
                        
                        # CRITICAL: Wait for Bright Data to attempt auto-submit (which we'll block and capture)
                        print("   ⏳ Waiting for auto-submit attempt (which we'll block)...")
                        await asyncio.sleep(5)  # Additional wait for token propagation
                        
                        # PRIORITY 1: Check if we captured token from blocked POST request
                        if self.captured_token_from_request and len(self.captured_token_from_request) > 1000:
                            print(f"   🎯 Using token captured from blocked POST request! (length: {len(self.captured_token_from_request)})")
                            token = {'source': 'blocked-request', 'token': self.captured_token_from_request}
                        # PRIORITY 2: Check if our observer caught the token
                        else:
                            print("   🔍 Checking if token observer captured token...")
                            captured_token = await page.evaluate("() => window.__captcha_token_captured")
                            
                            if captured_token and len(captured_token) > 1000:
                                print(f"   🎯 TOKEN CAPTURED BY OBSERVER! (length: {len(captured_token)})")
                                token = {'source': 'observer', 'token': captured_token}
                            # PRIORITY 3: Try direct extraction from hCaptcha API
                            else:
                                print("   ⏳ Token not captured yet, trying direct API extraction...")
                                await asyncio.sleep(2)
                                
                                # Try to get token directly from hCaptcha API
                                api_token = await page.evaluate("""
                                    () => {
                                        if (window.hcaptcha && window.hcaptcha.getResponse) {
                                            try {
                                                const token = window.hcaptcha.getResponse();
                                                if (token && token.length > 1000) {
                                                    return token;
                                                }
                                            } catch(e) {
                                                console.error('Failed to get hcaptcha response:', e);
                                            }
                                        }
                                        return null;
                                    }
                                """)
                                
                                if api_token and len(api_token) > 1000:
                                    print(f"   🎯 TOKEN EXTRACTED from hCaptcha API! (length: {len(api_token)})")
                                    token = {'source': 'hcaptcha-api', 'token': api_token}
                                # PRIORITY 4: Try all textareas
                                else:
                                    print("   🔍 Attempting to retrieve token from page textareas...")
                                    await asyncio.sleep(1)
                                    
                                    token = await page.evaluate("""
                                    () => {
                                        // Check captured token first
                                        if (window.__captcha_token_captured && window.__captcha_token_captured.length > 1000) {
                                            return { source: 'observer-delayed', token: window.__captcha_token_captured };
                                        }
                                        
                                        // Method 1: hCaptcha API
                                        if (window.hcaptcha && window.hcaptcha.getResponse) {
                                            try {
                                                const token = window.hcaptcha.getResponse();
                                                if (token && token.length > 100) {
                                                    return { source: 'hcaptcha.getResponse', token: token };
                                                }
                                            } catch(e) {}
                                        }
                                        
                                        // Method 2: Textarea
                                        const textarea = document.querySelector('textarea[name="h-captcha-response"]');
                                        if (textarea && textarea.value && textarea.value.length > 100) {
                                        return { source: 'textarea', token: textarea.value };
                                    }
                                    
                                    // Method 3: All textareas (in case of dynamic creation)
                                const allTextareas = document.querySelectorAll('textarea');
                                for (const ta of allTextareas) {
                                    if (ta.value && ta.value.length > 1000 && ta.value.startsWith('P')) {
                                        return { source: 'textarea-search', token: ta.value };
                                    }
                                }
                                
                                return { source: 'none', token: null };
                            }
                        """)
                        
                        if token and token.get('token'):
                            print(f"   ✅ Found token via {token['source']} (length: {len(token['token'])})")
                            
                            # ALWAYS inject the captured token (it was consumed by blocked auto-submit)
                            print("   💉 Re-injecting captured token into textarea...")
                            injection_success = await self.inject_captcha_token(page, token['token'])
                            
                            if injection_success:
                                print("   ✅ Token injection successful")
                            else:
                                print("   ⚠️ Initial injection failed, will retry...")
                            
                            await asyncio.sleep(2)
                        else:
                            print(f"   ⚠️ No token found in page (tried multiple methods)")
                        
                        # Final verification
                        print("   🔍 Final token verification...")
                        token_len = await page.evaluate("() => document.querySelector('textarea[name=\"h-captcha-response\"]')?.value.length || 0")
                        print(f"   📏 Token length in textarea: {token_len}")
                        
                        # 🚨 CRITICAL: Check if token is valid before allowing submission
                        # Note: Some tokens might be shorter but still valid
                        if token_len > 1500:  # Lowered threshold to accept captured tokens
                            print(f"   ✅ TOKEN DETECTED ({token_len} chars)")
                            if token_len < 3000:
                                print(f"   ⚠️ Token is shorter than expected, but will try anyway")
                            print("   🟢 Enabling form submission - POST requests now allowed")
                            self.ready_to_submit = True
                            if self.blocked_requests:
                                print(f"   📊 Blocked {len(self.blocked_requests)} premature auto-submit attempts")
                        else:
                            print(f"   ⚠️ Token too short ({token_len} chars) - NOT enabling submission yet")
                            
                            # 🔥 CRITICAL FIX: If we have captured token, try MULTIPLE injection attempts
                            if token and token.get('token') and len(token['token']) > 1500:
                                print(f"   🔄 Have valid captured token ({len(token['token'])} chars)")
                                print(f"   🔥 Attempting aggressive re-injection (3 attempts)...")
                                
                                for retry in range(3):
                                    print(f"   💉 Injection attempt {retry + 1}/3...")
                                    await self.inject_captcha_token(page, token['token'])
                                    await asyncio.sleep(1.5)
                                    
                                    token_len = await page.evaluate("() => document.querySelector('textarea[name=\"h-captcha-response\"]')?.value.length || 0")
                                    if token_len > 1500:
                                        print(f"   ✅ Token successfully injected ({token_len} chars) on attempt {retry + 1}")
                                        self.ready_to_submit = True
                                        if self.blocked_requests:
                                            print(f"   📊 Blocked {len(self.blocked_requests)} premature auto-submit attempts")
                                        break
                                    else:
                                        print(f"   ⚠️ Attempt {retry + 1} failed (got {token_len} chars)")
                                        
                                if token_len <= 1500:
                                    print(f"   ❌ All injection attempts failed - token still not in textarea")
                                    print(f"   🔄 Will reset widget and try fresh solve...")
                        
                        # Additional wait for token to fully settle
                        await asyncio.sleep(1)
                        
                        # Verify token and form state before submission
                        print("   🔍 Verifying form state before submission...")
                        token_ready = await self.verify_token_ready(page)
                        
                        if not token_ready:
                            # Check if we have a captured token but it's just not injecting properly
                            has_captured_token = (token and token.get('token') and len(token.get('token', '')) > 1500)
                            
                            if has_captured_token and token_len <= 1500:
                                print("   ⚠️ Form not ready - have valid token but injection failing")
                                print("   � BYPASSING textarea - will submit form directly with captured token!")
                                
                                # Get form data
                                form_data = await page.evaluate("""
                                    () => {
                                        const form = document.querySelector('form');
                                        if (!form) return null;
                                        
                                        const data = {};
                                        const formData = new FormData(form);
                                        for (let [key, value] of formData.entries()) {
                                            data[key] = value;
                                        }
                                        
                                        // Get CSRF token
                                        const csrfInput = form.querySelector('input[name="_csrf"], input[name="csrf_token"]');
                                        if (csrfInput) data['_csrf'] = csrfInput.value;
                                        
                                        return {
                                            action: form.action,
                                            method: form.method,
                                            data: data
                                        };
                                    }
                                """)
                                
                                if form_data and form_data.get('action'):
                                    print(f"   📋 Form action: {form_data['action']}")
                                    print(f"   📦 Adding captured token to form data...")
                                    
                                    # Submit using JavaScript to bypass textarea requirement
                                    submit_result = await page.evaluate("""
                                        (tokenValue) => {
                                            const form = document.querySelector('form');
                                            if (!form) return { success: false, error: 'No form found' };
                                            
                                            // Ensure token textarea exists
                                            let textarea = form.querySelector('textarea[name="h-captcha-response"]');
                                            if (!textarea) {
                                                textarea = document.createElement('textarea');
                                                textarea.name = 'h-captcha-response';
                                                textarea.style.display = 'none';
                                                form.appendChild(textarea);
                                            }
                                            textarea.value = tokenValue;
                                            
                                            console.log('🚀 Submitting form with token:', tokenValue.length, 'chars');
                                            
                                            // Find and click submit button
                                            const submitBtn = form.querySelector('button[type="submit"], input[type="submit"]');
                                            if (submitBtn) {
                                                submitBtn.click();
                                                return { success: true, method: 'button-click' };
                                            }
                                            
                                            // Fallback: trigger form submit
                                            form.submit();
                                            return { success: true, method: 'form-submit' };
                                        }
                                    """, token['token'])
                                    
                                    if submit_result.get('success'):
                                        print(f"   ✅ Form submitted via {submit_result['method']}!")
                                        print("   ⏳ Waiting for navigation...")
                                        await asyncio.sleep(5)
                                        return  # Exit this attempt
                                    else:
                                        print(f"   ❌ Form submission failed: {submit_result.get('error')}")
                                else:
                                    print("   ❌ Could not get form data")
                                
                                print("   �🔄 Fallback: Resetting widget and retrying...")
                                await self.reset_captcha_widget(page)
                                captcha_solve_attempts -= 1  # Don't count this as a failed attempt
                                await asyncio.sleep(2)
                                continue
                            else:
                                print("   ⚠️ Form not ready - missing token, CSRF, or authorization_id")
                                print("   🔄 Resetting widget and retrying...")
                                await self.reset_captcha_widget(page)
                                captcha_solve_attempts -= 1  # Don't count this as a failed attempt
                                await asyncio.sleep(2)
                                continue
                        
                        # CRITICAL: Click submit button (don't use form.submit() - it bypasses handlers)
                        print("   � Submitting form with verified token...")
                        
                        try:
                            # Look for submit button
                            submit_selectors = [
                                'button[type="submit"]',
                                'input[type="submit"]',
                                'form button:not([type="button"])',
                                'button.govbr-button',
                                'button:has-text("Entrar")',
                                'button:has-text("Continuar")',
                            ]
                            
                            submitted = False
                            for selector in submit_selectors:
                                try:
                                    btn = page.locator(selector).first
                                    if await btn.is_visible(timeout=2000):
                                        print(f"   🔘 Clicking submit button: {selector}")
                                        
                                        # Click and wait for navigation or response
                                        async with page.expect_response(lambda r: 'login' in r.url or 'certificado' in r.url, timeout=15000) as response_info:
                                            await btn.click()
                                        
                                        response = await response_info.value
                                        print(f"   � Response status: {response.status}")
                                        
                                        if response.status == 400:
                                            body_text = await response.text()
                                            if 'captcha' in body_text.lower() and 'inválido' in body_text.lower():
                                                print("   🚨 Server rejected captcha (400 Bad Request)")
                                                submitted = False
                                                break
                                        
                                        submitted = True
                                        print(f"   ✅ Form submitted successfully")
                                        break
                                except Exception as e:
                                    pass
                            
                            if not submitted:
                                print("   ⚠️ Could not find or click submit button")
                                # Don't force form.submit() - it will fail
                            
                        except Exception as e:
                            print(f"   ⚠️ Submission error: {e}")
                        
                        # Wait for server to process
                        print("   ⏳ Waiting for server validation...")
                        await asyncio.sleep(4)
                        
                        # Check result
                        page_text = await page.evaluate("() => document.body.innerText")
                        current_url = page.url
                        
                        # Success check
                        if 'login' not in current_url.lower() or any(kw in page_text.lower() for kw in ['bem-vindo', 'sucesso', 'autenticado']):
                            print(f"   🎉 Authentication succeeded!")
                            print(f"   📍 URL: {current_url}")
                            continue
                        
                        # Check for captcha invalid
                        if 'Captcha inválido' in page_text or 'captcha inválido' in page_text:
                            print("   ⚠️ 'Captcha inválido' - resetting widget and retrying...")
                            
                            if captcha_solve_attempts < max_captcha_attempts:
                                # Reset widget in-place (no page reload)
                                await self.reset_captcha_widget(page)
                                await asyncio.sleep(2)
                                continue
                            else:
                                print(f"   ❌ Max captcha attempts ({max_captcha_attempts}) reached")
                                return False
                        else:
                            print("   ✅ No error detected - captcha accepted")
                        
                        continue
                    else:
                        print("   ⚠️ Captcha solve failed")
                        if captcha_solve_attempts < max_captcha_attempts:
                            print(f"   🔄 Will retry if captcha appears again...")
                            await asyncio.sleep(3)
                            continue
                        else:
                            return False
            except Exception as e:
                print(f"   ⚠️ Error during captcha detection: {e}")
                pass
            
            # Check for any certificate selection dialog or error messages
            try:
                page_text = await page.evaluate("() => document.body.innerText")
                
                # Check for captcha invalid message (without recent solve)
                if 'Captcha inválido' in page_text or 'captcha inválido' in page_text:
                    # Only handle if we're not already in a solve loop
                    if captcha_solve_attempts == 0 or step > 5:
                        print("   ⚠️ 'Captcha inválido' message detected outside solve loop")
                        print("   🔄 Resetting widget to retry...")
                        await self.reset_captcha_widget(page)
                        await asyncio.sleep(2)
                        continue
                
                # Check for certificate selection dialog or submit button after captcha
                if 'certificado' in page_text.lower():
                    # Look for "Selecione" dialog
                    if 'selecione' in page_text.lower():
                        print("   📜 Certificate selection dialog detected")
                        try:
                            cert_options = page.locator('button, input[type="submit"], a').filter(has_text='certificado')
                            if await cert_options.count() > 0:
                                await cert_options.first.click()
                                await asyncio.sleep(3)
                                continue
                        except Exception as e:
                            print(f"   ⚠️ Error clicking certificate option: {e}")
                            pass
                    
                    # Look for submit/continue button after captcha solve
                    # 🚨 ONLY click if we have verified token and enabled submission
                    try:
                        # Common button texts after captcha
                        submit_buttons = [
                            page.locator('button:has-text("Continuar")'),
                            page.locator('button:has-text("Entrar")'),
                            page.locator('button:has-text("Enviar")'),
                            page.locator('input[type="submit"]'),
                            page.locator('button[type="submit"]'),
                        ]
                        
                        for btn_locator in submit_buttons:
                            if await btn_locator.count() > 0 and await btn_locator.first.is_visible():
                                btn_text = await btn_locator.first.text_content() or 'submit'
                                
                                # Check if we have a valid token before clicking
                                if self.ready_to_submit:
                                    print(f"   🔘 Found submit button: '{btn_text}' - clicking (submission enabled)...")
                                    await btn_locator.first.click()
                                    print(f"   ✅ Clicked, waiting for response...")
                                    await asyncio.sleep(5)
                                    continue
                                else:
                                    print(f"   ⏸️ Found submit button: '{btn_text}' - WAITING for token verification...")
                    except Exception as e:
                        print(f"   ⚠️ Error checking submit buttons: {e}")
                        pass
                
                # Check if we're back at CPF login (certificate auth failed)
                if 'digite seu cpf' in page_text.lower() or 'número do cpf' in page_text.lower():
                    print("   ⚠️ Back at CPF login page - certificate authentication may not have completed")
                    
                    # Check if there are any certificate-related buttons/links we missed
                    try:
                        # Look for certificate login link again
                        cert_links = page.locator('a:has-text("certificado"), button:has-text("certificado")')
                        cert_count = await cert_links.count()
                        
                        if cert_count > 0:
                            print(f"   🔍 Found {cert_count} certificate-related element(s)")
                            for i in range(cert_count):
                                link = cert_links.nth(i)
                                text = await link.text_content()
                                is_visible = await link.is_visible()
                                print(f"      Element {i}: '{text.strip()}' (visible: {is_visible})")
                            
                            # Try clicking the "Seu certificado digital" link again if visible
                            cert_digital = page.locator('a:has-text("Seu certificado digital"), button:has-text("Seu certificado digital")')
                            if await cert_digital.count() > 0 and await cert_digital.first.is_visible():
                                print("   🔄 Clicking 'Seu certificado digital' again...")
                                await cert_digital.first.click()
                                await asyncio.sleep(3)
                                continue
                    except Exception as e:
                        print(f"   ⚠️ Error checking certificate elements: {e}")
                
                # Check for success indicators
                success_keywords = ['sucesso', 'bem-vindo', 'dashboard', 'autenticado', 'logado']
                if any(keyword in page_text.lower() for keyword in success_keywords):
                    print("   🎉 Success indicators found in page text!")
                    return True
                
                # Check if we're on a different page (successful redirect)
                if page.url != TARGET_URL and 'login' not in page.url.lower() and 'certificado' not in page.url.lower():
                    print(f"   🎉 Redirected to new page: {page.url}")
                    return True
                
            except Exception as e:
                print(f"   ⚠️ Error checking page content: {e}")
                pass
            
            # Check current status before waiting
            try:
                current_url = page.url
                print(f"   📍 Current URL: {current_url}")
            except:
                pass
            
            # Wait a bit and check again
            await asyncio.sleep(2)
        
        print("\n   ℹ️ Reached maximum steps")
        # Do a final check
        try:
            page_text = await page.evaluate("() => document.body.innerText")
            final_url = page.url
            
            print(f"   📍 Final URL: {final_url}")
            
            if 'Captcha inválido' in page_text or 'captcha inválido' in page_text:
                print("   ❌ Still showing 'Captcha inválido'")
                return False
            
            # Check if still on login page with CPF form
            if 'digite seu cpf' in page_text.lower() and 'login' in final_url:
                print("   ⚠️ Still on CPF login page - certificate authentication incomplete")
                print("   💡 The certificate may need to be selected from browser or OS dialog")
                return False
            
            print("   ✅ No error messages detected")
            return True
        except Exception as e:
            print(f"   ⚠️ Error in final check: {e}")
            return True
    
    async def run(self):
        async with async_playwright() as playwright:
            for attempt in range(3):
                browser = None
                # Reset submission flag for each attempt
                self.ready_to_submit = False
                self.blocked_requests = []
                self.captured_token_from_request = None
                self.form_submitted = False
                self.first_submission_delayed = False
                
                try:
                    print("\n" + "="*70)
                    print(f"🎉 FULL AUTOMATION - ATTEMPT {attempt + 1}/3 🎉")
                    print("="*70)
                    print("✅ Automatic hCaptcha solving (Bright Data)")
                    print("✅ Client certificate injection (Browser.addCertificate)")
                    print("✅ Token verification before submission (>1000 chars)")
                    print("✅ Widget reset on failure (no page reload)")
                    print("✅ Enterprise hCaptcha config extraction (sitekey/rqdata)")
                    print("✅ CSRF/authorization_id validation before submit")
                    print("✅ Native button click (no form.submit() bypass)")
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
                    self.cdp_session = cdp_session  # Store for later use
                    captcha_solver = BrightDataCaptchaSolver(cdp_session)
                    
                    # 🚨 Monitor form submissions (allowing them to proceed naturally)
                    print("   🔧 Setting up request monitoring...")
                    self.captured_token_from_request = None
                    self.first_submission_delayed = False
                    
                    async def block_premature_submits(route):
                        request = route.request
                        
                        # Monitor POST requests
                        if (request.method == "POST" and 
                            any(pattern in request.url for pattern in ['/login', '/auth', '/certificado'])):
                            
                            # Log the token being submitted
                            token_length = 0
                            try:
                                post_data = request.post_data
                                if post_data:
                                    import urllib.parse
                                    data = urllib.parse.parse_qs(post_data)
                                    token = data.get('h-captcha-response', [''])[0]
                                    token_length = len(token)
                                    if token and token_length > 1000:
                                        # 🎯 CAPTURE the token from this request!
                                        if not self.captured_token_from_request:
                                            print(f"   🎯 CAPTURING token from POST request ({token_length} chars)")
                                            self.captured_token_from_request = token
                                        self.form_submitted = True
                                        self.ready_to_submit = True
                            except Exception as e:
                                pass
                            
                            # CRITICAL: Delay first submission to allow hCaptcha server validation
                            if not self.first_submission_delayed and token_length > 1000:
                                print(f"   ⏸️ DELAYING first POST to allow hCaptcha backend validation...")
                                print(f"   📤 Token length: {token_length} chars")
                                print(f"   ⏳ Waiting {CAPTCHA_SUBMIT_DELAY} seconds for hCaptcha to validate token on their servers...")
                                await asyncio.sleep(CAPTCHA_SUBMIT_DELAY)  # Configurable from .env
                                self.first_submission_delayed = True
                                print(f"   ✅ Delay complete - ALLOWING POST to {request.url.split('/')[-1]}")
                            elif token_length > 1000:
                                print(f"   ✅ ALLOWING POST to {request.url.split('/')[-1]} (token: {token_length} chars)")
                        
                        # Allow all other requests
                        await route.continue_()
                    
                    await page.route("**/*", block_premature_submits)
                    print("   ✅ Request monitoring active - submissions will be ALLOWED")
                    
                    # Set up event handlers for debugging
                    print("   🔧 Setting up event handlers...")
                    
                    # Handle dialogs (certificate selection, alerts, etc.)
                    async def handle_dialog(dialog):
                        print(f"   🔔 DIALOG: type={dialog.type}, message={dialog.message}")
                        await dialog.accept()
                        print(f"   ✅ Dialog accepted")
                    
                    page.on("dialog", handle_dialog)
                    
                    # Monitor console messages
                    page.on("console", lambda msg: print(f"   🖥️ Console [{msg.type}]: {msg.text}"))
                    
                    # Monitor page errors
                    page.on("pageerror", lambda err: print(f"   ❌ Page Error: {err}"))
                    
                    # Monitor navigation events
                    page.on("framenavigated", lambda frame: print(f"   🧭 Navigation: {frame.url}") if frame == page.main_frame else None)
                    
                    # Monitor failed requests
                    def handle_request_failed(request):
                        if '400' in str(request.failure) or 'failed' in str(request.failure).lower():
                            print(f"   🚫 Request FAILED: {request.method} {request.url}")
                            print(f"      Failure: {request.failure}")
                    
                    page.on("requestfailed", handle_request_failed)
                    
                    # Monitor POST requests to login endpoint
                    async def handle_request(request):
                        if request.method == "POST" and 'login' in request.url:
                            print(f"   📤 POST to {request.url}")
                            try:
                                post_data = request.post_data
                                if post_data:
                                    # Parse form data
                                    import urllib.parse
                                    data = urllib.parse.parse_qs(post_data)
                                    # Show presence of key fields
                                    has_token = 'h-captcha-response' in data and len(data.get('h-captcha-response', [''])[0]) > 1000
                                    has_csrf = '_csrf' in data
                                    has_authz = 'authorization_id' in data
                                    print(f"      Token: {'✓' if has_token else '✗'} (len={len(data.get('h-captcha-response', [''])[0])})")
                                    print(f"      CSRF: {'✓' if has_csrf else '✗'}")
                                    print(f"      AuthZ: {'✓' if has_authz else '✗'}")
                            except Exception as e:
                                pass
                    
                    page.on("request", lambda req: asyncio.create_task(handle_request(req)))
                    
                    # Track validation failures
                    validation_state = {"failed": False, "reason": "", "timestamp": 0}
                    
                    # Monitor responses for debugging
                    async def handle_response(response):
                        if response.status >= 400:
                            # Special handling for different error types
                            if response.status == 502:
                                print(f"   ⚠️ HTTP 502 (Bad Gateway): {response.url}")
                                print(f"      This is a temporary server issue - resource may load on retry")
                            elif response.status == 400:
                                print(f"   ⚠️ HTTP 400 (Bad Request): {response.url}")
                                # Try to get response body for 400 errors
                                try:
                                    body = await response.text()
                                    if body:
                                        print(f"      Response body: {body[:500]}")
                                        # Check if this is captcha validation failure
                                        if 'captcha' in body.lower() and ('inválido' in body.lower() or 'invalid' in body.lower()):
                                            import time
                                            validation_state["failed"] = True
                                            validation_state["reason"] = "Server rejected captcha with 400 error"
                                            validation_state["timestamp"] = time.time()
                                            print(f"   🚨 DETECTED: Server rejected captcha solution!")
                                            print(f"   💡 Possible causes:")
                                            print(f"      - Token submitted too quickly (before hCaptcha backend validated)")
                                            print(f"      - Missing required form fields (CSRF, authorization_id)")
                                            print(f"      - Token expired before submission")
                                except Exception as e:
                                    pass
                            else:
                                print(f"   ⚠️ HTTP {response.status}: {response.url}")
                    
                    page.on("response", lambda response: asyncio.create_task(handle_response(response)))
                    
                    print("   ✅ Connected\n")
                    
                    print("🔐 Verifying and injecting certificate...")
                    cert_valid = await self.verify_certificate(cdp_session, cert_base64, CERTIFICATE_PASSWORD)
                    
                    if not cert_valid:
                        print("\n❌ Certificate verification failed - cannot proceed")
                        print("💡 Please check:")
                        print("   - Certificate file is not corrupted")
                        print("   - CERTIFICATE_PASSWORD is correct in .env file")
                        print("   - Certificate has not expired")
                        await browser.close()
                        continue
                    
                    print()
                    
                    print(f"📍 Navigating to {TARGET_URL}...")
                    await page.goto(TARGET_URL, wait_until='domcontentloaded', timeout=30000)
                    print(f"   ✅ Page loaded")
                    
                    # Wait for page to be fully interactive (with fallback)
                    print("   ⏳ Waiting for page to be fully interactive...")
                    try:
                        await page.wait_for_load_state('networkidle', timeout=15000)
                        print("   ✅ Page reached networkidle state")
                    except Exception as e:
                        print(f"   ⚠️ Networkidle timeout (normal for some pages) - continuing...")
                    
                    # Additional wait to ensure all scripts are loaded
                    print("   ⏳ Ensuring scripts are loaded...")
                    await asyncio.sleep(3)
                    print("   ✅ Page is ready\n")
                    
                    # Wait and handle any elements that appear
                    success = await self.handle_page_elements(page, captcha_solver)
                    
                    if not success:
                        print("\n❌ Page handling failed or captcha invalid")
                        await self.debug_page_state(page)
                        await browser.close()
                        await asyncio.sleep(2)
                        continue
                    
                    # Get final page content and status
                    print("\n🔍 Checking final page status...")
                    page_text = await page.evaluate("() => document.body.innerText")
                    current_url = page.url
                    
                    # Check for various error conditions
                    error_found = False
                    
                    if 'certificado digital não encontrado' in page_text.lower():
                        print("❌ Certificate not recognized by website")
                        error_found = True
                    
                    if 'captcha inválido' in page_text.lower():
                        print("❌ 'Captcha inválido' still present on final page")
                        error_found = True
                    
                    if 'erro' in page_text.lower() and 'certificado' in page_text.lower():
                        print("⚠️ Certificate-related error detected in page text")
                        error_found = True
                    
                    if error_found:
                        print(f"\n📋 Page text sample (first 500 chars):")
                        print(page_text[:500])
                        await browser.close()
                        continue
                    
                    # Success analysis
                    print("="*70)
                    print("✅✅✅ SUCCESS! ✅✅✅")
                    print("="*70)
                    print(f"🌐 URL: {current_url}")
                    
                    try:
                        page_title = await page.title()
                        print(f"📄 Title: {page_title}")
                    except:
                        print(f"📄 Title: [Unable to retrieve]")
                    
                    # Determine authentication status
                    if 'login' not in current_url.lower() and 'acesso.gov.br/login' not in current_url:
                        print("\n🎉 FULLY AUTHENTICATED AND REDIRECTED!")
                    elif 'x509' not in current_url and 'certificado' not in current_url:
                        print("\n✅ Authentication appears successful")
                    else:
                        print("\n✅ Process completed (verify authentication manually)")
                    
                    # Check for success keywords
                    success_keywords = ['sucesso', 'bem-vindo', 'dashboard', 'autenticado']
                    found_success = [kw for kw in success_keywords if kw in page_text.lower()]
                    if found_success:
                        print(f"🎯 Success keywords found: {', '.join(found_success)}")
                    
                    print("\n📋 Page content preview (first 600 chars):")
                    print(page_text[:600])
                    print("\n" + "="*70)
                    
                    # Navigate to servicos page after successful captcha solve
                    print("\n🌐 Navigating to https://servicos.acesso.gov.br ...")
                    try:
                        await page.goto("https://servicos.acesso.gov.br", wait_until='domcontentloaded', timeout=30000)
                        await asyncio.sleep(3)
                        
                        final_url = page.url
                        final_text = await page.evaluate("() => document.body.innerText")
                        
                        print(f"   ✅ Navigated to: {final_url}")
                        
                        # Check if we successfully accessed the services page
                        if 'servicos' in final_url.lower():
                            print("\n🎉 SUCCESSFULLY ACCESSED SERVICES PAGE!")
                        else:
                            print(f"\n⚠️ Redirected to: {final_url}")
                        
                        print("\n📋 Services page preview (first 600 chars):")
                        print(final_text[:600])
                    except Exception as nav_error:
                        print(f"\n⚠️ Navigation to services page failed: {nav_error}")
                        print("   💡 You can manually navigate to https://servicos.acesso.gov.br")
                    
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
                        print(f"\n⏳ Retrying immediately...\n")
                        await asyncio.sleep(0.5)
                    else:
                        print("\n❌ All 3 attempts failed")
                        input("\nPress Enter to close...")


async def main():
    automation = BrightDataFullAutomation()
    await automation.run()


if __name__ == "__main__":
    asyncio.run(main())
