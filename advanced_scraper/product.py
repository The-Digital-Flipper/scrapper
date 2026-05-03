from __future__ import annotations

import html
import csv
import json
import os
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from .archive import create_site_archive, import_site_archive, list_archives, list_imports
from .storage import APP_DIR, RUNS_DIR, create_run, finish_run, get_run, list_profiles, list_result_index, list_runs, save_profile, save_result_index


HOST = "127.0.0.1"
PORT = int(os.environ.get("ADVANCED_SCRAPER_PORT", "8787"))


CSS = """
:root{--bg:#050805;--bg-soft:#0b120b;--panel:#081008;--panel-alt:#0d160d;--text:#f5fff5;--muted:#c6d8c6;--line:#2a532a;--line-strong:#44a044;--accent:#35ff8a;--accent-weak:#102116;--danger:#ff3e2f;--warn:#7ddc7d;--success:#35ff8a;--shadow:0 12px 36px rgba(0,0,0,.44)}
*{box-sizing:border-box}
body{margin:0;background:radial-gradient(circle at top, rgba(53,255,138,.10), transparent 34%), linear-gradient(180deg, #040704 0%, #020402 100%);color:var(--text);font:14px/1.5 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;position:relative;overflow-x:hidden}
body::before{content:"";position:fixed;inset:-10vh -8vw auto auto;width:min(78vw,1080px);height:min(78vw,1080px);pointer-events:none;opacity:.09;z-index:0;background-repeat:no-repeat;background-position:center;background-size:contain;background-image:url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 900 900'%3E%3Cg fill='none' stroke='%2335ff8a' stroke-width='18' stroke-linecap='round' stroke-linejoin='round' opacity='.9'%3E%3Cpath d='M140 105h620'/%3E%3Cpath d='M140 180h420'/%3E%3Cpath d='M140 255h520'/%3E%3Cpath d='M140 330h360'/%3E%3Cpath d='M140 405h580'/%3E%3Cpath d='M140 480h300'/%3E%3Cpath d='M140 555h500'/%3E%3Cpath d='M140 630h420'/%3E%3Cpath d='M140 705h560'/%3E%3Cpath d='M140 780h360'/%3E%3Cpath d='M235 145c55-72 122-108 205-108 84 0 150 36 205 108'/%3E%3Cpath d='M250 235c35 70 78 110 160 128 85-18 128-58 163-128'/%3E%3Cpath d='M300 465c40-45 80-65 150-65s110 20 150 65'/%3E%3Cpath d='M330 570c45 35 90 52 120 52s75-17 120-52'/%3E%3Cpath d='M360 420h0'/%3E%3Cpath d='M540 420h0'/%3E%3Cpath d='M360 420c16-14 32-14 48 0'/%3E%3Cpath d='M492 420c16-14 32-14 48 0'/%3E%3Cpath d='M450 450c0 18 0 18-18 36'/%3E%3Cpath d='M432 486c20 16 36 20 52 12'/%3E%3C/g%3E%3Cg fill='%23ff1a00' opacity='.17'%3E%3Ccircle cx='360' cy='440' r='12'/%3E%3Ccircle cx='540' cy='440' r='12'/%3E%3C/g%3E%3C/svg%3E\")}
a{color:var(--accent)}
header.topbar{background:#040704;color:#eaffee;border-bottom:1px solid rgba(53,255,138,.16);position:relative;z-index:1}
.topbar-inner{max-width:1440px;margin:0 auto;padding:18px 28px;display:flex;align-items:center;justify-content:space-between;gap:16px}
.brand{font-size:22px;font-weight:800;letter-spacing:0}
.brand-sub{margin-top:2px;color:#cbd5e1;font-size:13px}
.topbar-chip{display:inline-flex;align-items:center;gap:8px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.12);border-radius:999px;padding:8px 12px;color:#e5e7eb;font-weight:650;font-size:12px}
nav.tabs{background:#070b07;padding:10px 28px;border-bottom:1px solid rgba(53,255,138,.10);display:flex;gap:18px;overflow:auto;position:relative;z-index:1}
nav.tabs a{color:#d1d5db;text-decoration:none;font-weight:700;padding:4px 0;white-space:nowrap}
nav.tabs a:hover{color:#fff}
main.app-main{max-width:1440px;margin:0 auto;padding:24px;position:relative;z-index:1}
h1{margin:0;font-size:24px;line-height:1.1}
h2{font-size:17px;margin:0 0 14px}
h3{font-size:15px;margin:18px 0 8px}
.hero{display:grid;grid-template-columns:minmax(0,1.4fr) minmax(360px,.9fr);gap:18px;align-items:stretch;margin-bottom:18px}
.hero-panel,.panel,.quick{background:var(--panel);border:1px solid var(--line);border-radius:10px;box-shadow:var(--shadow)}
.hero-panel{padding:22px}
.hero-kicker{display:inline-flex;align-items:center;gap:8px;font-size:12px;font-weight:800;color:var(--accent);text-transform:uppercase;letter-spacing:.02em}
.hero-copy{max-width:68ch}
.hero-copy p{color:var(--muted)}
.hero-actions{display:flex;flex-wrap:wrap;gap:10px;margin-top:16px}
.hero-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin-top:18px}
.stat-card{background:var(--bg-soft);border:1px solid var(--line);border-radius:10px;padding:14px}
.stat-card strong{display:block;font-size:24px;line-height:1.05;margin-top:2px}
.launcher{padding:22px}
.launcher form{display:grid;gap:12px}
.launcher .row{grid-template-columns:1fr 1fr}
.quick form{display:grid;gap:12px}
.quick input{font-size:15px;padding:12px 14px}
.quick button{font-size:15px;padding:12px 16px}
.panel{padding:18px}
.details{margin-top:18px}
.stack{display:grid;gap:18px}
.grid{display:grid;grid-template-columns:1.1fr .9fr;gap:18px}
.stacked-grid{display:grid;grid-template-columns:1.2fr .8fr;gap:18px;align-items:start}
.form-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
.form-grid .full{grid-column:1/-1}
.label-row{display:flex;justify-content:space-between;align-items:center;gap:10px}
label{display:block;font-weight:800;margin:10px 0 5px;color:#f8fff8}
input,select,textarea{width:100%;box-sizing:border-box;border:1px solid var(--line-strong);border-radius:8px;padding:10px 11px;background:#0b1017;color:var(--text)}
input:focus,select:focus,textarea:focus{outline:2px solid rgba(15,118,110,.14);border-color:var(--accent)}
textarea{min-height:72px;resize:vertical}
button,.button{display:inline-flex;align-items:center;justify-content:center;gap:8px;background:linear-gradient(180deg,#ffb24d,#ff8a00);color:#181109;border:0;border-radius:8px;padding:10px 14px;text-decoration:none;font-weight:800;cursor:pointer;box-shadow:0 1px 0 rgba(255,255,255,.08) inset}
button:hover,.button:hover{filter:brightness(1.02)}
.secondary{background:#1a2230;color:#e6edf7}
.ghost{background:#121926;color:#d5deea}
.muted{color:var(--muted)}
.row{display:grid;grid-template-columns:1fr 1fr;gap:10px}
code,pre{background:#0a1018;border:1px solid var(--line);border-radius:8px;color:#f4f7fb}
code{padding:1px 4px}
pre{padding:12px;overflow:auto}
table{width:100%;border-collapse:collapse}
th,td{text-align:left;border-bottom:1px solid rgba(255,255,255,.08);padding:9px;vertical-align:top;color:#eef2f7}
th{font-size:12px;text-transform:uppercase;color:#dbe4f0;background:#0a1018}
.panel table, .record-card table{background:#0a1018}
.panel table td, .panel table th, .record-card table td, .record-card table th{color:#f5f7fb}
.panel table .muted, .record-card .muted{color:#a7b0bf}
.preview-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.record-card{border:1px solid var(--line);border-radius:8px;background:rgba(8,12,18,.98);padding:14px;box-shadow:0 1px 0 rgba(15,23,42,.02)}
.record-card h3{margin:0 0 6px;font-size:15px;color:#f8fafc}
.record-card p{margin:7px 0}
.summary-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-top:12px}
.summary-card{border:1px solid var(--line);border-radius:8px;background:rgba(8,12,18,.96);padding:12px}
.summary-card strong{display:block;font-size:24px;color:#f8fafc}
.record-meta{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}
.badge{display:inline-flex;border:1px solid var(--line);border-radius:999px;padding:3px 9px;background:#111827;color:#e5edf7;font-size:12px;font-weight:700}
.preview-text{max-height:112px;overflow:auto;color:#d9e3ef}
.mini-list{margin:8px 0 0;padding-left:18px;color:#d9e3ef}
.mini-list li{margin:3px 0;overflow-wrap:anywhere}
.media-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.media-card{border:1px solid var(--line);border-radius:10px;background:#fff;overflow:hidden}
.media-thumb{width:100%;aspect-ratio:4/3;object-fit:cover;display:block;background:#f1f5f9}
.media-caption{padding:10px;font-size:12px;color:#475467;word-break:break-word}
.crawl-map{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
.crawl-sector{border:1px solid var(--line);border-radius:10px;background:var(--bg-soft);padding:12px}
.crawl-sector h3{margin:0 0 6px;font-size:14px}
.crawl-sector .muted{font-size:12px}
.crawl-pills{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.crawl-pill{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--line);border-radius:999px;background:#0d0d0d;color:#ffd8b2;padding:6px 10px;font-size:12px;max-width:100%}
.crawl-pill span{opacity:.78}
.depth-bars{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin-top:12px}
.depth-bar{border:1px solid var(--line);border-radius:10px;background:#0b0b0b;padding:10px}
.depth-bar strong{display:block;font-size:20px;color:var(--accent)}
.depth-bar .muted{font-size:12px}
.tool-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.tool-card{border:1px solid var(--line);border-radius:10px;background:var(--bg-soft);padding:14px}
.tool-card h3{margin:0 0 6px;font-size:14px}
.tool-card p{margin:6px 0 0;color:var(--muted)}
.tool-actions{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.tool-screens{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}
.tool-shot{display:block;border:1px solid var(--line);border-radius:10px;overflow:hidden;background:#0d0d0d}
.tool-shot img{display:block;width:100%;aspect-ratio:4/3;object-fit:cover}
.tool-shot span{display:block;padding:8px 10px;font-size:12px;color:#ffd8b2;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.raw-record summary{cursor:pointer;color:var(--accent);font-weight:800;margin-top:8px}
.raw-record pre{max-height:220px}
.status-running{color:var(--warn);font-weight:700}.status-finished{color:var(--success);font-weight:700}.status-error{color:var(--danger);font-weight:700}
.eyebrow{display:inline-flex;align-items:center;font-size:11px;font-weight:800;color:var(--accent);text-transform:uppercase;letter-spacing:.03em}
.section-shell{display:grid;grid-template-columns:1fr;gap:18px}
.subgrid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
.pill-row{display:flex;flex-wrap:wrap;gap:8px}
.panel-title{display:flex;align-items:baseline;justify-content:space-between;gap:12px}
.panel-title h2{margin-bottom:0}
.devil-mark{display:inline-flex;align-items:center;justify-content:center;width:20px;height:20px;margin-left:8px;border-radius:999px;background:rgba(255,26,0,.18);border:1px solid rgba(255,26,0,.34);color:#ff1a00;font-size:12px;line-height:1}
.devil-mark::before{content:"\\2666"}
.compact{padding:14px}
.stack-tight{display:grid;gap:12px}
.hidden{display:none}
@media(max-width:1080px){.hero,.grid,.stacked-grid{grid-template-columns:1fr}}
@media(max-width:1080px){.hero-stats,.subgrid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:850px){.preview-grid{grid-template-columns:1fr}}
@media(max-width:850px){.row,.form-grid{grid-template-columns:1fr}}
@media(max-width:850px){.topbar-inner{padding:16px 18px;align-items:flex-start;flex-direction:column}}
@media(max-width:850px){.media-grid{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:540px){.media-grid{grid-template-columns:1fr}}
@media(max-width:850px){.crawl-map{grid-template-columns:1fr}}
@media(max-width:1080px){.tool-grid,.tool-screens{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:640px){.tool-grid,.tool-screens{grid-template-columns:1fr}}
"""


