#!/usr/bin/env bash
set -euo pipefail
mkdir -p /home/007-JB/.local/bin /home/007-JB/.local/share/applications /home/007-JB/.advanced-scraper/runs
ln -sf /home/007-JB/advanced-scraper/start-advanced-scraper.sh /home/007-JB/.local/bin/advanced-scraper
chmod +x /home/007-JB/advanced-scraper/start-advanced-scraper.sh
chmod +x /home/007-JB/advanced-scraper/advanced-scraper-app.sh
chmod +x /home/007-JB/advanced-scraper/install-local.sh
cp /home/007-JB/advanced-scraper/advanced-scraper.desktop /home/007-JB/.local/share/applications/advanced-scraper.desktop
cp /home/007-JB/advanced-scraper/advanced-scraper.desktop /home/007-JB/Desktop/advanced-scraper.desktop
mkdir -p /home/007-JB/.local/share/icons
ln -sf /home/007-JB/advanced-scraper/advanced-scraper-icon.svg /home/007-JB/.local/share/icons/advanced-scraper-icon.svg
update-desktop-database /home/007-JB/.local/share/applications >/dev/null 2>&1 || true
echo "Installed. Start with: advanced-scraper"
