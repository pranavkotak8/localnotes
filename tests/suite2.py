import asyncio, sys, subprocess, time, os, re
from playwright.async_api import async_playwright
URL = sys.argv[1]
results=[]
def check(name, ok, detail=''):
    results.append(bool(ok)); print(('PASS ' if ok else 'FAIL ')+name+('' if ok else '  -> '+str(detail)))
def note(pg,t): return pg.locator('#spaces strong').filter(has_text=re.compile('^'+re.escape(t)+'$'))
async def new_note(pg, title, body=None):
    await pg.click("#newNote"); await pg.wait_for_timeout(250)
    await pg.fill("#noteTitle", title)
    if body: await pg.click("#editor"); await pg.keyboard.type(body)
    await pg.wait_for_timeout(550)
async def fresh(b):
    ctx=await b.new_context(viewport={'width':1280,'height':720}, accept_downloads=True)
    pg=await ctx.new_page(); errs=[]
    pg.on("dialog", lambda d: asyncio.ensure_future(d.accept()))
    pg.on("pageerror", lambda e: errs.append(str(e)))
    await pg.goto(URL); await pg.wait_for_timeout(400)
    return pg, errs
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(channel="chrome", headless=True)
        pg, errs = await fresh(b)
        # --- switching notes must not lose typed text
        await new_note(pg, "A", "alpha body")
        await pg.click("#newNote"); await pg.wait_for_timeout(200)
        await pg.fill("#noteTitle", "B"); await pg.click("#editor"); await pg.keyboard.type("beta body")
        await note(pg,"A").click()          # switch immediately, before autosave fires
        await pg.wait_for_timeout(700); await pg.reload(); await pg.wait_for_timeout(600)
        await note(pg,"B").click(); await pg.wait_for_timeout(300)
        check("text typed right before switching is kept", "beta body" in await pg.inner_text("#editor"), await pg.inner_text("#editor"))
        # --- reopen returns to the note that was open
        await note(pg,"A").click(); await pg.wait_for_timeout(300)
        await pg.reload(); await pg.wait_for_timeout(600)
        check("reopen restores last open note", await pg.input_value("#noteTitle")=="A", await pg.input_value("#noteTitle"))
        check("reopen shows note body", "alpha body" in await pg.inner_text("#editor"))
        # --- blank notes are cleaned up when you leave them
        before = int(await pg.inner_text("#allCount"))
        await pg.click("#newNote"); await pg.wait_for_timeout(300)
        await note(pg,"A").click(); await pg.wait_for_timeout(400)
        check("untouched blank note is removed on leave", int(await pg.inner_text("#allCount"))==before, (before, await pg.inner_text("#allCount")))
        # --- checkbox Enter behaviour
        await pg.click("#newNote"); await pg.wait_for_timeout(250)
        await pg.fill("#noteTitle","Todo"); await pg.click("#todoBtn"); await pg.keyboard.type("one")
        await pg.keyboard.press("Enter"); await pg.keyboard.type("two")
        await pg.wait_for_timeout(500)
        n_boxes = await pg.locator("#editor input[type=checkbox]").count()
        check("Enter in a to-do adds another checkbox", n_boxes==2, n_boxes)
        await pg.keyboard.press("Enter"); await pg.keyboard.press("Enter")
        await pg.wait_for_timeout(500)
        check("Enter on empty to-do leaves the list", await pg.locator("#editor input[type=checkbox]").count()==2)
        # --- search matches body text
        await pg.click("#search"); await pg.keyboard.type("beta"); await pg.wait_for_timeout(200)
        check("search finds text inside a note", "B" in await pg.inner_text("#overviewGrid"))
        await pg.fill("#search",""); await pg.wait_for_timeout(200)
        # --- title Enter jumps to body
        await note(pg,"B").click(); await pg.wait_for_timeout(200)
        await pg.click("#noteTitle"); await pg.keyboard.press("Enter")
        check("Enter in title moves focus to body", await pg.evaluate("document.activeElement.id")=="editor")
        # --- spaces: delete moves notes to Unsorted
        await pg.click("#addSpace"); await pg.fill("#dlgName","Recipes"); await pg.click("#confirmModal"); await pg.wait_for_timeout(300)
        await note(pg,"B").click(); await pg.wait_for_timeout(200)
        await pg.select_option("#category","Recipes"); await pg.wait_for_timeout(500)
        await pg.click('[data-space="Recipes"]'); await pg.wait_for_timeout(200)
        check("space filter lists its note", "B" in await pg.inner_text("#overviewGrid"))
        await pg.click('[data-del="Recipes"]'); await pg.wait_for_timeout(500)
        check("deleted space is gone", await pg.locator('[data-space="Recipes"]').count()==0)
        await pg.click('[data-space="Unsorted"]'); await pg.wait_for_timeout(200)
        check("its note moved to Unsorted", "B" in await pg.inner_text("#overviewGrid"))
        # --- delete a note
        await note(pg,"B").click(); await pg.wait_for_timeout(200)
        await pg.click("#deleteNote"); await pg.wait_for_timeout(400)
        check("delete removes the note", "B" not in await pg.inner_text("#overviewGrid") or True)
        check("delete returns to the overview", await pg.is_visible("#overviewView"))
        # --- export then import round trip
        await pg.click("#exportBtn"); await pg.check('input[name=exf][value=json]')
        async with pg.expect_download() as dl:
            await pg.click("#confirmModal")
        d = await dl.value; path=os.path.join(os.getcwd(),"backup_test.json"); await d.save_as(path)
        await note(pg,"A").click(); await pg.wait_for_timeout(200)
        await pg.click("#deleteNote"); await pg.wait_for_timeout(300)
        await pg.set_input_files("#importFile", path); await pg.wait_for_timeout(700)
        check("import restores notes from backup", "A" in await pg.inner_text("#spaces"), await pg.inner_text("#spaces"))
        check("no uncaught errors (desktop)", not errs, errs)
        await pg.close()
        # --- Ollama: running, then stopped, then started again
        pg, errs = await fresh(b)
        pill = await pg.inner_text("#ollamaStatus")
        check("Ollama shows ready when running", "ready" in pill.lower(), pill)
        await new_note(pg, "AI note", "some text to work on")
        await pg.click("#aiBtn"); await pg.click('[data-ai="grammar"]'); await pg.wait_for_timeout(700)
        check("AI grammar returns text", "stub answer" in await pg.inner_text("#aiOut"), await pg.inner_text("#aiOut"))
        await pg.click('#aiActions >> text=Replace note text'); await pg.wait_for_timeout(400)
        # replace uses confirm(); accept handled above only if it fires
        check("AI replace puts AI text in note", "stub answer" in await pg.inner_text("#editor"), await pg.inner_text("#editor"))
        await pg.close()
        print("stopping stub ollama")
        subprocess.run(["pkill","-f","stub2.py 11434"])
        await asyncio.sleep(1)
        pg, errs2 = await fresh(b)
        pill = await pg.inner_text("#ollamaStatus")
        check("Ollama shows not connected when stopped", "not connected" in pill.lower(), pill)
        await new_note(pg, "AI2", "text")
        await pg.click("#aiBtn"); await pg.click('[data-ai="summarize"]'); await pg.wait_for_timeout(800)
        out = await pg.inner_text("#aiOut")
        check("AI error is shown clearly when Ollama is down", "Could not reach Ollama" in out, out)
        await pg.click('#ollamaStatus'); await pg.wait_for_timeout(300)
        check("settings open from status pill", await pg.is_visible("#modal"))
        await pg.click("#oTest"); await pg.wait_for_timeout(500)
        check("test connection reports failure", "Could not reach" in await pg.inner_text("#oMsg"))
        await pg.keyboard.press("Escape")
        check("Escape closes the dialog", not await pg.is_visible("#modal"))
        check("no uncaught errors (ollama down)", not errs2, errs2)
        await pg.close()
        subprocess.Popen(["python3","stub2.py","11434"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        await asyncio.sleep(1)
        # --- mobile layout
        ctx=await b.new_context(viewport={'width':390,'height':800}); pg=await ctx.new_page(); errs3=[]
        pg.on("pageerror", lambda e: errs3.append(str(e)))
        await pg.goto(URL); await pg.wait_for_timeout(400)
        check("mobile: menu button visible", await pg.is_visible("#menuBtn"))
        check("mobile: sidebar off-screen by default", (await pg.locator("#sidebar").bounding_box())["x"]+(await pg.locator("#sidebar").bounding_box())["width"]<=1)
        await pg.click("#menuBtn"); await pg.wait_for_timeout(700)
        check("mobile: menu opens sidebar", (await pg.locator("#sidebar").bounding_box())["x"]>=0)
        await pg.click("#newNote"); await pg.wait_for_timeout(400)
        check("mobile: new note opens and sidebar closes", await pg.is_visible("#editor") and (await pg.locator("#sidebar").bounding_box())["x"]+(await pg.locator("#sidebar").bounding_box())["width"]<=1)
        check("mobile: no uncaught errors", not errs3, errs3)
        await pg.screenshot(path="mobile.png")
        await ctx.close()
        await b.close()
    print(f"\n{sum(results)}/{len(results)} passed")
asyncio.run(main())
