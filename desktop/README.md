# Advanced Scraper Desktop

This folder holds the native desktop shell for Advanced Scraper.

What it does:
- starts the local scraper dashboard if needed
- opens it in a native Electron window
- gives you app-style menu actions for Dashboard, Preview, Runs, and Archives

Run it locally after installing dependencies:

```bash
cd /home/007-JB/advanced-scraper/desktop
npm install
npm start
```

Build a distributable package:

```bash
npm run dist
```

Build the bundled backend executable locally:

```bash
cd /home/007-JB/advanced-scraper/desktop
./build-backend.sh
```

This creates `desktop/backend-dist/advanced-scraper-backend`, which the packaged Electron app launches instead of system Python.

For GitHub release publishing, the repo includes `.github/workflows/release-desktop.yml`. Tag a release like `v0.1.0` or `desktop-v0.1.0` and the workflow builds Linux, Windows, and macOS installers, then uploads them to the GitHub release.

The launcher at `/home/007-JB/advanced-scraper/advanced-scraper-app.sh` will use Electron automatically when it is installed, and fall back to the browser/dashboard path otherwise.
