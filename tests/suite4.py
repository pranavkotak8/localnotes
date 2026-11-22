import asyncio, os, re, sys, datetime, json
from playwright.async_api import async_playwright
URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8765/index.html"
HERE = os.path.dirname(os.path.abspath(__file__))
results = []
def check(name, ok, detail=''):
    results.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else '  -> ' + str(detail)))
def nt(pg, t): return pg.locator('#spaces strong').filter(has_text=re.compile('^' + re.escape(t) + '$'))
def key(d): return d.strftime('%Y-%m-%d')
async def main():
    today = datetime.date.today()
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome", headless=True)
        ctx = await b.new_context(viewport={'width': 1280, 'height': 800}, accept_downloads=True)
        pg = await ctx.new_page(); errs = []; dialogs = []
        pg.on("pageerror", lambda e: errs.append(str(e)))
        async def on_dialog(d):
            dialogs.append(d.message); await d.accept()
        pg.on("dialog", lambda d: asyncio.ensure_future(on_dialog(d)))
        await pg.goto(URL); await pg.wait_for_timeout(500)
        await pg.set_input_files("#importFile", os.path.join(HERE, "seed_backup.json")); await pg.wait_for_timeout(800)
        check("seed imported", await pg.locator('#spaces strong').count() >= 6)

        # ---- Markdown single file
        await pg.click("#exportBtn")
        await pg.check('input[name=exf][value=md-file]')
        async with pg.expect_download() as dl:
            await pg.click("#confirmModal")
        d = await dl.value; path = os.path.join(HERE, "out_notes.md"); await d.save_as(path)
        md = open(path, encoding='utf-8').read()
        check("markdown file has front matter", md.startswith('---\ntitle: ') and 'space: "Unsorted"' in md, md[:200])
        check("markdown keeps the note title as heading", '# Pitch deck feedback' in md)
        check("markdown has all notes", md.count('\n---\n') >= 6 * 2 - 1, md.count('---'))

        # ---- Markdown folder (fake directory handle)
        await pg.evaluate("""() => {
          window.__files = {};
          const mk = (path) => ({
            async getDirectoryHandle(name) { return mk(path + '/' + name); },
            async getFileHandle(name) { const p = path + '/' + name;
              return { async createWritable() { let buf = ''; return { async write(t){ buf = t; }, async close(){ window.__files[p] = buf; } }; } }; }
          });
          window.showDirectoryPicker = async () => mk('root');
        }""")
        await pg.click("#exportBtn"); await pg.check('input[name=exf][value=md-folder]')
        await pg.click("#confirmModal"); await pg.wait_for_timeout(400)
        files = await pg.evaluate("() => Object.keys(window.__files)")
        check("folder mode writes one file per note", len(files) == 6, files)
        check("folder mode groups by space folder", all(f.startswith('root/Unsorted/') for f in files), files)
        await pg.evaluate("() => { delete window.showDirectoryPicker; }")

        # ---- Encrypted backup
        await pg.click("#exportBtn"); await pg.check('input[name=exf][value=enc]')
        await pg.fill("#exPass", "short"); await pg.fill("#exPass2", "short")
        await pg.click("#confirmModal"); await pg.wait_for_timeout(200)
        check("short passphrase is refused", await pg.is_visible("#modal") and 'at least 12' in await pg.inner_text("#exMsg"))
        await pg.fill("#exPass", "correct horse"); await pg.fill("#exPass2", "correct hrose")
        await pg.click("#confirmModal"); await pg.wait_for_timeout(200)
        check("mismatched passphrase is refused", 'do not match' in await pg.inner_text("#exMsg"))
        await pg.fill("#exPass2", "correct horse")
        async with pg.expect_download() as dl:
            await pg.click("#confirmModal")
        d = await dl.value; enc_path = os.path.join(HERE, "out_backup.localnotes"); await d.save_as(enc_path)
        enc = open(enc_path, encoding='utf-8').read()
        check("encrypted file hides note text", 'Pitch deck feedback' not in enc and 'Fundraising' not in enc)
        check("encrypted file is marked", '"format": "encrypted"' in enc)
        await pg.wait_for_timeout(300)
        # wrong passphrase
        await pg.set_input_files("#importFile", enc_path); await pg.wait_for_timeout(400)
        check("import asks for passphrase", await pg.is_visible("#modal") and 'Open encrypted backup' in await pg.inner_text("#modalTitle"))
        await pg.fill("#imPass", "wrong passphrase"); await pg.click("#confirmModal"); await pg.wait_for_timeout(500)
        check("wrong passphrase is refused", await pg.is_visible("#modal") and 'Wrong passphrase' in await pg.inner_text("#imMsg"))
        # correct passphrase
        await pg.fill("#imPass", "correct horse"); await pg.click("#confirmModal"); await pg.wait_for_timeout(700)
        check("correct passphrase restores notes", any('Imported 6 notes' in m for m in dialogs), dialogs[-3:])

        # ---- Reminders
        await pg.click("#brand"); await pg.wait_for_timeout(300)
        check("home shows calendar", await pg.locator('#calGrid .cal-cell').count() >= 28)
        await nt(pg, "Pitch deck feedback").click(); await pg.wait_for_timeout(200)
        target = today + datetime.timedelta(days=2)
        await pg.fill("#reminderInput", key(target)); await pg.wait_for_timeout(700)
        await pg.click("#brand"); await pg.wait_for_timeout(300)
        if target.month != today.month:
            await pg.click("#calNext"); await pg.wait_for_timeout(100)
        cell = pg.locator(f'#calGrid [data-day="{key(target)}"]')
        check("reminder marks calendar day", await cell.count() == 1 and await cell.locator('i').count() == 1)
        check("reminder listed under coming up", 'Pitch deck feedback' in await pg.inner_text("#upList"))
        await nt(pg, "Gym plan").click(); await pg.wait_for_timeout(200)
        yest = today - datetime.timedelta(days=1)
        await pg.fill("#reminderInput", key(yest)); await pg.wait_for_timeout(700)
        await pg.click("#brand"); await pg.wait_for_timeout(300)
        late = pg.locator('#upList .up-row.late')
        check("overdue reminder flagged", await late.count() == 1 and 'Gym plan' in await late.inner_text())
        await pg.click(f'#calGrid [data-day="{key(target)}"]'); await pg.wait_for_timeout(150)
        check("day click filters the list", 'Reminders on' in await pg.inner_text("#upHeading") and await pg.locator('#upList .up-row').count() == 1)
        check("show all clears the filter", await pg.is_visible("#upClear"))
        await pg.click("#upClear"); await pg.wait_for_timeout(100)
        check("show all restores coming up", await pg.inner_text("#upHeading") == 'Coming up')
        await nt(pg, "Pitch deck feedback").click(); await pg.wait_for_timeout(200)
        await pg.click("#reminderClear"); await pg.wait_for_timeout(700)
        await pg.click("#brand"); await pg.wait_for_timeout(300)
        check("clear removes the reminder", 'Pitch deck feedback' not in await pg.inner_text("#upList"))
        check("no uncaught errors", not errs, errs)
        await pg.screenshot(path=os.path.join(HERE, "home_reminders.png"), full_page=True)
        await b.close()
    print(f"{sum(results)}/{len(results)} passed")
asyncio.run(main())
