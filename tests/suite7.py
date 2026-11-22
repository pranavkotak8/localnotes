# Privacy check: record every network request the page makes during a typical session.
# Passes only if every request goes to this machine (localhost / 127.0.0.1) or is an in-page blob/data URL.
import asyncio, os, sys
from urllib.parse import urlparse
from playwright.async_api import async_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765/index.html"
HERE = os.path.dirname(os.path.abspath(__file__))
res = []
def check(name, ok, detail=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else '  -> ' + str(detail)))
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome", headless=True)
        ctx = await b.new_context(viewport={'width': 1280, 'height': 800}, accept_downloads=True)
        pg = await ctx.new_page()
        hosts = set(); urls = []
        def on_req(r):
            u = r.url; urls.append(u)
            if u.startswith(('blob:', 'data:')): return
            hosts.add(urlparse(u).hostname or u)
        pg.on("request", on_req)
        pg.on("dialog", lambda d: asyncio.ensure_future(d.accept()))
        await pg.goto(URL); await pg.wait_for_timeout(500)
        await pg.set_input_files("#importFile", os.path.join(HERE, "seed_backup.json")); await pg.wait_for_timeout(700)
        await pg.click("#canvasBtn"); await pg.fill("#canvasText", "Buy milk\nSend the deck to Anna"); await pg.wait_for_timeout(200)
        await pg.click("#chatBtn"); await pg.fill("#chatInput", "what did I write about fundraising?"); await pg.click("#chatSend"); await pg.wait_for_timeout(600)
        await pg.click("#exportBtn"); await pg.check('input[name=exf][value=json]')
        async with pg.expect_download():
            await pg.click("#confirmModal")
        await pg.wait_for_timeout(300)
        await pg.click("#themeBtn"); await pg.wait_for_timeout(200)
        await b.close()
        print("hosts contacted:", sorted(hosts) or ["(none)"])
        check("every request stays on this machine", hosts <= {"localhost", "127.0.0.1"}, sorted(hosts - {"localhost", "127.0.0.1"}))
        check("no request to a CDN, font service or analytics", not any(h.endswith(("google.com", "gstatic.com", "jsdelivr.net", "unpkg.com", "cloudflare.com")) for h in hosts))
    print(f"{sum(res)}/{len(res)} passed")
asyncio.run(main())
