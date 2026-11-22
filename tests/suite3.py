import asyncio, os, re
from playwright.async_api import async_playwright
URL=os.environ.get("LOCALNOTES_URL","http://localhost:8765/index.html")
HERE=os.path.dirname(os.path.abspath(__file__))
results=[]
def check(name,ok,detail=''):
    results.append(bool(ok)); print(('PASS ' if ok else 'FAIL ')+name+('' if ok else '  -> '+str(detail)))
def calls():
    try: return sum(1 for _ in open(os.path.join(os.path.dirname(os.path.abspath(__file__)),'stub_11434_calls.log')))
    except FileNotFoundError: return 0
def note_by_title(pg,t): return pg.locator('#spaces strong').filter(has_text=re.compile('^'+re.escape(t)+'$'))
async def ask(pg,q):
    await pg.fill("#chatInput",q); await pg.click("#chatSend")
    await wait_until(pg, "() => document.querySelector('#chatSend').disabled===false")
    await pg.wait_for_timeout(150)
    bots=await pg.locator('#chatLog .msg-bot').all_inner_texts()
    srcs=await pg.locator('#chatLog .src').last.locator('button').all_inner_texts() if await pg.locator('#chatLog .src').count() else []
    return bots[-1] if bots else '', srcs
def src_titles(srcs): return [re.sub(r' · \d{4}-\d{2}-\d{2}$','',s) for s in srcs]
async def wait_until(pg, fn_js, arg=None, timeout=20000):
    # Polls with a function (not a string) so the app's Content Security Policy does not block the test.
    import time
    end = time.time() + timeout / 1000
    while time.time() < end:
        if await pg.evaluate(fn_js, arg): return
        await pg.wait_for_timeout(150)
    raise TimeoutError(str(arg))

