# Bergen County cooking-class finder

Collects cooking classes posted on social media and event sites for Bergen County, NJ, uses Claude to turn each post into a structured record (date, time, town, price, host, sign-up link), merges duplicates, and publishes a list.

```
 sources ──► keyword filter ──► Claude extraction ──► dedupe/merge ──► data/latest.md
 (web search,   (cheap, skips       (structured output,     (same class on FB +       data/classes.csv
  Reddit, IG,    obvious noise)      Bergen check)           IG = one record)          data/classes.json
  pages, inbox)
```

## Sources and what each one reaches

| Source | Reaches | Needs |
|---|---|---|
| `web_search` | Public **Facebook** events/posts, public **Instagram** posts, Eventbrite, AllEvents, Meetup, Patch, library and town calendars, all through Claude's web search tool | `ANTHROPIC_API_KEY` |
| `instagram` | Recent posts on hashtags like `#njcookingclass` and `#bergencountynj` through the official Instagram Graph API | IG Business/Creator account + Meta app (`IG_USER_ID`, `IG_ACCESS_TOKEN`) |
| `reddit` | r/newjersey, r/BergenCounty, r/northjersey | nothing |
| `pages` | Class calendars you want re-checked every run (cooking schools, ShopRite/Kings/Whole Foods event pages, adult schools) | add URLs in `config.toml` |
| `manual` | **Private Facebook groups**, Nextdoor, WhatsApp, flyers: paste the post into `inbox/` | nothing |

**About Facebook:** Meta has no API for searching Facebook posts or groups, and scraping it breaks its terms. That leaves two legitimate routes: public events and posts that search engines index (the `web_search` source finds these), and posts you paste in from groups you belong to (`inbox/`). Local mom groups and "Bergen County Foodies"-type groups are where most home cooks post classes, so the inbox is worth using.

## Run it

```bash
cd cooking-classes
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...

python -m cooking_classes --dry-run            # collect + filter, print candidates, no Claude extraction calls
python -m cooking_classes                      # full run
python -m cooking_classes --sources manual     # only process pasted posts
```

Output goes to `data/latest.md` (a readable table with new classes flagged 🆕), `data/classes.csv` (for Google Sheets/Excel), and `data/classes.json` (the full record, including every URL each class was seen at).

Each run only sends posts it hasn't read before to Claude (`data/seen.json`). A watched page whose content changes gets re-read.

## Scheduled runs

`.github/workflows/cooking-classes.yml` runs Mondays and Thursdays, commits the updated `data/`, and puts the table in the run summary. To turn it on, add the `ANTHROPIC_API_KEY` repository secret (plus `IG_USER_ID` / `IG_ACCESS_TOKEN` if you set up Instagram). To start a run by hand, use **Actions → Bergen County cooking classes → Run workflow**.

## Tuning

Everything is in `config.toml`: search queries, subreddits, hashtags (Meta allows 30 unique hashtags per 7 days), watched pages, and the Claude model and effort levels. Claude's prompts are in `cooking_classes/sources/web_search.py` (discovery) and `cooking_classes/extract.py` (extraction).

## Tests

```bash
python -m unittest discover -s tests
```

The tests use a fake Claude client, so they need no API key.
