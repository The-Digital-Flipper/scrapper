# Advanced Scraper Install And Use

## Install

Run:

```bash
/home/007-JB/advanced-scraper/install-local.sh
```

This installs:

- terminal command: `advanced-scraper`
- desktop launcher: `/home/007-JB/.local/share/applications/advanced-scraper.desktop`
- local storage folder: `/home/007-JB/.advanced-scraper`

## Start

Run:

```bash
advanced-scraper
```

Open:

```text
http://127.0.0.1:8787
```

## Basic Workflow

1. Open the dashboard.
2. Create a profile.
3. Add one or more seed URLs.
4. Choose max pages, max depth, workers, and rate limit.
5. Enable sitemaps for whole-site coverage.
6. Enable DOM snapshots and asset downloads for full-detail capture.
7. Enable zip archive if you want a portable copy.
8. Save the profile.
9. Run the profile.
10. Check Runs and Archives.

## Whole-Site Capture Settings

Use these for a broad crawl:

```text
Seed URLs: https://example.com
Max pages: 10000
Max depth: 6
Workers: 6
Rate limit seconds: 1.0
Use sitemaps: on
Save DOM snapshots: on
Download linked images/files: on
Create zip archive after runs: on
```

## Import A Site Zip

In the dashboard, paste the full zip path:

```text
/home/007-JB/Downloads/site.zip
```

Imported sites go here:

```text
/home/007-JB/.advanced-scraper/imports
```

## Command Line

Run a crawl:

```bash
cd /home/007-JB/advanced-scraper
python3 -m advanced_scraper.cli https://example.com --sitemaps --max-pages 500 -o output.jsonl
```

Extract specific fields:

```bash
python3 -m advanced_scraper.cli https://example.com --css h1 --css .price --regex '\$[0-9,.]+' -o products.jsonl
```

Import a zip:

```bash
python3 -m advanced_scraper.manage import-archive /home/007-JB/Downloads/site.zip
```

## Storage Paths

```text
Profiles and database: /home/007-JB/.advanced-scraper/scraper.db
Run outputs:           /home/007-JB/.advanced-scraper/runs
Zip archives:          /home/007-JB/.advanced-scraper/archives
Imported sites:        /home/007-JB/.advanced-scraper/imports
DOM snapshots:         /home/007-JB/.advanced-scraper/dom
Assets/files:          /home/007-JB/.advanced-scraper/assets
```