async def main():
    async with async_playwright() as p:
        b=await p.chromium.launch(channel="chrome",headless=True)
        ctx=await b.new_context(viewport={'width':1280,'height':800},accept_downloads=True)
        pg=await ctx.new_page(); errs=[]
        pg.on("pageerror",lambda e: errs.append(str(e)))
        pg.on("dialog",lambda d: asyncio.ensure_future(d.accept()))
        await pg.goto(URL); await pg.wait_for_timeout(500)
        # --- seed the database via the real import path
        await pg.click("#importBtn") if False else None
        await pg.set_input_files("#importFile", os.path.join(HERE,"seed_backup.json")); await pg.wait_for_timeout(800)
        check("seed notes imported", await pg.locator('#spaces strong').count()>=6)
        # --- chat: topic + "last month"
        await pg.click("#chatBtn"); await pg.wait_for_timeout(200)
        check("chat view opens", await pg.is_visible("#chatView") and not await pg.is_visible("#canvasView"))
        bot,srcs=await ask(pg,"what did I do last month on fundraising?")
        check("last month + topic: exact sources",
              sorted(src_titles(srcs))==sorted(["Pitch deck feedback","Fundraising call with Anna"]), srcs)
        check("last month + topic: model was sent those notes (answer lists them)",
              "Notes used: Pitch deck feedback | Fundraising call with Anna" in bot, bot)
        check("dates shown with sources", all(re.search(r'2026-10-\d\d$',s) for s in srcs), srcs)
        # --- last month, no topic
        bot,srcs=await ask(pg,"what did I write last month?")
        check("last month, no topic: all October notes, nothing else",
              sorted(src_titles(srcs))==sorted(["Pitch deck feedback","Fundraising call with Anna","Groceries","Gym plan"]), srcs)
        # --- this month
        bot,srcs=await ask(pg,"what did I do this month on fundraising?")
        check("this month + topic: only November note",
              src_titles(srcs)==["Fundraising wrap-up"], srcs)
        # --- nothing found: no model call
        before=calls()
        bot,srcs=await ask(pg,"what did I say about kangaroos last month?")
        check("no matches: says so", "couldn't find any notes" in bot and "kangaroos" in bot, bot)
        check("no matches: model not called", calls()==before, (before,calls()))
        # --- click a source opens that note
        bot,srcs=await ask(pg,"what did I do last month on fundraising?")
        await pg.locator('#chatLog .src button', has_text="Pitch deck feedback").first.click()
        await pg.wait_for_timeout(300)
        check("source chip opens the note", await pg.input_value("#noteTitle")=="Pitch deck feedback")
        # --- canvas: points are sorted by topic, deadlines become reminders
        await pg.click("#canvasBtn"); await pg.wait_for_timeout(200)
        dump=("Buy milk\npick up eggs\n"
              "Investors want a clearer deck\nSend the deck to Anna\n"
              "Plan trip: book train to Leeds\n"
              "Finish the tax form by 2026-11-25")
        await pg.fill("#canvasText", dump); await pg.wait_for_timeout(200)
        check("canvas keeps text while typing", "Send the deck" in await pg.input_value("#canvasText"))
        await pg.click("#organiseBtn")
        await wait_until(pg, "() => document.getElementById('canvasStatus').textContent.startsWith('6 points')")
        st=await pg.inner_text("#canvasStatus")
        check("6 points sorted into 4 notes with 1 reminder", st.startswith("6 points sorted into 4 notes") and "1 reminder set" in st, st)
        check("canvas cleared after organising", (await pg.input_value("#canvasText"))=="")
        await pg.click("#allBtn"); await pg.wait_for_timeout(300)
        titles=await pg.locator('#spaces strong').all_inner_texts()
        check("one note per topic", all(t in titles for t in ["Shopping","Deck feedback","Trip","Other points"]), titles)
        await note_by_title(pg,"Shopping").click(); await pg.wait_for_timeout(200)
        check("topic note sits in its space", await pg.input_value("#category")=="Routines", await pg.input_value("#category"))
        check("points became checkboxes, all listed", await pg.locator("#editor input[type=checkbox]").count()==2 and "pick up eggs" in await pg.inner_text("#editor"))
        await note_by_title(pg,"Deck feedback").click(); await pg.wait_for_timeout(200)
        check("deck points stay together in Work", await pg.input_value("#category")=="Work" and await pg.locator("#editor input[type=checkbox]").count()==2)
        await note_by_title(pg,"Other points").click(); await pg.wait_for_timeout(200)
        check("deadline sets the note reminder", await pg.input_value("#reminderInput")=="2026-11-25", await pg.input_value("#reminderInput"))
        await pg.click("#brand"); await pg.wait_for_timeout(300)
        check("deadline shows in coming up", "Other points" in await pg.inner_text("#upList"), await pg.inner_text("#upList"))
        if "2026-11-25"[:7]==__import__("datetime").date.today().strftime("%Y-%m"):
            check("deadline marked on the calendar", await pg.locator('#calGrid [data-day="2026-11-25"] i').count()==1)
        # --- the organised notes are searchable in chat right away
        await pg.click("#chatBtn"); await pg.wait_for_timeout(200)
        bot,srcs=await ask(pg,"what did I note about the deck?")
        check("chat finds an organised note", "Deck feedback" in src_titles(srcs), srcs)
        # --- undo
        await pg.click("#canvasBtn"); await pg.wait_for_timeout(200)
        await pg.click("#undoBtn"); await pg.wait_for_timeout(500)
        check("undo restores canvas text", "Send the deck" in await pg.input_value("#canvasText"))
        await pg.click("#allBtn"); await pg.wait_for_timeout(300)
        titles=await pg.locator('#spaces strong').all_inner_texts()
        check("undo removes organised notes", not any(t in titles for t in ["Shopping","Deck feedback","Trip","Other points"]), titles)
        # --- a topic split across blank lines still becomes one checklist
        await pg.click("#canvasBtn"); await pg.wait_for_timeout(200)
        before_n=await pg.locator('#spaces strong').count()
        await pg.fill("#canvasText","Investors want a clearer deck\n\nSend the deck to Anna\n\nBook a deck review\n\nBuy milk")
        await pg.click("#organiseBtn")
        await wait_until(pg, "() => document.getElementById('canvasStatus').textContent.startsWith('4 points')")
        st=await pg.inner_text("#canvasStatus")
        check("4 points on 2 topics make exactly 2 notes", st.startswith("4 points sorted into 2 notes") and await pg.locator('#spaces strong').count()-before_n==2, st)
        await note_by_title(pg,"Deck feedback").click(); await pg.wait_for_timeout(250)
        boxes=await pg.locator("#editor input[type=checkbox]").count()
        check("the deck topic is one page with 3 checkable points", boxes==3, boxes)
        check("points are listed, not split into pages", "Send the deck to Anna" in await pg.inner_text("#editor"))
        # --- the Work page is also shown on the category page when the space is opened
        await pg.click('[data-space="Work"]'); await pg.wait_for_timeout(300)
        check("space page lists its note", "Work" in await pg.inner_text("#overviewTitle") and await pg.locator('#overviewGrid .card').count()>=1)
        await pg.click("#canvasBtn"); await pg.wait_for_timeout(200)
        # --- canvas text survives reload and reopen returns to canvas
        await pg.click("#canvasBtn"); await pg.wait_for_timeout(200)
        await pg.fill("#canvasText","half thought about tents"); await pg.wait_for_timeout(200)
        await pg.reload(); await pg.wait_for_timeout(600)
        check("reopen returns to canvas", await pg.is_visible("#canvasView"))
        check("canvas text survives reload", await pg.input_value("#canvasText")=="half thought about tents")
        # --- Ctrl+Enter organises
        await pg.click("#canvasClear") if False else None
        await pg.fill("#canvasText","Call the bank\n\nWrite the report"); await pg.wait_for_timeout(150)
        await pg.focus("#canvasText"); await pg.keyboard.press("Control+Enter")
        await wait_until(pg, "() => document.getElementById('canvasStatus').textContent.startsWith('2 points')")
        check("Ctrl+Enter organises into one checklist for same-topic points", "sorted into 1 note" in await pg.inner_text("#canvasStatus"), await pg.inner_text("#canvasStatus"))
        # --- bad AI reply keeps the text and says why
        await pg.click("#canvasBtn"); await pg.wait_for_timeout(150)
        await pg.fill("#canvasText","Keep this safe\n\nand this too"); await pg.wait_for_timeout(200)
        await pg.click("#ollamaStatus"); await pg.wait_for_timeout(200)
        await pg.fill("#oAddr","http://127.0.0.1:11435"); await pg.click("#confirmModal"); await pg.wait_for_timeout(500)
        await pg.click("#canvasBtn"); await pg.wait_for_timeout(200)
        await pg.click("#organiseBtn"); await pg.wait_for_timeout(1500)
        st=await pg.inner_text("#canvasStatus")
        check("bad AI reply: explains and keeps text", "could not be read" in st and "Keep this safe" in await pg.input_value("#canvasText"), st)
        # --- Ollama not running
        await pg.click("#ollamaStatus"); await pg.wait_for_timeout(200)
        await pg.fill("#oAddr","http://127.0.0.1:11999"); await pg.click("#confirmModal"); await pg.wait_for_timeout(400)
        await pg.click("#canvasBtn"); await pg.wait_for_timeout(150)
        await pg.click("#organiseBtn"); await pg.wait_for_timeout(1200)
        st=await pg.inner_text("#canvasStatus")
        check("AI down: clear message and text kept", "Could not reach Ollama" in st and "Keep this safe" in await pg.input_value("#canvasText"), st)
        # --- chat when AI down
        await pg.click("#chatBtn"); await pg.wait_for_timeout(150)
        bot,srcs=await ask(pg,"what did I do last month on fundraising?")
        check("chat with AI down: clear error", "Could not reach Ollama" in bot, bot)
        # --- back to working AI
        await pg.click("#ollamaStatus"); await pg.wait_for_timeout(200)
        await pg.fill("#oAddr","http://127.0.0.1:11434"); await pg.click("#confirmModal"); await pg.wait_for_timeout(500)
        check("AI recovers after fixing address", "ready" in (await pg.inner_text("#ollamaStatus")).lower())
        # --- notes view still works after all this
        await pg.click("#allBtn"); await pg.wait_for_timeout(300)
        check("notes still open and editable", await pg.locator('#spaces strong').count()>=6)
        check("no uncaught errors", not errs, errs)
        await b.close()
    print(f"\n{sum(results)}/{len(results)} passed")
asyncio.run(main())
