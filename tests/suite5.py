import asyncio, os, sys, re
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
        total = lambda: pg.evaluate("() => parseInt(document.getElementById('allCount').textContent||'0',10)")
        start = await total()
        # card delete on All notes
        await pg.click("#allBtn"); await pg.wait_for_timeout(300)
        await pg.locator("#overviewGrid .card-del").first.click(force=True); await pg.wait_for_timeout(500)
        check("card delete removes one note", await total() == start - 1, (start, await total()))
        check("card delete keeps you on the list", await pg.is_visible("#overviewView"))
        # sidebar delete
        await pg.click("#brand"); await pg.wait_for_timeout(200)
        await pg.click("#allBtn"); await pg.wait_for_timeout(200)
        ex = await total()
        check("sidebar notes have a delete control", await pg.locator("#spaces .tnote-del").count() >= 1)
        if True:
            await pg.locator("#spaces .tnote-del").first.click(force=True); await pg.wait_for_timeout(500)
            check("sidebar delete removes one note", await total() == ex - 1, (ex, await total()))
        # editor delete
        await pg.locator("#spaces strong").first.click(); await pg.wait_for_timeout(400)
        before = await total()
        await pg.click("#deleteNote"); await pg.wait_for_timeout(500)
        check("editor delete still works", await total() == before - 1, (before, await total()))
        check("after delete the editor is closed", await pg.is_hidden("#editorView"))
        # card delete on home overview of a category
        await pg.click("#allBtn"); await pg.wait_for_timeout(300)
        n_before = await total()
        if await pg.locator("#overviewGrid .card-del").count():
            await pg.locator("#overviewGrid .card-del").first.click(force=True); await pg.wait_for_timeout(500)
        check("delete from All notes again", await total() == n_before - 1 or n_before == 0, (n_before, await total()))
        check("no uncaught errors", not errs, errs)
        await b.close()
    print(f"{sum(res)}/{len(res)} passed")
asyncio.run(main())
