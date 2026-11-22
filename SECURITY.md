# Security

## What this app protects against
- Notes never leave the browser, except to the Ollama address you configure (default `localhost:11434`).
- Note text is never inserted as HTML. Titles, previews, chat answers and AI replies are escaped or written as plain text.
- Rich text pasted or imported is cleaned by a whitelist (`clean()` in `index.html`). Scripts, iframes, images and unknown tags are removed. Links must be `http(s)` or `mailto`.
- A Content Security Policy blocks scripts and connections from any other origin.
- Encrypted backups use PBKDF2-SHA-256 (310,000 iterations) and AES-256-GCM through the browser's WebCrypto API.

## What it does not protect against
- Anyone with access to your unlocked computer or browser profile can read your notes. Data is stored unencrypted in IndexedDB.
- Plain JSON backups are not encrypted.
- Encryption strength depends on your passphrase. Use a long one (12+ characters).
- If you point the AI address at a remote server, your note text is sent there. Keep it on `localhost`.
- No independent security audit has been done.

## How to check it yourself
1. Read the code. It is one file, `index.html`, with no build step and no dependencies.
2. Run the privacy test. It records every network request during a session and fails if any leaves this machine:
   `python3 tests/suite7.py http://localhost:8765/index.html`
3. Open the browser's developer tools, go to the Network tab, and use the app. Only `localhost` requests should appear.
4. Check the Content Security Policy in the page's `<head>`.

## Reporting a vulnerability
Please do not open a public issue for security problems. Email the maintainer, or use GitHub's "Report a vulnerability" button under the Security tab, and allow time for a fix before publishing details.
