# Antigravity Perf / Disk Report

Generated: 2026-01-12 22:05:45


## Current resource pressure
```
hw.memsize: 8589934592
vm.swapusage: total = 5120.00M  used = 3506.75M  free = 1613.25M  (encrypted)
20353   1.0  8.8 738824 /Applications/Antigravity.app/Contents/Frameworks/Antigravity Helper (Plugin).app/Contents/MacOS/Antigravity Helper (Plugin)
22411   0.0  6.9 577120 /Applications/Antigravity.app/Contents/Frameworks/Antigravity Helper (Plugin).app/Contents/MacOS/Antigravity Helper (Plugin)
93736  16.8  5.8 487236 /Applications/Antigravity.app/Contents/Frameworks/Antigravity Helper (Renderer).app/Contents/MacOS/Antigravity Helper (Renderer)
20462   7.1  3.0 250764 /Applications/Antigravity.app/Contents/Resources/app/extensions/antigravity/bin/language_server_macos_x64
54359   0.1  1.6 138276 /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
22326   2.6  1.4 120888 npm exec @agentai/mcp-server
93731   4.3  1.3 111696 /Applications/Antigravity.app/Contents/MacOS/Electron
22167   0.0  1.1  95908 /Applications/Antigravity.app/Contents/Frameworks/Antigravity Helper (Plugin).app/Contents/MacOS/Antigravity Helper (Plugin)
20151   0.0  1.1  95220 /Applications/Google Chrome.app/Contents/Frameworks/Google Chrome Framework.framework/Versions/143.0.7499.193/Helpers/Google Chrome Helper (Renderer).app/Contents/MacOS/Google Chrome Helper (Renderer)
54437   0.0  1.1  88240 /Applications/Google Chrome.app/Contents/Frameworks/Google Chrome Framework.framework/Versions/143.0.7499.193/Helpers/Google Chrome Helper (Renderer).app/Contents/MacOS/Google Chrome Helper (Renderer)
20350   0.0  1.0  80232 /Applications/Antigravity.app/Contents/Frameworks/Antigravity Helper (Renderer).app/Contents/MacOS/Antigravity Helper (Renderer)
20106   0.0  0.9  76132 /Applications/Google Chrome.app/Contents/Frameworks/Google Chrome Framework.framework/Versions/143.0.7499.193/Helpers/Google Chrome Helper (Renderer).app/Contents/MacOS/Google Chrome Helper (Renderer)
```

## Disk usage highlights
```
1.4G	~/.antigravity
2.8G	~/.gemini

```

## Duplicate / multiple installs (likely)
```
/usr/local/bin/gcloud
lrwxr-xr-x  1 garvey  admin  72 Feb 17  2025 /usr/local/bin/gcloud -> /usr/local/Caskroom/google-cloud-sdk/510.0.0/google-cloud-sdk/bin/gcloud
1.5G	/usr/local/share/google-cloud-sdk
898M	~/google-cloud-sdk
```

## Browsers (Chrome / Chromium / Firefox)
Top-level apps in `/Applications`:
```
/Applications/Google Chrome.app
```

Cached “browser installs” from automation tools (not normal apps, but they do take space):
```
271M	~/.cache/puppeteer/chrome/mac-1108766/chrome-mac/Chromium.app
305M	~/Library/Caches/ms-playwright/chromium-1187/chrome-mac/Chromium.app
282M	~/Library/Caches/ms-playwright/chromium-1193/chrome-mac/Chromium.app
264M	~/Library/Caches/ms-playwright/firefox-1490/firefox/Nightly.app
```

Notes:
- I did **not** find `/Applications/Chromium.app` or `/Applications/Firefox*.app` installed.
- The cached Playwright/Puppeteer browsers total about **~1.1GB**; safe to delete if you don’t need Playwright/Puppeteer right now (they’ll re-download later).


## Changes made to reduce slowness (summary)
- Removed large Docker Desktop leftovers in `~/Library/Containers/com.docker.docker` and `~/Library/Group Containers/group.com.docker`.
- Added workspace exclusions to reduce indexing via `.aiexclude` in `~/Dev/projects/EventRelay` and referenced it in Antigravity settings.
- Set performance-related settings (Cloud Code auto-deps off; Gemini Code Assist local codebase awareness off; verbose logging off).
- Stopped runaway `notebooklm-mcp` MCP server auto-start and removed its config entries (was pegging CPU).
- Created missing `vscodevim.vim/.registers` file to stop extension host error spam.
- Removed leftover Cursor IDE data (was not installed, but left caches behind).
- Google Drive is currently not running and File Provider domain is disconnected.
