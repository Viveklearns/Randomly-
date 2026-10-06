Paste posts here that no API can reach (private Facebook groups, Nextdoor, WhatsApp, flyers).

- One post per `.txt` file. Optional first line: `URL: https://facebook.com/groups/...`
- Or append lines to `posts.jsonl`: `{"url": "...", "platform": "facebook", "text": "..."}`

The next run reads them and moves `.txt` files into `processed/`.
