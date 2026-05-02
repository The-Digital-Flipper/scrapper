# Advanced Scraper

A dependency-free Python scraper designed for legitimate research, indexing, audits, and data collection where you are allowed to crawl the target.

It includes:

- Same-domain crawling by default
- `robots.txt` checks by default
- Per-host rate limiting
- Retry with backoff
- Concurrent workers
- Sitemap discovery from `robots.txt` and `sitemap.xml`
- Include/exclude URL regex rules
- HTML title, meta description, canonical URL, Open Graph, JSON-LD, headings, text preview, link extraction
- SHA-256 content hashes for dedupe/change detection
- JSONL and CSV export
- Resumable visited-state file
- Optional Playwright rendering for JavaScript-heavy pages

It intentionally does not include CAPTCHA bypass, stealth fingerprinting, auth bypass, or anti-bot evasion.

## Run

Local product dashboard:

```bash
advanced-scraper
```

Then open:

```text
http://127.0.0.1:8787
```

The dashboard now includes built-in pages:

- Install
- Features
- Recipes
- Help

Offline guide:

```text
/home/007-JB/advanced-scraper/INSTALL_AND_USE.md
```

The dashboard stores profiles, run history, results, archives, imports, DOM snapshots, and downloaded assets in:

```text
/home/007-JB/.advanced-scraper
```

Install or refresh the local launcher:

```bash
/home/007-JB/advanced-scraper/install-local.sh
```

Desktop packaging:

```bash
cd /home/007-JB/advanced-scraper/desktop
./build-backend.sh
npm run dist
```

The Electron shell is designed to launch a bundled backend executable from `desktop/backend-dist/` when packaged. A GitHub Actions workflow is included at `.github/workflows/release-desktop.yml` to build and publish installers on tag pushes.

Ship checklist:

- `RELEASE_CHECKLIST.md`

Command-line crawler:

```bash
cd /home/007-JB/advanced-scraper
python3 -m advanced_scraper.cli https://example.com --max-pages 25 --max-depth 1 -o output.jsonl
```

CSV output:

```bash
python3 -m advanced_scraper.cli https://example.com --format csv -o output.csv
```

More aggressive but still polite:

```bash
python3 -m advanced_scraper.cli https://example.com --workers 10 --rate-limit 0.5 --max-pages 500
```

Sitemap-assisted crawl:

```bash
python3 -m advanced_scraper.cli https://example.com --sitemaps --max-pages 1000 -o sitemap-output.jsonl
```

Only crawl product URLs and skip account/cart pages:

```bash
python3 -m advanced_scraper.cli https://example.com \
  --include '/products/' \
  --exclude '/cart|/account|/login' \
  --max-pages 500
```

JavaScript rendering, optional:

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
python3 -m advanced_scraper.cli https://example.com --render-js --max-pages 25
```

## Options

```text
--max-pages N       maximum pages to fetch
--max-depth N       crawl depth from seed URLs
--workers N         concurrent worker count
--rate-limit N      minimum seconds between requests per host
--state-file PATH   resumable visited state
--format jsonl|csv  output format
--cross-domain      allow links outside seed domains
--ignore-robots     disable robots checks; only use when you own or are authorized for the target
--sitemaps          add URLs from discovered sitemaps
--include REGEX     only crawl matching URLs; repeatable
--exclude REGEX     skip matching URLs; repeatable
--render-js         render with Playwright if installed
```

## Site Zip Archives

The app can package a captured site into a portable zip containing:

- scraped data
- run logs
- DOM snapshots
- downloaded images/files
- manifest/config metadata

Create one from the CLI:

```bash
python3 -m advanced_scraper.manage archive \
  --name example-site \
  --output /home/007-JB/.advanced-scraper/runs/run.jsonl \
  --event-log /home/007-JB/.advanced-scraper/runs/run-events.jsonl \
  --dom-dir /home/007-JB/.advanced-scraper/dom \
  --asset-dir /home/007-JB/.advanced-scraper/assets
```

Import a zip:

```bash
python3 -m advanced_scraper.manage import-archive /path/to/site.zip
```

In the dashboard, use **Import Site Zip** with a local zip path.

## Market-Level Notes

The current strongest general-purpose scraper stack is:

- Scrapy-style HTTP crawling for speed and scale
- Crawlee-style request queues, retries, and storage
- Playwright for dynamic JavaScript pages
- Strict rate limiting, robots awareness, and clear user-agent identification

This project implements the same shape without mandatory dependencies so it can run on this machine now. Playwright is supported as an optional renderer.
