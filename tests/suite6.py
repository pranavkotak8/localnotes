import asyncio, os, sys
from playwright.async_api import async_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765/index.html"
HERE = os.path.dirname(os.path.abspath(__file__))
res = []
def check(name, ok, detail=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else '  -> ' + str(detail)))
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome", headless=True)
        pg = await (await b.new_context(viewport={'width': 1280, 'height': 800})).new_page()
        errs = []; pg.on("pageerror", lambda e: errs.append(str(e)))
        pg.on("dialog", lambda d: asyncio.ensure_future(d.accept()))
        await pg.goto(URL); await pg.wait_for_timeout(400)
        await pg.set_input_files("#importFile", os.path.join(HERE, "seed_backup.json")); await pg.wait_for_timeout(700)
        count = lambda: pg.evaluate("() => parseInt(document.getElementById('allCount').textContent||'0',10)")
        await pg.click("#allBtn"); await pg.wait_for_timeout(250)
        check("reset button shows on All notes", await pg.is_visible("#resetAll"))
        await pg.click("#spaces .group-name"); await pg.wait_for_timeout(200)
        check("reset button hidden inside a space", await pg.is_hidden("#resetAll"))
        await pg.click("#allBtn"); await pg.wait_for_timeout(250)
        before = await count(); spaces_before = await pg.locator('#spaces .group').count()
        await pg.click("#resetAll"); await pg.wait_for_timeout(250)
        check("reset asks for RESET", await pg.is_visible("#modal"))
        await pg.fill("#resetWord", "reset"); await pg.click("#confirmModal"); await pg.wait_for_timeout(250)
        check("wrong word keeps notes", await count() == before and await pg.is_visible("#modal"), await count())
        await pg.fill("#resetWord", "RESET"); await pg.click("#confirmModal"); await pg.wait_for_timeout(500)
        check("RESET removes every note", await count() == 0, await count())
        check("empty state shown", "No notes yet" in await pg.inner_text("#overviewGrid"))
        check("spaces are kept", await pg.locator('#spaces .group').count() == spaces_before, (spaces_before, await pg.locator('#spaces .group').count()))
        check("no uncaught errors", not errs, errs)
        await b.close()
    print(f"{sum(res)}/{len(res)} passed")
asyncio.run(main())
