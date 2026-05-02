# Release Checklist

Use this before shipping a desktop build.

## Build

- [ ] Package the backend executable with `desktop/build-backend.sh`
- [ ] Build the Electron installer with `npm run dist`
- [ ] Confirm the installer includes the backend bundle
- [ ] Confirm the app opens without system Python installed

## Verify

- [ ] Launch the desktop app
- [ ] Confirm the dashboard opens
- [ ] Confirm quick scrape still runs
- [ ] Confirm preview still loads
- [ ] Confirm collected data appears in the preview
- [ ] Confirm archives are created
- [ ] Confirm screenshots and images load

## Release

- [ ] Tag the release, for example `desktop-v0.1.0`
- [ ] Push the tag to GitHub
- [ ] Verify the GitHub Actions release workflow completed
- [ ] Download and test the installer artifact

## Ops

- [ ] Keep the changelog or release notes updated
- [ ] If signing is required, add code-signing certs before public distribution
- [ ] If updates are required, configure the release feed or update channel
