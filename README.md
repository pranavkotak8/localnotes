# Localnotes

A private, local-first notes app in a single HTML file. Write anything on the Canvas, and a local AI (through Ollama, optional) groups it by topic into checklists filed in your spaces. Ask questions of your own notes. Set reminders on a calendar.

No build step, no account, no server. Your notes stay in your browser on your computer.

## Features
- **Canvas (main feature):** a blank sheet for dumping anything in any order. Each line is one point. "Organise with AI" sorts the points by topic: one note per topic, one checklist line per point, filed in a space. Deadlines in a point ("by 30 Nov", "due Friday", "tomorrow", "2026-12-03") become a reminder on that note. Undo reverses an organise.
- **Ask your notes:** answers come only from your notes, and each answer lists the notes it used. Date words narrow the search: "today", "last week", "this month", "last 3 months", "in March".
- **Spaces:** a collapsible tree in the sidebar. Click a name to list its notes; click the arrow to fold it away.
- **Rich-text notes:** bold, italic, underline, strikethrough, headings, quotes, bullet and numbered lists, checkbox to-dos, colours, highlights, links, undo/redo.
- **Reminders:** set a "Remind me" date on any note. The home page shows a month calendar with a dot on each day that has reminders, and a short "Coming up" list (overdue items first, then the next two weeks).
- **Export:** Markdown (one folder of .md files grouped by space, or one .md file), encrypted backup, or plain JSON backup.
- **Import:** restores JSON and encrypted backups.
- **Local AI (optional):** summarise, fix grammar, pull out action items, suggest a title. You review each result before anything changes.

## Privacy
- Notes are saved only in this browser on this computer.
- The AI runs on your computer through Ollama. Nothing is sent to a server.
- The app makes no network requests except to the local Ollama address you set. This was checked by recording the network hosts the page contacts (only localhost).

## Backups and portability
- **Markdown** is the portable format. Each file has front matter with the title, space, dates and any reminder. Use it to move notes into another app.
- **Encrypted backup** (`.localnotes`): the whole notebook is encrypted with AES-256-GCM. The key is derived from your passphrase with PBKDF2-SHA-256 (310,000 iterations). Without the passphrase the file cannot be read. Choose a passphrase you will remember: if you forget it, the backup cannot be recovered.
- **Plain JSON** is readable by anyone who has the file. Keep it somewhere safe.

## What it does not do yet
Stated plainly, so you know what to expect:
- **No sync.** Notes live in one browser on one computer. There is no way to see them on another device.
- **No mobile app.** The page works in a phone browser, but it is designed for a computer and is not tested as an app.
- **No live folder sync.** Markdown export is a copy. Changes you make to the .md files are not read back.
- **Reminders only show while the page is open.** There are no notifications, and nothing fires when the tab is closed.
- **Encryption covers backups only.** Notes are stored unencrypted in the browser's own storage on your computer, as any browser data is.
- **Browser storage can be lost.** Clearing site data, using a private window, or uninstalling the browser deletes notes. Export a backup regularly.
- **Chrome and Edge only.** Folder export needs the File System Access API, which other browsers lack. Other features may work elsewhere but are not tested.
- **No images, attachments or drawings.** Text and checklists only.
- **Dates are read in English.** "30 Nov", "November 30", weekdays, "tomorrow", "in 3 days" and ISO dates are understood. Numeric dates such as 03/12 are not, so write the month name or the ISO date.
- **Sorting depends on the AI.** The model decides which points share a topic. Deadlines are read by the app itself, not the model. Check the result after organising.
- **Search is keyword-based.** It does not understand synonyms, so ask with the words you used in your notes.
- **The AI has been tested against a stub, not a real model.** The checks confirm what the app sends and how it handles replies. The quality of answers from a real Ollama model has not been measured here.
- **Not security-audited.** It is a careful personal project, not a reviewed product. Do not rely on it for information that needs certified protection.

## Running it
Easiest: double-click `index.html`. For the most reliable behaviour, and for Ollama, serve the folder:

    python -m http.server 8000

then open http://localhost:8000.

## Ollama (optional)
1. Install Ollama and pull a model, for example `ollama pull llama3.2`.
2. Start Ollama.
3. In Localnotes, click the AI status pill (or "AI setup") and press "Test connection".

If the test fails while Ollama is running, the page is probably being refused. Add the page's address to `OLLAMA_ORIGINS` (for example `OLLAMA_ORIGINS=http://localhost:8000`), restart Ollama, and reload. Do not use a wildcard origin on an untrusted network.

## How the chat finds notes
Matching is by date first, then by word overlap with your question (simple stemming: "fundraising" matches "fundraise"). Up to 15 matching notes go to the model, and each answer shows which were used. If nothing matches, the app says so without calling the model.

## Tests
The tests use Playwright with the installed Chrome channel, from the `tests/` folder.

    pip install playwright
    python3 -m http.server 8765        # from the repository root, in another terminal
    cd tests
    python3 stub2.py 11434 &           # stand-in Ollama, working
    python3 stub2.py 11435 bad &       # stand-in Ollama, returns bad replies
    python3 suite2.py http://localhost:8765/index.html   # notes, spaces, export/import, Ollama, mobile
    python3 suite3.py                  # canvas, organise, undo, chat
    python3 suite4.py                  # Markdown, encrypted backup, reminders

The `LOCALNOTES_URL` environment variable can point suite3 at another address.


## Security and privacy checks
See [SECURITY.md](SECURITY.md) for the threat model and how to verify the claims. In short: run `python3 tests/suite7.py http://localhost:8765/index.html` (with the server running). It records every network request and fails if any leaves your machine.

## Licence
MIT. See [LICENSE](LICENSE).