def page(title: str, body: str) -> bytes:
    return f"""<!doctype html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title><style>{CSS}</style></head>
<body><header class="topbar"><div class="topbar-inner"><div><div class="brand">Advanced Scraper</div><div class="brand-sub">Local crawl studio for whole-site capture, preview, and export</div></div><div class="topbar-chip">URL-only quick path • Advanced mode • Playwright</div></div></header>
<nav class="tabs"><a href="/">Dashboard</a><a href="/runs">Runs</a><a href="/preview">Preview</a><a href="/archives">Archives</a><a href="/privacy">Privacy</a><a href="/install">Install</a><a href="/features">Features</a><a href="/recipes">Recipes</a><a href="/help">Help</a></nav>
<main class="app-main">{body}</main></body>
</html>""".encode("utf-8")


class ProductHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/":
            self.render_home()
        elif path == "/runs":
            self.render_runs()
        elif path == "/preview":
            self.render_preview()
        elif path == "/file":
            self.render_file()
        elif path == "/image":
            self.render_image()
        elif path == "/archives":
            self.render_archives()
        elif path == "/privacy":
            self.render_privacy()
        elif path == "/install":
            self.render_install()
        elif path == "/features":
            self.render_features()
        elif path == "/recipes":
            self.render_recipes()
        elif path == "/help":
            self.render_help()
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        data = {key: values[-1] for key, values in parse_qs(body).items()}
        parsed = urlparse(self.path)
        path = parsed.path
        query_data = {key: values[-1] for key, values in parse_qs(parsed.query).items()}
        data.update(query_data)
        if path == "/profiles":
            self.create_profile(data)
        elif path == "/run":
            self.start_run(data)
        elif path == "/quick-run":
            self.quick_run(data)
        elif path == "/import":
            self.import_archive(data)
        else:
            self.send_error(404)

    def render_home(self) -> None:
        profiles = list_profiles()
        runs = list_runs(12)
        archives = list_archives()
        profile_options = "\n".join(
            f'<option value="{p["id"]}">{html.escape(p["name"])}</option>' for p in profiles
        )
        profile_rows = "\n".join(
            f"<tr><td>{p['id']}</td><td>{html.escape(p['name'])}</td><td><code>{html.escape(json.dumps(p['config'])[:220])}</code></td></tr>"
            for p in profiles
        ) or '<tr><td colspan="3" class="muted">No saved profiles yet.</td></tr>'
        latest_run = runs[0] if runs else None
        latest_status = html.escape(str(latest_run["status"])) if latest_run else "No runs yet"
        latest_profile = html.escape(str(latest_run.get("profile_name") or "Ad hoc")) if latest_run else "None"
        latest_output = html.escape(str(latest_run["output_path"])) if latest_run else ""
        body = f"""
<section class="hero">
  <div class="hero-panel">
    <div class="hero-copy">
      <div class="hero-kicker">Whole-site capture studio</div>
      <h1>Turn one URL into a full local site map, media index, and export package.</h1>
      <p>URL-only quick capture is the default. It uses the strong owner preset, Playwright rendering, sitemap seeding, media discovery, API capture, and login/session support when you need it.</p>
      <div class="hero-actions">
        <a class="button" href="/preview">Open Preview</a>
        <a class="button secondary" href="/runs">View Runs</a>
        <a class="button ghost" href="/help">How it works</a>
      </div>
    </div>
    <div class="hero-stats">
      <div class="stat-card"><span class="muted">Profiles</span><strong>{len(profiles)}</strong><span class="muted">Saved crawl configs</span></div>
      <div class="stat-card"><span class="muted">Runs</span><strong>{len(runs)}</strong><span class="muted">Recent crawl jobs</span></div>
      <div class="stat-card"><span class="muted">Archives</span><strong>{len(archives)}</strong><span class="muted">Portable site zips</span></div>
      <div class="stat-card"><span class="muted">Last run</span><strong>{latest_status if latest_status != 'No runs yet' else '—'}</strong><span class="muted">{latest_profile}</span></div>
    </div>
  </div>
  <section class="hero-panel launcher">
    <div class="panel-title"><h2>Quick capture</h2><span class="eyebrow">Type URL only</span></div>
    <form method="post" action="/quick-run">
      <div>
        <label>Website URL</label>
        <input name="url" required placeholder="https://example.com">
      </div>
      <div class="pill-row">
        <button type="submit" formaction="/quick-run?mode=quick" formmethod="post">Scrape Site</button>
        <button type="submit" formaction="/quick-run?mode=whole" formmethod="post" class="secondary">Whole-site Mode</button>
        <button type="submit" formaction="/quick-run?mode=owner" formmethod="post" class="secondary">Owner Mode</button>
        <button type="button" class="secondary" onclick="fillPreset('whole')">Fill whole-site preset</button>
        <button type="button" class="secondary" onclick="fillPreset('owner')">Fill owner mode</button>
        <label style="display:inline-flex;align-items:center;gap:8px;font-weight:750;margin:0"><input type="checkbox" id="showAdvanced" style="width:auto"> Advanced mode</label>
      </div>
    </form>
    <p class="muted" style="margin:12px 0 0">The fast path runs with JS rendering, deep crawl limits, media capture, API capture, DOM snapshots, and zip export already on.</p>
    <p class="muted" style="margin:8px 0 0">Latest output: <code>{latest_output or "No run output yet"}</code></p>
  </section>
</section>
{render_tool_strip(runs, archives)}
<section class="section-shell">
  <div class="grid">
    <section class="panel" id="advancedPanel" style="display:none">
      <div class="panel-title"><h2>New Profile</h2><span class="eyebrow">Advanced control</span></div>
      <form method="post" action="/profiles">
        <div class="form-grid">
          <div class="full"><label>Name</label><input name="name" required placeholder="Product monitor"></div>
          <div class="full"><label>Seed URLs</label><textarea name="seeds" required placeholder="https://example.com"></textarea></div>
          <div><label>Max pages</label><input name="max_pages" value="1000"></div>
          <div><label>Max depth</label><input name="max_depth" value="6"></div>
          <div><label>Workers</label><input name="workers" value="6"></div>
          <div><label>Rate limit seconds</label><input name="rate_limit" value="1.0"></div>
          <div><label>Timeout seconds</label><input name="timeout" value="20"></div>
          <div><label>Retries</label><input name="retries" value="2"></div>
          <div><label>Max images per page</label><input name="max_images" value="200"></div>
          <div><label>Max media per page</label><input name="max_media" value="200"></div>
          <div><label>Max API endpoints per page</label><input name="max_api_endpoints" value="200"></div>
          <div class="full"><label>Include regex</label><input name="include" placeholder="/products/"></div>
          <div class="full"><label>Exclude regex</label><input name="exclude" placeholder="/cart|/login"></div>
          <div class="full"><label>CSS selectors</label><input name="css" placeholder="h1,.price,#main"></div>
          <div class="full"><label>Regex extractors</label><input name="regex" placeholder="\\$[0-9,.]+"></div>
          <div class="full"><label>Structured schema JSON</label><textarea name="schema_json" placeholder='[{{"name":"price","selector":".price","kind":"text","required":true}}]'></textarea></div>
          <div class="full"><label>Click selectors</label><input name="click_selectors" placeholder=".load-more,.next"></div>
          <div class="full"><label>Wait selectors</label><input name="wait_selectors" placeholder=".results,.listing"></div>
          <div><label>Scroll passes</label><input name="scrolls" value="6"></div>
          <div><label>Scroll pause ms</label><input name="scroll_pause_ms" value="900"></div>
          <div><label>Extra wait ms</label><input name="wait_ms" value="0"></div>
          <div><label>Browser mode</label><select name="browser_mode"><option value="http">HTTP mode</option><option value="mixed" selected>Mixed mode</option><option value="playwright">Playwright mode</option></select></div>
          <div><label>Session name</label><input name="session_name" placeholder="site-session"></div>
          <div class="full"><label>Login URL</label><input name="login_url" placeholder="https://example.com/login"></div>
          <div><label>Username</label><input name="username" placeholder="name@example.com"></div>
          <div><label>Password</label><input name="password" type="password" placeholder="password"></div>
          <div><label>Username selector</label><input name="username_selector" placeholder="input[name='email']"></div>
          <div><label>Password selector</label><input name="password_selector" placeholder="input[name='password']"></div>
          <div><label>Submit selector</label><input name="submit_selector" placeholder="button[type='submit']"></div>
          <div><label>Login wait selector</label><input name="login_wait_selector" placeholder=".account,.dashboard"></div>
          <div class="full"><label>Authorized proxy or VPN endpoint</label><input name="proxy" placeholder="http://user:pass@host:port"></div>
          <div class="full"><label><input type="checkbox" name="sitemaps" value="1" checked style="width:auto"> Use sitemaps</label></div>
          <div class="full"><label><input type="checkbox" name="save_dom" value="1" checked style="width:auto"> Save DOM snapshots</label></div>
          <div class="full"><label><input type="checkbox" name="download_assets" value="1" checked style="width:auto"> Download linked images/files</label></div>
          <div class="full"><label><input type="checkbox" name="archive" value="1" checked style="width:auto"> Create zip archive after runs</label></div>
          <div class="full"><label><input type="checkbox" name="render_js" value="1" checked style="width:auto"> Render JavaScript pages</label></div>
          <div class="full"><label><input type="checkbox" name="save_screenshots" value="1" checked style="width:auto"> Save Playwright screenshots</label></div>
          <div class="full"><label><input type="checkbox" name="resume_failed" value="1" checked style="width:auto"> Resume failed URLs</label></div>
          <div class="full"><label><input type="checkbox" name="privacy_mode" value="1" checked style="width:auto"> Privacy mode</label></div>
        </div>
        <div class="pill-row" style="margin-top:12px">
        <button type="button" class="secondary" onclick="fillPreset('whole')">Fill whole-site preset</button>
        <button type="button" class="secondary" onclick="fillPreset('owner')">Fill owner mode</button>
          <button type="submit">Save Profile</button>
        </div>
      </form>
    </section>
    <section class="panel">
      <div class="panel-title"><h2>Run Profile</h2><span class="eyebrow">Saved profiles</span></div>
      <form method="post" action="/run">
        <label>Profile</label><select name="profile_id" required>{profile_options}</select>
        <label>Output format</label><select name="format"><option>jsonl</option><option>csv</option><option>xml</option><option>sqlite</option></select>
        <div class="pill-row" style="margin-top:12px">
          <button type="submit">Start Crawl</button>
          <a class="button secondary" href="/runs">View Runs</a>
          <a class="button ghost" href="/archives">Archives</a>
          <a class="button ghost" href="/help">Help</a>
        </div>
      </form>
      <p class="muted" style="margin-top:12px">Data is stored in <code>{html.escape(str(APP_DIR))}</code></p>
      <h2 style="margin-top:22px">Import Site Zip</h2>
      <form method="post" action="/import">
        <label>Zip path on this computer</label><input name="zip_path" required placeholder="/home/007-JB/Downloads/site.zip">
        <div style="margin-top:12px"><button type="submit">Import Zip</button></div>
      </form>
    </section>
  </div>
  <details class="details" style="display:none">
  <summary><strong>Advanced setup</strong></summary>
  <section class="panel" style="margin-top:18px">
    <div class="panel-title"><h2>Saved Profiles</h2><span class="eyebrow">Config history</span></div>
    <table><thead><tr><th>ID</th><th>Name</th><th>Config</th></tr></thead><tbody>{profile_rows}</tbody></table>
  </section>
  </details>
</section>
<script>
document.getElementById('showAdvanced')?.addEventListener('change', (event) => {{
  const panel = document.getElementById('advancedPanel');
  const details = document.querySelector('details.details');
  const show = event.target.checked;
  if (panel) panel.style.display = show ? '' : 'none';
  if (details) details.style.display = show ? '' : 'none';
}});
function fillPreset(mode) {{
  const advancedToggle = document.getElementById('showAdvanced');
  const panel = document.getElementById('advancedPanel');
  const details = document.querySelector('details.details');
  const preset = mode === 'owner' ? {{
    max_pages: 50000,
    max_depth: 20,
    workers: 16,
    rate_limit: 0.15,
    max_images: 400,
    max_media: 400,
    max_api_endpoints: 300,
    scrolls: 15,
    scroll_pause_ms: 500,
    wait_ms: 1000,
    timeout: 30,
    retries: 4,
    sitemaps: true,
    save_dom: true,
    download_assets: true,
    archive: true,
    render_js: true,
    resume_failed: true,
    privacy_mode: true
  }} : {{
    max_pages: 10000,
    max_depth: 10,
    workers: 10,
    rate_limit: 0.5,
    max_images: 250,
    max_media: 250,
    max_api_endpoints: 200,
    scrolls: 10,
    scroll_pause_ms: 700,
    wait_ms: 500,
    timeout: 20,
    retries: 2,
    sitemaps: true,
    save_dom: true,
    download_assets: true,
    archive: true,
    render_js: true,
    browser_mode: 'mixed',
    resume_failed: true,
    privacy_mode: true
  }};
  if (mode === 'owner') {{
    preset.browser_mode = 'playwright';
  }}
  document.querySelectorAll('input[name="max_pages"]').forEach((el) => el.value = preset.max_pages);
  document.querySelectorAll('input[name="max_depth"]').forEach((el) => el.value = preset.max_depth);
  document.querySelectorAll('input[name="workers"]').forEach((el) => el.value = preset.workers);
  document.querySelectorAll('input[name="rate_limit"]').forEach((el) => el.value = preset.rate_limit);
  document.querySelectorAll('input[name="timeout"]').forEach((el) => el.value = preset.timeout);
  document.querySelectorAll('input[name="retries"]').forEach((el) => el.value = preset.retries);
  document.querySelectorAll('input[name="max_images"]').forEach((el) => el.value = preset.max_images || 200);
  document.querySelectorAll('input[name="max_media"]').forEach((el) => el.value = preset.max_media || 200);
  document.querySelectorAll('input[name="max_api_endpoints"]').forEach((el) => el.value = preset.max_api_endpoints || 200);
  document.querySelectorAll('input[name="scrolls"]').forEach((el) => el.value = preset.scrolls);
  document.querySelectorAll('input[name="scroll_pause_ms"]').forEach((el) => el.value = preset.scroll_pause_ms);
  document.querySelectorAll('input[name="wait_ms"]').forEach((el) => el.value = preset.wait_ms);
  document.querySelectorAll('input[name="schema_json"]').forEach((el) => {{
    if (!el.value) el.value = '[{{"name":"title","selector":"h1","kind":"text","required":true}},{{"name":"price","selector":".price","kind":"text"}},{{"name":"description","selector":".description","kind":"text"}}]';
  }});
  ["sitemaps", "save_dom", "download_assets", "archive", "render_js", "resume_failed", "privacy_mode"].forEach((name) => {{
    document.querySelectorAll(`input[name="${{name}}"]`).forEach((el) => el.checked = preset[name]);
  }});
  const browserMode = document.querySelector('select[name="browser_mode"]');
  if (browserMode && preset.browser_mode) browserMode.value = preset.browser_mode;
  const css = document.querySelector('input[name="css"]');
  const regex = document.querySelector('input[name="regex"]');
  const clickSelectors = document.querySelector('input[name="click_selectors"]');
  const waitSelectors = document.querySelector('input[name="wait_selectors"]');
  const sessionName = document.querySelector('input[name="session_name"]');
  const loginUrl = document.querySelector('input[name="login_url"]');
  const username = document.querySelector('input[name="username"]');
  const password = document.querySelector('input[name="password"]');
  const usernameSelector = document.querySelector('input[name="username_selector"]');
  const passwordSelector = document.querySelector('input[name="password_selector"]');
  const submitSelector = document.querySelector('input[name="submit_selector"]');
  const loginWaitSelector = document.querySelector('input[name="login_wait_selector"]');
  if (css && !css.value) css.value = "h1,h2,h3,.title,.price,.description";
  if (regex && !regex.value) regex.value = "\\$[0-9,.]+|https?://[^\\s\"'<>]+";
  if (clickSelectors && !clickSelectors.value) clickSelectors.value = ".load-more,.next,.show-more";
  if (waitSelectors && !waitSelectors.value) waitSelectors.value = ".results,.listing,.posts";
  if (sessionName && !sessionName.value) sessionName.value = "site-session";
  if (loginUrl && !loginUrl.value) loginUrl.value = "https://example.com/login";
  if (usernameSelector && !usernameSelector.value) usernameSelector.value = "input[name='email'], input[type='email'], #email, #username";
  if (passwordSelector && !passwordSelector.value) passwordSelector.value = "input[name='password'], #password";
  if (submitSelector && !submitSelector.value) submitSelector.value = "button[type='submit'], input[type='submit']";
  if (loginWaitSelector && !loginWaitSelector.value) loginWaitSelector.value = ".account,.dashboard";
  if (advancedToggle) {{
    advancedToggle.checked = true;
  }}
  if (panel) {{
    panel.style.display = '';
    panel.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
  }}
  if (details) {{
    details.style.display = '';
    details.open = true;
  }}
}}
function fillBrowserTools(mode) {{
  fillPreset('owner');
  const renderJs = document.querySelector('input[name="render_js"]');
  const saveScreenshots = document.querySelector('input[name="save_screenshots"]');
  const browserMode = document.querySelector('select[name="browser_mode"]');
  const scrolls = document.querySelector('input[name="scrolls"]');
  const waitMs = document.querySelector('input[name="wait_ms"]');
  const clickSelectors = document.querySelector('input[name="click_selectors"]');
  const waitSelectors = document.querySelector('input[name="wait_selectors"]');
  const loginUrl = document.querySelector('input[name="login_url"]');
  if (renderJs) renderJs.checked = true;
  if (saveScreenshots) saveScreenshots.checked = true;
  if (browserMode) browserMode.value = mode === 'login' ? 'playwright' : mode === 'capture' ? 'mixed' : 'playwright';
  if (scrolls) scrolls.value = mode === 'capture' ? 20 : 15;
  if (waitMs) waitMs.value = mode === 'capture' ? 400 : 900;
  if (clickSelectors && !clickSelectors.value) clickSelectors.value = ".load-more,.next,.show-more,button";
  if (waitSelectors && !waitSelectors.value) waitSelectors.value = ".results,.listing,.posts,.content";
  if (loginUrl && mode === 'login' && !loginUrl.value) loginUrl.value = "https://example.com/login";
  if (mode === 'login') {{
    const username = document.querySelector('input[name="username"]');
    const password = document.querySelector('input[name="password"]');
    const usernameSelector = document.querySelector('input[name="username_selector"]');
    const passwordSelector = document.querySelector('input[name="password_selector"]');
    const submitSelector = document.querySelector('input[name="submit_selector"]');
    const loginWaitSelector = document.querySelector('input[name="login_wait_selector"]');
    if (usernameSelector && !usernameSelector.value) usernameSelector.value = "input[name='email'], input[type='email'], #email, #username";
    if (passwordSelector && !passwordSelector.value) passwordSelector.value = "input[name='password'], #password";
    if (submitSelector && !submitSelector.value) submitSelector.value = "button[type='submit'], input[type='submit']";
    if (loginWaitSelector && !loginWaitSelector.value) loginWaitSelector.value = ".account,.dashboard";
    if (username && !username.value) username.value = "you@example.com";
    if (password && !password.value) password.value = "your-password";
  }}
}}
</script>
"""
        self.respond(page("Advanced Scraper", body))

    def render_runs(self) -> None:
        rows = ""
        for run in list_runs():
            status = html.escape(run["status"])
            rows += f"""<tr>
<td>{run["id"]}</td><td>{html.escape(run.get("profile_name") or "Ad hoc")}</td>
<td class="status-{status}">{status}</td><td>{run["pages"]}</td><td>{run["errors"]}</td>
<td><code>{html.escape(run["output_path"])}</code></td><td>{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(run["started_at"]))}</td>
<td><a class="button" href="/preview?run_id={run["id"]}">Preview</a></td>
</tr>"""
        rows = rows or '<tr><td colspan="7" class="muted">No runs yet.</td></tr>'
        body = f"""<section class="panel"><h2>Run History</h2><p><a class="button" href="/">Back</a></p>
<table><thead><tr><th>ID</th><th>Profile</th><th>Status</th><th>Pages</th><th>Errors</th><th>Output</th><th>Started</th><th>Preview</th></tr></thead><tbody>{rows}</tbody></table></section>"""
        self.respond(page("Runs", body))

    def render_preview(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        run_id_text = (query.get("run_id") or [""])[0]
        search = (query.get("q") or [""])[0].strip()
        status_filter = (query.get("status") or [""])[0].strip()
        runs = list_runs(100)
        run = get_run(int(run_id_text)) if run_id_text.isdigit() else (runs[0] if runs else None)
        run_options = "\n".join(
            f'<option value="{item["id"]}" {"selected" if run and item["id"] == run["id"] else ""}>#{item["id"]} - {html.escape(item.get("profile_name") or "Ad hoc")} - {html.escape(item["status"])}</option>'
            for item in runs
        )
        if not run:
            body = '<section class="panel"><h2>Preview</h2><p class="muted">No scrape runs yet.</p><p><a class="button" href="/">Start a scrape</a></p></section>'
            self.respond(page("Preview", body))
            return

        all_records, message = load_preview_records(Path(run["output_path"]), limit=200)
        filtered = filter_records(all_records, search, status_filter)
        records = filtered[:40]
        cards = "\n".join(render_record_card(record) for record in records)
        if not cards:
            cards = f'<p class="muted">{html.escape(message or "No records available yet. If the scrape is still running, refresh in a few seconds.")}</p>'
        refresh = '<meta http-equiv="refresh" content="4">' if run["status"] == "running" else ""
        summary = preview_summary(all_records)
        crawl_map = render_crawl_map(all_records)
        site_map = render_site_map(all_records)
        media_index = render_media_index(all_records)
        image_gallery = render_image_gallery(all_records)
        api_index = render_api_index(all_records)
        hidden_index = render_hidden_index(all_records)
        collected_index = render_collected_data(list_result_index(run["id"], limit=120))
        status_options = "\n".join(
            f'<option value="{html.escape(item)}" {"selected" if item == status_filter else ""}>{html.escape(item or "Any status")}</option>'
            for item in ["", *summary["statuses"]]
        )
        file_links = f"""
<p>
  <a class="button secondary" href="/file?run_id={run["id"]}&kind=output">View output file</a>
  <a class="button secondary" href="/file?run_id={run["id"]}&kind=events">View event log</a>
</p>
"""
        body = f"""
{refresh}
<section class="panel">
  <h2>Scrape Preview</h2>
  <form method="get" action="/preview" class="grid">
    <div><label>Run</label><select name="run_id">{run_options}</select></div>
    <div><label>Search title, URL, text</label><input name="q" value="{html.escape(search)}" placeholder="product, price, error, URL..."></div>
    <div><label>Status</label><select name="status">{status_options}</select></div>
    <div style="align-self:end"><button type="submit">Update Preview</button> <a class="button secondary" href="/runs">Runs</a></div>
  </form>
  <div class="summary-grid">
    <div class="summary-card">Loaded<strong>{len(all_records)}</strong></div>
    <div class="summary-card">Showing<strong>{len(records)}</strong></div>
    <div class="summary-card">Errors<strong>{summary["errors"]}</strong></div>
    <div class="summary-card">Avg words<strong>{summary["avg_words"]}</strong></div>
    <div class="summary-card">API endpoints<strong>{summary["api_endpoints"]}</strong></div>
  </div>
  <p class="muted">Showing up to 40 matching records from <code>{html.escape(run["output_path"])}</code>. Running scrapes auto-refresh every 4 seconds.</p>
  {file_links}
</section>
<section class="panel" style="margin-top:18px">
  <h2>Inside The Site</h2>
  <div class="stack">
    <div class="panel" style="margin:0">
      <h2>Collected Data</h2>
      {collected_index}
    </div>
    <div class="panel" style="margin:0">
      <h2>Crawl Map</h2>
      {crawl_map}
    </div>
    <div class="panel" style="margin:0">
      <h2>Site Map</h2>
      {site_map}
    </div>
    <div class="panel" style="margin:0">
      <h2>Media Index</h2>
      {media_index}
    </div>
    <div class="panel" style="margin:0">
      <h2>Image Gallery</h2>
      {image_gallery}
    </div>
    <div class="panel" style="margin:0">
      <h2>API Index</h2>
      {api_index}
    </div>
    <div class="panel" style="margin:0">
      <h2>Hidden Content</h2>
      {hidden_index}
    </div>
  </div>
</section>
<section class="panel" style="margin-top:18px">
  <h2>What The Scraper Found</h2>
  <div class="preview-grid">{cards}</div>
</section>
"""
        self.respond(page("Preview", body))

    def render_file(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        run_id_text = (query.get("run_id") or [""])[0]
        kind = (query.get("kind") or ["output"])[0]
        if not run_id_text.isdigit():
            self.send_error(400)
            return
        run = get_run(int(run_id_text))
        if not run:
            self.send_error(404)
            return
        target = Path(run["event_log_path"] if kind == "events" else run["output_path"])
        if not safe_app_file(target):
            self.send_error(403)
            return
        if not target.exists():
            self.respond_text("File has not been created yet.", 404)
            return
        text = target.read_text(encoding="utf-8", errors="replace")
        if len(text) > 250_000:
            text = text[:250_000] + "\n\n...truncated to first 250 KB..."
        self.respond_text(text)

    def render_image(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        path_value = (query.get("path") or [""])[0]
        if not path_value:
            self.send_error(400)
            return
        target = Path(path_value).expanduser()
        if not safe_app_file(target):
            self.send_error(403)
            return
        if not target.exists():
            self.send_error(404)
            return
        data = target.read_bytes()
        suffix = target.suffix.lower()
        if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".gif"}:
            self.send_error(415)
            return
        mime = "image/png" if suffix == ".png" else "image/jpeg" if suffix in {".jpg", ".jpeg"} else "image/webp" if suffix == ".webp" else "image/gif"
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def render_archives(self) -> None:
        archive_rows = "\n".join(
            f"<tr><td><code>{html.escape(str(path))}</code></td><td>{path.stat().st_size // 1024} KB</td></tr>"
            for path in list_archives()
        ) or '<tr><td colspan="2" class="muted">No archives yet.</td></tr>'
        import_rows = "\n".join(
            f"<tr><td><code>{html.escape(str(path))}</code></td></tr>" for path in list_imports()
        ) or '<tr><td class="muted">No imported archives yet.</td></tr>'
        body = f"""<section class="panel"><h2>Site Archives</h2><p><a class="button" href="/">Back</a></p>
<h2>Saved Zip Archives</h2><table><thead><tr><th>Path</th><th>Size</th></tr></thead><tbody>{archive_rows}</tbody></table>
<h2 style="margin-top:22px">Imported Sites</h2><table><thead><tr><th>Folder</th></tr></thead><tbody>{import_rows}</tbody></table></section>"""
        self.respond(page("Archives", body))

    def render_privacy(self) -> None:
        body = """
<div class="stack">
<section class="panel">
  <h2>Privacy Options</h2>
  <p>This app runs locally on your computer. It does not make you anonymous by itself, and it cannot guarantee that no one can identify you.</p>
  <table><tbody>
    <tr><td><strong>Privacy mode</strong></td><td>Strips common tracking URL parameters and redacts common emails, phone numbers, and SSN-like values from saved output.</td></tr>
    <tr><td><strong>Authorized proxy/VPN</strong></td><td>Routes scraper requests through a proxy endpoint you own, pay for, or are allowed to use.</td></tr>
    <tr><td><strong>Local storage</strong></td><td>Profiles, outputs, logs, and archives stay under /home/007-JB/.advanced-scraper.</td></tr>
    <tr><td><strong>Polite crawling</strong></td><td>Robots.txt, crawl-delay, and rate limits remain available.</td></tr>
  </tbody></table>
</section>
<section class="panel">
  <h2>What I Won't Do</h2>
  <p>I will not configure stolen/open proxies, use someone else's network address without permission, bypass identity checks, or evade site security. Use a legitimate VPN or proxy service instead.</p>
</section>
<section class="panel">
  <h2>Proxy Format</h2>
  <pre>http://user:password@proxy-host:port
http://proxy-host:port</pre>
  <p>Paste that into the proxy field on the Dashboard. Leave it blank if you are using a system-wide VPN app.</p>
</section>
</div>
"""
        self.respond(page("Privacy", body))

    def render_install(self) -> None:
        body = f"""
<div class="stack">
<section class="panel">
  <h2>Install</h2>
  <p>The app is already installed locally. Run this anytime to refresh the launcher:</p>
  <pre>/home/007-JB/advanced-scraper/install-local.sh</pre>
  <p>Start the dashboard from a terminal:</p>
  <pre>advanced-scraper</pre>
  <p>Then open:</p>
  <pre>http://127.0.0.1:{PORT}</pre>
  <p>Program folder:</p><pre>/home/007-JB/advanced-scraper</pre>
  <p>Saved data folder:</p><pre>{html.escape(str(APP_DIR))}</pre>
</section>
<section class="panel">
  <h2>Desktop Launcher</h2>
  <p>A desktop/app-menu launcher was installed here:</p>
  <pre>/home/007-JB/.local/share/applications/advanced-scraper.desktop</pre>
  <p>If your app menu does not refresh immediately, log out and back in, or start it from terminal with <code>advanced-scraper</code>.</p>
</section>
</div>
"""
        self.respond(page("Install", body))

    def render_features(self) -> None:
        rows = [
            ("Discovery", "Sitemaps, robots.txt, internal links, canonical URLs, hreflang alternates, pagination, include/exclude rules, depth limits, URL dedupe."),
            ("Rendering", "Static HTML now; optional Playwright mode with clicks, waits, scrolling, lazy-load capture, and session state."),
            ("Extraction", "Meta tags, Open Graph, Twitter cards, JSON-LD, headings, links, tables, images, files, CSS selectors, XPath subset, regex, JSON APIs."),
            ("Schema Builder", "Named structured fields from CSS or XPath selectors with required fields, types, and validation issues."),
            ("Session", "Custom user-agent, headers, cookies, token headers, persistent browser sessions, proxy-session pairing."),
            ("Reliability", "Rate limits, adaptive backoff, retries, timeouts, checkpoint state, event logs, failed-page records, resume failed crawls."),
            ("Data Quality", "URL normalization, content hashes, text cleanup, dedupe, structured JSONL, markdown output, semantic chunks."),
            ("Exports", "JSONL, CSV, XML, SQLite, webhooks, downloaded assets, portable site zip archives."),
            ("Storage", "Profiles, run history, archives, imports, DOM snapshots, assets, and session files under ~/.advanced-scraper."),
            ("Compliance", "Robots support on by default, same-domain crawling by default, crawl-delay support, allow-list rules, audit logs, PII redaction."),
        ]
        table_rows = "".join(f"<tr><td><strong>{html.escape(a)}</strong></td><td>{html.escape(b)}</td></tr>" for a, b in rows)
        body = f"""<section class="panel"><h2>Features</h2><table><tbody>{table_rows}</tbody></table>
<p class="muted">The app does not include CAPTCHA bypass, auth bypass, or stealth evasion. Use it only on sites you are allowed to crawl.</p></section>"""
        self.respond(page("Features", body))

    def render_recipes(self) -> None:
        body = """
<div class="stack">
<section class="panel"><h2>Whole-Site Archive</h2>
<p>Create a profile with the root URL, enable the whole-site preset, render JavaScript, save DOM snapshots, download linked images/files, and create zip archive after runs.</p>
<pre>Seed URLs: https://example.com
Max pages: 10000
Max depth: 8
Use sitemaps: checked
Render JavaScript: checked
Save DOM snapshots: checked
Download linked images/files: checked
Create zip archive after runs: checked</pre></section>
<section class="panel"><h2>Product Monitor</h2>
<pre>Include regex: /products/
Exclude regex: /cart|/account|/login
CSS selectors: h1,.price,.sku
Regex extractors: \\$[0-9,.]+</pre></section>
<section class="panel"><h2>Import A Captured Site</h2>
<p>Use the Dashboard import form and paste the full zip path, for example:</p>
<pre>/home/007-JB/Downloads/example-site.zip</pre></section>
<section class="panel"><h2>Command Line Examples</h2>
<pre>cd /home/007-JB/advanced-scraper
python3 -m advanced_scraper.cli https://example.com --sitemaps --render-js --scrolls 8 --max-pages 1000 -o output.sqlite --format sqlite
python3 -m advanced_scraper.cli https://example.com --whole-site -o whole-site.sqlite --format sqlite
python3 -m advanced_scraper.cli https://example.com --css h1 --css .price --regex '\\$[0-9,.]+' -o products.jsonl
python3 -m advanced_scraper.manage import-archive /home/007-JB/Downloads/site.zip</pre></section>
</div>
"""
        self.respond(page("Recipes", body))

    def render_help(self) -> None:
        body = """
<div class="stack">
<section class="panel"><h2>How To Use</h2>
<h3>Simple Mode</h3>
<ol>
  <li>Paste a URL on the Dashboard.</li>
  <li>Click Scrape Site.</li>
  <li>Open Runs to watch progress and find the output file.</li>
  <li>Open Archives to find the zip package.</li>
</ol>
<h3>Advanced Mode</h3>
<ol>
  <li>Create a profile with one or more seed URLs.</li>
  <li>Choose crawl limits. Start small, then increase max pages and depth.</li>
  <li>Add include/exclude rules if you only want part of a site.</li>
  <li>Add CSS selectors or regex patterns for specific data.</li>
  <li>Enable sitemaps for broad site coverage.</li>
  <li>Enable DOM snapshots, asset downloads, and zip archive for full-detail capture.</li>
  <li>Save the profile, then run it from the Run Profile panel.</li>
  <li>Check Runs for output paths and Archives for zip packages.</li>
</ol></section>
<section class="panel"><h2>Field Guide</h2>
<table><tbody>
<tr><td><strong>Seed URLs</strong></td><td>Starting pages. Use full URLs like https://example.com.</td></tr>
<tr><td><strong>Max pages</strong></td><td>Hard stop for crawl size.</td></tr>
<tr><td><strong>Max depth</strong></td><td>How many link-click levels from the seed.</td></tr>
<tr><td><strong>Workers</strong></td><td>Parallel fetchers. Higher is faster but heavier.</td></tr>
<tr><td><strong>Rate limit</strong></td><td>Seconds between requests per host.</td></tr>
<tr><td><strong>Include regex</strong></td><td>Only crawl URLs matching these patterns.</td></tr>
<tr><td><strong>Exclude regex</strong></td><td>Skip URLs matching these patterns.</td></tr>
<tr><td><strong>CSS selectors</strong></td><td>Extract text from selectors like h1, .price, #main.</td></tr>
<tr><td><strong>Regex extractors</strong></td><td>Extract matching text from the page HTML.</td></tr>
<tr><td><strong>Use sitemaps</strong></td><td>Add URLs from sitemap files.</td></tr>
<tr><td><strong>Save DOM</strong></td><td>Save HTML snapshots locally.</td></tr>
<tr><td><strong>Download assets</strong></td><td>Download linked images/files.</td></tr>
<tr><td><strong>Create zip archive</strong></td><td>Package the crawl into a portable zip.</td></tr>
</tbody></table></section>
<section class="panel"><h2>Where Files Go</h2>
<pre>Profiles and database: /home/007-JB/.advanced-scraper/scraper.db
Run outputs:           /home/007-JB/.advanced-scraper/runs
Zip archives:          /home/007-JB/.advanced-scraper/archives
Imported sites:        /home/007-JB/.advanced-scraper/imports
DOM snapshots:         /home/007-JB/.advanced-scraper/dom
Assets/files:          /home/007-JB/.advanced-scraper/assets</pre></section>
</div>
"""
        self.respond(page("Help", body))

    def create_profile(self, data: dict[str, str]) -> None:
        config = {
            "seeds": [line.strip() for line in data.get("seeds", "").splitlines() if line.strip()],
            "max_pages": int(data.get("max_pages", "1000") or 1000),
            "max_depth": int(data.get("max_depth", "6") or 6),
            "workers": int(data.get("workers", "6") or 6),
            "rate_limit": float(data.get("rate_limit", "1.0") or 1.0),
            "timeout": int(data.get("timeout", "20") or 20),
            "retries": int(data.get("retries", "2") or 2),
            "max_images": int(data.get("max_images", "200") or 200),
            "max_media": int(data.get("max_media", "200") or 200),
            "max_api_endpoints": int(data.get("max_api_endpoints", "200") or 200),
            "include": [x.strip() for x in data.get("include", "").split(",") if x.strip()],
            "exclude": [x.strip() for x in data.get("exclude", "").split(",") if x.strip()],
            "css": [x.strip() for x in data.get("css", "").split(",") if x.strip()],
            "regex": [x.strip() for x in data.get("regex", "").split(",") if x.strip()],
            "schema_json": data.get("schema_json", "").strip(),
            "click_selectors": [x.strip() for x in data.get("click_selectors", "").split(",") if x.strip()],
            "wait_selectors": [x.strip() for x in data.get("wait_selectors", "").split(",") if x.strip()],
            "scrolls": int(data.get("scrolls", "6") or 6),
            "scroll_pause_ms": int(data.get("scroll_pause_ms", "900") or 900),
            "wait_ms": int(data.get("wait_ms", "0") or 0),
            "browser_mode": data.get("browser_mode", "mixed").strip() or "mixed",
            "session_name": data.get("session_name", "").strip(),
            "login_url": data.get("login_url", "").strip(),
            "username": data.get("username", "").strip(),
            "password": data.get("password", "").strip(),
            "username_selector": data.get("username_selector", "").strip(),
            "password_selector": data.get("password_selector", "").strip(),
            "submit_selector": data.get("submit_selector", "").strip(),
            "login_wait_selector": data.get("login_wait_selector", "").strip(),
            "sitemaps": data.get("sitemaps") == "1",
            "save_dom": data.get("save_dom") == "1",
            "save_screenshots": data.get("save_screenshots") == "1",
            "download_assets": data.get("download_assets") == "1",
            "archive": data.get("archive") == "1",
            "render_js": data.get("render_js") == "1",
            "resume_failed": data.get("resume_failed") == "1",
            "privacy_mode": data.get("privacy_mode") == "1",
            "proxy": data.get("proxy", "").strip(),
        }
        save_profile(data["name"], config)
        self.redirect("/")

    def quick_run(self, data: dict[str, str]) -> None:
        url = data["url"].strip()
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        name = urlparse(url).netloc or "quick-site"
        mode = data.get("mode", "quick")
        config = {
            "seeds": [url],
            "max_pages": 50000 if mode in {"owner", "whole"} else 10000,
            "max_depth": 20 if mode == "owner" else 10,
            "workers": 16 if mode == "owner" else 10,
            "rate_limit": 0.15 if mode == "owner" else 0.5,
            "timeout": 30 if mode == "owner" else 20,
            "retries": 4 if mode == "owner" else 2,
            "max_images": 400 if mode == "owner" else 250,
            "max_media": 400 if mode == "owner" else 250,
            "max_api_endpoints": 300 if mode == "owner" else 200,
            "include": [],
            "exclude": ["/cart", "/checkout", "/account", "/login", "/logout", "/wp-admin", "/search", "?sort=", "?filter="],
            "css": [],
            "regex": [],
            "schema_json": "",
            "click_selectors": [".load-more", ".next", ".show-more", "button"] if mode == "owner" else [".load-more", ".next", ".show-more"],
            "wait_selectors": [".results", ".listing", ".posts", ".content", ".page"] if mode == "owner" else [".results", ".listing", ".posts"],
            "scrolls": 15 if mode == "owner" else 10,
            "scroll_pause_ms": 500 if mode == "owner" else 700,
            "wait_ms": 1000 if mode == "owner" else 500,
            "browser_mode": "playwright" if mode == "owner" else "mixed" if mode == "whole" else "http",
            "session_name": f"quick-{name}",
            "login_url": data.get("login_url", "").strip(),
            "username": data.get("username", "").strip(),
            "password": data.get("password", "").strip(),
            "username_selector": data.get("username_selector", "").strip(),
            "password_selector": data.get("password_selector", "").strip(),
            "submit_selector": data.get("submit_selector", "").strip(),
            "login_wait_selector": data.get("login_wait_selector", "").strip(),
            "sitemaps": True,
            "save_dom": True,
            "save_screenshots": True,
            "download_assets": True,
            "archive": True,
            "render_js": mode != "quick",
            "resume_failed": True,
            "privacy_mode": True,
            "proxy": data.get("proxy", "").strip(),
        }
        profile_label = "Quick Owner" if mode == "owner" else "Quick Whole-Site" if mode == "whole" else "Quick"
        profile_id = save_profile(f"{profile_label} - {name}", config)
        run_stamp = time.strftime("%Y%m%d-%H%M%S")
        output = RUNS_DIR / f"quick-{mode}-{name}-{run_stamp}.jsonl"
        event_log = RUNS_DIR / f"quick-{mode}-{name}-{run_stamp}-events.jsonl"
        command = build_command(config, output, event_log, "jsonl")
        run_id = create_run(profile_id, {"argv": command, "quick": True, "mode": mode}, output, event_log)
        thread = threading.Thread(target=run_command, args=(run_id, command, f"{profile_label} - {name}", config, output, event_log), daemon=True)
        thread.start()
        self.redirect("/runs")

    def start_run(self, data: dict[str, str]) -> None:
        from .storage import get_profile

        profile = get_profile(int(data["profile_id"]))
        if not profile:
            self.send_error(404)
            return
        cfg = profile["config"]
        run_stamp = time.strftime("%Y%m%d-%H%M%S")
        fmt = data.get("format", "jsonl")
        output = RUNS_DIR / f"run-{run_stamp}.{fmt}"
        event_log = RUNS_DIR / f"run-{run_stamp}-events.jsonl"
        command = build_command(cfg, output, event_log, fmt)
        run_id = create_run(profile["id"], {"argv": command}, output, event_log)
        thread = threading.Thread(target=run_command, args=(run_id, command, profile["name"], cfg, output, event_log), daemon=True)
        thread.start()
        self.redirect("/runs")

    def import_archive(self, data: dict[str, str]) -> None:
        try:
            import_site_archive(Path(data["zip_path"]).expanduser())
            self.redirect("/archives")
        except Exception as exc:
            self.respond(page("Import Error", f'<section class="panel"><h2>Import failed</h2><p>{html.escape(str(exc))}</p><p><a class="button" href="/">Back</a></p></section>'), 400)

    def respond(self, body: bytes, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def respond_text(self, body: str, status: int = 200) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def redirect(self, target: str) -> None:
        self.send_response(303)
        self.send_header("Location", target)
        self.end_headers()

    def log_message(self, _fmt: str, *_args: object) -> None:
        return


def build_command(config: dict[str, object], output: Path, event_log: Path, fmt: str) -> list[str]:
    cmd = [
        sys.executable,
        "-m",
        "advanced_scraper.cli",
        *list(config["seeds"]),
        "--output",
        str(output),
        "--format",
        fmt,
        "--state-file",
        str(APP_DIR / "state.json"),
        "--max-pages",
        str(config["max_pages"]),
        "--max-depth",
        str(config["max_depth"]),
        "--workers",
        str(config["workers"]),
        "--rate-limit",
        str(config["rate_limit"]),
        "--timeout",
        str(config.get("timeout", 20)),
        "--retries",
        str(config.get("retries", 2)),
        "--max-images",
        str(config.get("max_images", 200)),
        "--max-media",
        str(config.get("max_media", 200)),
        "--max-api-endpoints",
        str(config.get("max_api_endpoints", 200)),
        "--event-log",
        str(event_log),
    ]
    for key, flag in (("include", "--include"), ("exclude", "--exclude"), ("css", "--css"), ("regex", "--regex")):
        for value in config.get(key, []):
            cmd.extend([flag, str(value)])
    if config.get("schema_json"):
        cmd.extend(["--schema", str(config["schema_json"])])
    for key, flag in (("click_selectors", "--click"), ("wait_selectors", "--wait-for")):
        for value in config.get(key, []):
            cmd.extend([flag, str(value)])
    if config.get("scrolls") is not None:
        cmd.extend(["--scrolls", str(config["scrolls"])])
    if config.get("scroll_pause_ms") is not None:
        cmd.extend(["--scroll-pause-ms", str(config["scroll_pause_ms"])])
    if config.get("wait_ms") is not None:
        cmd.extend(["--wait-ms", str(config["wait_ms"])])
    if config.get("sitemaps"):
        cmd.append("--sitemaps")
    if config.get("save_dom"):
        cmd.extend(["--save-dom", "--dom-dir", str(APP_DIR / "dom")])
    if config.get("save_screenshots"):
        cmd.extend(["--save-screenshots", "--screenshot-dir", str(APP_DIR / "screenshots"), "--screenshot-full-page"])
    if config.get("download_assets"):
        cmd.extend(["--download-assets", "--asset-dir", str(APP_DIR / "assets")])
    if config.get("render_js"):
        cmd.append("--render-js")
    if config.get("resume_failed"):
        cmd.append("--resume-failed")
    if config.get("privacy_mode"):
        cmd.append("--privacy-mode")
    if config.get("session_name"):
        cmd.extend(["--session-name", str(config["session_name"])])
    for key, flag in (
        ("login_url", "--login-url"),
        ("username", "--username"),
        ("password", "--password"),
        ("username_selector", "--username-selector"),
        ("password_selector", "--password-selector"),
        ("submit_selector", "--submit-selector"),
        ("login_wait_selector", "--login-wait-selector"),
    ):
        if config.get(key):
            cmd.extend([flag, str(config[key])])
    if config.get("proxy"):
        cmd.extend(["--proxy", str(config["proxy"])])
    return cmd


def run_command(run_id: int, command: list[str], profile_name: str, config: dict[str, object], output: Path, event_log: Path) -> None:
    try:
        result = subprocess.run(command, cwd=str(Path(__file__).resolve().parents[1]), text=True, capture_output=True)
        if result.returncode == 0:
            try:
                records = load_output_records(output)
                if records:
                    save_result_index(run_id, records)
            except Exception:
                pass
            if config.get("archive"):
                create_site_archive(
                    name=profile_name,
                    output_path=output,
                    event_log_path=event_log,
                    dom_dir=APP_DIR / "dom" if config.get("save_dom") else None,
                    asset_dir=APP_DIR / "assets" if config.get("download_assets") else None,
                    config=config,
                )
            finish_run(run_id, "finished", result.stderr[-1000:])
        else:
            finish_run(run_id, "error", (result.stderr or result.stdout)[-1000:])
    except Exception as exc:
        finish_run(run_id, "error", str(exc))


def load_output_records(output: Path) -> list[dict[str, object]]:
    if not output.exists():
        return []
    try:
        if output.suffix == ".jsonl":
            records: list[dict[str, object]] = []
            with output.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(item, dict):
                        records.append(item)
            return records
        if output.suffix == ".csv":
            with output.open("r", encoding="utf-8", newline="") as handle:
                return [dict(row) for row in csv.DictReader(handle)]
        if output.suffix == ".xml":
            tree = ET.parse(output)
            records = []
            for item in tree.getroot().findall("record"):
                records.append({child.tag: child.text or "" for child in item})
            return records
        if output.suffix in {".sqlite", ".db"}:
            import sqlite3

            with sqlite3.connect(output) as conn:
                rows = conn.execute("select record_json from records order by id desc").fetchall()
            records = []
            for row in rows:
                try:
                    item = json.loads(row[0])
                except (TypeError, json.JSONDecodeError):
                    continue
                if isinstance(item, dict):
                    records.append(item)
            return records
    except Exception:
        return []
    return []


def load_preview_records(output: Path, limit: int = 24) -> tuple[list[dict[str, object]], str]:
    if not output.exists():
        return [], "The output file has not been created yet."
    try:
        if output.suffix == ".jsonl":
            records: list[dict[str, object]] = []
            with output.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(item, dict):
                        records.append(item)
                    if len(records) >= limit:
                        break
            return records, ""
        if output.suffix == ".csv":
            with output.open("r", encoding="utf-8", newline="") as handle:
                return [dict(row) for _, row in zip(range(limit), csv.DictReader(handle))], ""
        if output.suffix == ".xml":
            tree = ET.parse(output)
            records = []
            for item in tree.getroot().findall("record")[:limit]:
                records.append({child.tag: child.text or "" for child in item})
            return records, ""
        if output.suffix == ".sqlite" or output.suffix == ".db":
            import sqlite3

            with sqlite3.connect(output) as conn:
                rows = conn.execute(
                    "select record_json from records order by id desc limit ?",
                    (limit,),
                ).fetchall()
            records = []
            for row in rows:
                try:
                    item = json.loads(row[0])
                    if isinstance(item, dict):
                        records.append(item)
                except json.JSONDecodeError:
                    continue
            return records, ""
    except Exception as exc:
        return [], str(exc)
    return [], f"Preview does not support {output.suffix or 'this'} output yet."


def filter_records(records: list[dict[str, object]], search: str, status: str) -> list[dict[str, object]]:
    result = records
    if status:
        result = [record for record in result if str(record.get("status", "")) == status]
    if search:
        needle = search.lower()
        result = [
            record for record in result
            if needle in " ".join(
                str(record.get(key, ""))
                for key in ("url", "title", "description", "canonical", "text_preview", "hidden_text", "error", "author", "meta_keywords", "published_time")
            ).lower()
        ]
    return result


def preview_summary(records: list[dict[str, object]]) -> dict[str, object]:
    statuses = sorted({str(record.get("status", "")) for record in records if str(record.get("status", ""))})
    errors = sum(1 for record in records if str(record.get("status", "")).lower() in {"error", "blocked_by_robots"} or record.get("error"))
    api_endpoints = 0
    word_counts = []
    for record in records:
        try:
            word_counts.append(int(record.get("word_count") or 0))
        except (TypeError, ValueError):
            pass
        api = record.get("api_endpoints")
        if isinstance(api, list):
            api_endpoints += len([item for item in api if item])
    avg_words = int(sum(word_counts) / len(word_counts)) if word_counts else 0
    return {"statuses": statuses, "errors": errors, "avg_words": avg_words, "api_endpoints": api_endpoints}


def render_site_map(records: list[dict[str, object]]) -> str:
    if not records:
        return '<p class="muted">No pages captured yet.</p>'
    rows = []
    for record in sorted(records, key=lambda item: (int(item.get("depth") or 0), str(item.get("url") or ""))):
        url = str(record.get("url") or "")
        title = str(record.get("title") or url or "Untitled")
        depth = str(record.get("depth") or 0)
        internal = str(record.get("internal_link_count") or 0)
        external = str(record.get("external_link_count") or 0)
        media = str(len(record.get("media", [])) if isinstance(record.get("media"), list) else 0)
        rows.append(f"""
<tr>
  <td>{html.escape(depth)}</td>
  <td><a href="{html.escape(url)}" target="_blank" rel="noreferrer">{html.escape(title[:120])}</a><div class="muted">{html.escape(url[:200])}</div></td>
  <td>{html.escape(internal)}</td>
  <td>{html.escape(external)}</td>
  <td>{html.escape(media)}</td>
</tr>""")
    return f"""
<table>
  <thead><tr><th>Depth</th><th>Page</th><th>Internal</th><th>External</th><th>Media</th></tr></thead>
  <tbody>{''.join(rows[:200])}</tbody>
</table>"""


def render_crawl_map(records: list[dict[str, object]]) -> str:
    if not records:
        return '<p class="muted">No pages captured yet.</p>'
    depth_counts: dict[int, int] = {}
    sectors: dict[str, list[dict[str, object]]] = {}
    for record in records:
        depth = int(record.get("depth") or 0)
        depth_counts[depth] = depth_counts.get(depth, 0) + 1
        url = str(record.get("url") or "")
        parsed = urlparse(url)
        parts = [part for part in parsed.path.split("/") if part]
        sector = parts[0] if parts else "home"
        if parsed.query:
            sector = f"{sector}?"
        sectors.setdefault(sector, []).append(record)
    depth_html = "".join(
        f'<div class="depth-bar"><span class="muted">Depth {depth}</span><strong>{count}</strong><div class="muted">pages reached at this layer</div></div>'
        for depth, count in sorted(depth_counts.items())
    )
    sector_html = []
    for sector, items in sorted(sectors.items(), key=lambda item: (-len(item[1]), item[0])):
        chips = []
        for record in items[:12]:
            url = str(record.get("url") or "")
            title = str(record.get("title") or url or "Untitled")
            chips.append(
                f'<a class="crawl-pill" href="{html.escape(url)}" target="_blank" rel="noreferrer"><strong>{html.escape(title[:34])}</strong><span>{html.escape(urlparse(url).path[:34] or "/")}</span></a>'
            )
        sector_html.append(
            f'<section class="crawl-sector"><h3>{html.escape(sector)}</h3><div class="muted">{len(items)} page(s) in this area</div><div class="crawl-pills">{"".join(chips)}</div></section>'
        )
    return f"""
<div class="depth-bars">{depth_html}</div>
<div class="crawl-map" style="margin-top:12px">{''.join(sector_html[:18])}</div>"""


def render_collected_data(records: list[dict[str, object]]) -> str:
    if not records:
        return '<p class="muted">No collected data yet.</p>'
    rows = []
    for record in records[:40]:
        url = str(record.get("url") or "")
        title = str(record.get("title") or url or "Untitled")
        status = str(record.get("status") or "")
        words = str(record.get("word_count") or 0)
        media = str(len(record.get("media", [])) if isinstance(record.get("media"), list) else 0)
        api = str(len(record.get("api_endpoints", [])) if isinstance(record.get("api_endpoints"), list) else 0)
        screenshot = str(record.get("screenshot_path") or "")
        rows.append(
            f"""
<tr>
  <td><a href="{html.escape(url)}" target="_blank" rel="noreferrer">{html.escape(title[:110])}</a><div class="muted">{html.escape(url[:180])}</div></td>
  <td class="status-{html.escape(status)}">{html.escape(status)}</td>
  <td>{html.escape(words)}</td>
  <td>{html.escape(media)}</td>
  <td>{html.escape(api)}</td>
  <td>{f'<a href="/image?path={quote(screenshot)}" target="_blank" rel="noreferrer">view</a>' if screenshot else '<span class="muted">none</span>'}</td>
</tr>"""
        )
    return f"""
<table>
  <thead><tr><th>Collected item</th><th>Status</th><th>Words</th><th>Media</th><th>API</th><th>Screenshot</th></tr></thead>
  <tbody>{''.join(rows)}</tbody>
</table>"""


def render_media_index(records: list[dict[str, object]]) -> str:
    items: list[str] = []
    for record in records:
        media = record.get("media")
        if isinstance(media, list):
            for item in media[:25]:
                if isinstance(item, dict):
                    kind = html.escape(str(item.get("kind") or "media"))
                    src = html.escape(str(item.get("src") or "")[:220])
                    items.append(f"<li><strong>{kind}</strong> {src}</li>")
    if not items:
        return '<p class="muted">No media captured yet.</p>'
    return f"<ul class='mini-list'>{''.join(items[:300])}</ul>"


def render_image_gallery(records: list[dict[str, object]]) -> str:
    cards: list[str] = []
    for record in records:
        images = record.get("images")
        if not isinstance(images, list):
            continue
        for image in images[:18]:
            if not isinstance(image, dict):
                continue
            src = str(image.get("src") or image.get("url") or "")
            if not src:
                continue
            alt = str(image.get("alt") or image.get("title") or image.get("kind") or "image")
            cards.append(
                f"""
<figure class="media-card">
  <a href="{html.escape(src)}" target="_blank" rel="noreferrer">
    <img class="media-thumb" loading="lazy" src="{html.escape(src)}" alt="{html.escape(alt[:120])}">
  </a>
  <figcaption class="media-caption">{html.escape(alt[:160])}<br><span class="muted">{html.escape(src[:160])}</span></figcaption>
</figure>"""
            )
    if not cards:
        return '<p class="muted">No image thumbnails captured yet.</p>'
    return f'<div class="media-grid">{"".join(cards[:36])}</div>'


def list_screenshot_paths(limit: int = 6) -> list[Path]:
    folder = APP_DIR / "screenshots"
    if not folder.exists():
        return []
    items = sorted(folder.glob("*.png"), key=lambda path: path.stat().st_mtime, reverse=True)
    return items[:limit]


def render_api_index(records: list[dict[str, object]]) -> str:
    items: list[str] = []
    for record in records:
        api_endpoints = record.get("api_endpoints")
        if isinstance(api_endpoints, list):
            for endpoint in api_endpoints[:30]:
                if endpoint:
                    items.append(f"<li><code>{html.escape(str(endpoint)[:220])}</code></li>")
        api_json = record.get("api_json")
        if api_json is not None:
            items.append(f"<li><strong>json</strong> {html.escape(str(record.get('url') or '')[:220])}</li>")
    if not items:
        return '<p class="muted">No API endpoints captured yet.</p>'
    return f"<ul class='mini-list'>{''.join(items[:250])}</ul>"


def render_tool_strip(runs: list[dict[str, object]], archives: list[Path]) -> str:
    latest_run = runs[0] if runs else None
    latest_output = str(latest_run["output_path"]) if latest_run else ""
    screenshots = list_screenshot_paths()
    screenshot_cards = ""
    if screenshots:
        screenshot_cards = "".join(
            f'<a class="tool-shot" href="/image?path={quote(str(path))}" target="_blank" rel="noreferrer"><img src="/image?path={quote(str(path))}" alt="screenshot"><span>{html.escape(path.name)}</span></a>'
            for path in screenshots
        )
    else:
        screenshot_cards = '<p class="muted">No screenshots saved yet.</p>'
    archive_link = f"/file?run_id={latest_run['id']}&kind=output" if latest_run else "/archives"
    body = f"""
<section class="panel">
  <div class="panel-title"><h2>Cool Tools</h2><span class="eyebrow">Fast actions</span></div>
  <div class="tool-grid">
    <div class="tool-card">
      <h3>Preset Loader</h3>
      <p>Push the crawl into whole-site or owner mode with one click.</p>
      <div class="tool-actions">
        <button type="button" class="secondary" onclick="fillPreset('whole')">Whole-site</button>
        <button type="button" class="secondary" onclick="fillPreset('owner')">Owner mode</button>
      </div>
    </div>
    <div class="tool-card">
      <h3>Browser Tools</h3>
      <p>Turn on the Playwright-style capture settings and browser flow helpers.</p>
      <div class="tool-actions">
        <button type="button" class="secondary" onclick="fillBrowserTools('playwright')">Render JS</button>
        <button type="button" class="secondary" onclick="fillBrowserTools('capture')">Capture</button>
        <button type="button" class="secondary" onclick="fillBrowserTools('login')">Login</button>
      </div>
    </div>
    <div class="tool-card">
      <h3>Preview Jump</h3>
      <p>Open the area map, media gallery, API index, and hidden content view.</p>
      <div class="tool-actions">
        <a class="button" href="/preview">Open Preview</a>
        <a class="button ghost" href="/runs">Runs</a>
      </div>
    </div>
    <div class="tool-card">
      <h3>Latest Output</h3>
      <p>{html.escape(latest_output or 'No run output yet.')}</p>
      <div class="tool-actions">
        <a class="button ghost" href="{archive_link}">Open Output</a>
        <a class="button ghost" href="/archives">Archives</a>
      </div>
    </div>
  </div>
  <div style="margin-top:14px">
    <h3>Recent screenshots</h3>
    <div class="tool-screens">{screenshot_cards}</div>
  </div>
</section>
"""
    return body


def render_hidden_index(records: list[dict[str, object]]) -> str:
    items: list[str] = []
    for record in records:
        hidden = str(record.get("hidden_text") or "")
        if hidden:
            items.append(f"<li>{html.escape(hidden[:220])}</li>")
        comments = record.get("comments")
        if isinstance(comments, list):
            for comment in comments[:10]:
                items.append(f"<li><strong>comment</strong> {html.escape(str(comment)[:220])}</li>")
    if not items:
        return '<p class="muted">No hidden text or comments captured yet.</p>'
    return f"<ul class='mini-list'>{''.join(items[:200])}</ul>"


def render_record_card(record: dict[str, object]) -> str:
    title = str(record.get("title") or record.get("url") or "Untitled")
    url = str(record.get("url") or "")
    status = str(record.get("status") or "")
    content_type = str(record.get("content_type") or "")
    word_count = str(record.get("word_count") or "")
    lang = str(record.get("lang") or "")
    author = str(record.get("author") or "")
    published_time = str(record.get("published_time") or "")
    description = str(record.get("description") or "")
    keywords = str(record.get("meta_keywords") or "")
    text_preview = str(record.get("text_preview") or "")
    headings = record.get("headings")
    heading_text = ""
    if isinstance(headings, list):
        heading_text = ", ".join(
            str(item.get("text", "")) if isinstance(item, dict) else str(item)
            for item in headings[:5]
        )
    links = record.get("links")
    link_count = len(links) if isinstance(links, list) else record.get("link_count", "")
    images = record.get("images")
    image_count = len(images) if isinstance(images, list) else ""
    media = record.get("media")
    media_count = len(media) if isinstance(media, list) else ""
    files = record.get("files")
    files_count = len(files) if isinstance(files, list) else ""
    comments = record.get("comments")
    comments_count = len(comments) if isinstance(comments, list) else ""
    api_endpoints = record.get("api_endpoints")
    api_count = len(api_endpoints) if isinstance(api_endpoints, list) else ""
    screenshot_path = str(record.get("screenshot_path") or "")
    screenshot_img = ""
    if screenshot_path:
        screenshot_img = f'<p><a href="/image?path={quote(screenshot_path)}" target="_blank" rel="noreferrer"><img class="media-thumb" loading="lazy" src="/image?path={quote(screenshot_path)}" alt="screenshot"></a></p>'
    internal_link_count = str(record.get("internal_link_count") or "")
    external_link_count = str(record.get("external_link_count") or "")
    error = str(record.get("error") or "")
    validation_issues = record.get("validation_issues")
    markdown = str(record.get("markdown") or "")
    hidden_text = str(record.get("hidden_text") or "")
    chunks = record.get("content_chunks")
    link_items = ""
    if isinstance(links, list) and links:
        link_items = "<ul class='mini-list'>" + "".join(f"<li>{html.escape(str(link)[:180])}</li>" for link in links[:5]) + "</ul>"
    image_items = ""
    if isinstance(images, list) and images:
        image_items = "<ul class='mini-list'>" + "".join(
            f"<li>{html.escape(str(item.get('src', item))[:180]) if isinstance(item, dict) else html.escape(str(item)[:180])}</li>"
            for item in images[:5]
        ) + "</ul>"
    raw = html.escape(json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True)[:6000])
    return f"""
<article class="record-card">
  <h3>{html.escape(title[:140])}</h3>
  <p><a href="{html.escape(url)}" target="_blank" rel="noreferrer">{html.escape(url[:160])}</a></p>
  <div class="record-meta">
    {badge("status", status)}
    {badge("words", word_count)}
    {badge("links", str(link_count))}
    {badge("internal", internal_link_count)}
    {badge("external", external_link_count)}
    {badge("images", str(image_count))}
    {badge("media", str(media_count))}
    {badge("files", str(files_count))}
    {badge("comments", str(comments_count))}
    {badge("api", str(api_count))}
    {badge("type", content_type[:40])}
  </div>
  {f'<p class="status-error"><strong>Error:</strong> {html.escape(error[:300])}</p>' if error else ''}
  {f'<p><strong>Lang:</strong> {html.escape(lang)}</p>' if lang else ''}
  {f'<p><strong>Author:</strong> {html.escape(author)}</p>' if author else ''}
  {f'<p><strong>Published:</strong> {html.escape(published_time)}</p>' if published_time else ''}
  {f'<p>{html.escape(description[:240])}</p>' if description else ''}
  {f'<p><strong>Keywords:</strong> {html.escape(keywords[:240])}</p>' if keywords else ''}
  {f'<p><strong>Headings:</strong> {html.escape(heading_text[:240])}</p>' if heading_text else ''}
  {f'<p><strong>Validation:</strong> {html.escape("; ".join(validation_issues[:5]))}</p>' if isinstance(validation_issues, list) and validation_issues else ''}
  {f'<p><strong>Hidden:</strong> {html.escape(hidden_text[:240])}</p>' if hidden_text else ''}
  {f'<p><strong>API:</strong> {html.escape(", ".join(str(item) for item in api_endpoints[:5] if item))}</p>' if isinstance(api_endpoints, list) and api_endpoints else ''}
  {f'<p><strong>Screenshot:</strong> <code>{html.escape(screenshot_path[:240])}</code></p>' if screenshot_path else ''}
  {screenshot_img}
  {f'<p class="preview-text">{html.escape(text_preview[:700])}</p>' if text_preview else ''}
  {f'<details class="raw-record"><summary>Markdown</summary><pre>{html.escape(markdown[:6000])}</pre></details>' if markdown else ''}
  {f'<p><strong>Chunks:</strong> {len(chunks) if isinstance(chunks, list) else 0}</p>' if chunks is not None else ''}
  {f'<p><strong>Top links</strong></p>{link_items}' if link_items else ''}
  {f'<p><strong>Images</strong></p>{image_items}' if image_items else ''}
  <details class="raw-record"><summary>Raw record</summary><pre>{raw}</pre></details>
</article>
"""


def badge(label: str, value: str) -> str:
    if not value:
        return ""
    return f'<span class="badge">{html.escape(label)}: {html.escape(value)}</span>'


def safe_app_file(path: Path) -> bool:
    try:
        target = path.expanduser().resolve()
        app_dir = APP_DIR.resolve()
        return target == app_dir or app_dir in target.parents
    except OSError:
        return False


def main() -> int:
    server = ThreadingHTTPServer((HOST, PORT), ProductHandler)
    print(f"Advanced Scraper dashboard: http://{HOST}:{PORT}")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
