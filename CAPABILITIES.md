# Capability Matrix

## Built In

Discovery:

- Sitemap discovery from `robots.txt` and `/sitemap.xml`
- Robots.txt compliance with crawl-delay support
- Internal link crawling
- URL normalization
- Duplicate URL detection
- Depth limits
- Include/exclude regex rules
- Canonical URL extraction
- Broken-link/error tracking in event logs

Rendering:

- Static HTML scraping
- Optional Playwright adapter for JavaScript rendering
- DOM snapshot saving

Extraction:

- Link extraction
- Image extraction
- File URL extraction
- JSON API extraction
- Meta tags
- Open Graph
- JSON-LD/schema data
- Headings and text preview
- Table extraction
- Simple CSS selector extraction
- Simple XPath selector extraction
- Regex extraction
- Content hashes for dedupe/change detection

Session Handling:

- Custom user-agent
- Custom headers
- Cookie injection
- Token header support

Reliability:

- Per-host rate limiting
- Retry with backoff
- Timeout handling
- Threaded queue management
- Checkpoint/resume state
- Error/audit JSONL event log
- Failed-page records

Exports:

- JSONL
- CSV
- XML
- Webhook delivery
- Asset downloading

Compliance:

- Robots.txt compliance on by default
- Same-domain crawling on by default
- Domain allowlist from seed URLs
- Crawl-delay support
- Audit logs
- No CAPTCHA bypass, auth bypass, or stealth evasion features

## Optional Adapters

These need external packages or services:

- Full JavaScript rendering: Playwright
- Lazy-load, infinite scroll, screenshots, mobile viewport, geolocation, accessibility tree: Playwright
- Full XPath/CSS selector engine: lxml/parsel/selectolax
- Excel export: openpyxl
- PDF text extraction: pypdf
- SQL/database export: sqlite3 built in, PostgreSQL/MySQL need drivers
- Job scheduling: cron/systemd timer locally, cloud scheduler remotely
- Distributed workers/cloud execution: Redis/Celery/RQ/Kubernetes/serverless
- Monitoring dashboard: FastAPI/Flask plus a frontend
- Cloud storage export: provider SDKs
- Language detection/classification: fastText/langdetect/model APIs
- Visual point-and-click selectors: browser extension or Playwright UI recorder

