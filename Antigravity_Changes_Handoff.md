# Antigravity Performance + System Cleanup — Change Log / Handoff

Generated: 2026-01-12 22:28:29

## Goal / Context
- Machine was extremely slow (“snail pace”) especially when using **Antigravity**.
- Suspected causes: disk bloat (Docker), duplicate installs (Google/Cloud tools), Google Drive sync overhead, Antigravity agent loop.

## Current System Snapshot
**Memory / swap**
```
hw.memsize: 8589934592
vm.swapusage: total = 6144.00M  used = 4664.50M  free = 1479.50M  (encrypted)
```

**Top memory consumers (RSS)**
```
30536   0.0  6.9 576040 /Applications/Antigravity.app/Contents/Frameworks/Antigravity Helper (Plugin).app/Contents/MacOS/Antigravity Helper (Plugin)
93736   0.0  6.1 508300 /Applications/Antigravity.app/Contents/Frameworks/Antigravity Helper (Renderer).app/Contents/MacOS/Antigravity Helper (Renderer)
28170  82.6  4.6 385908 /Applications/Antigravity.app/Contents/Frameworks/Antigravity Helper (Plugin).app/Contents/MacOS/Antigravity Helper (Plugin)
28225   4.9  1.9 161012 /Applications/Antigravity.app/Contents/Resources/app/extensions/antigravity/bin/language_server_macos_x64
93731   0.4  1.7 142524 /Applications/Antigravity.app/Contents/MacOS/Electron
54359   0.4  1.4 115352 /Applications/Google Chrome.app/Contents/MacOS/Google Chrome
39772   7.6  1.1  89588 /System/Applications/Utilities/Terminal.app/Contents/MacOS/Terminal
30478   0.0  1.1  88440 /Applications/Antigravity.app/Contents/Frameworks/Antigravity Helper (Renderer).app/Contents/MacOS/Antigravity Helper (Renderer)
20106   0.4  0.8  71180 /Applications/Google Chrome.app/Contents/Frameworks/Google Chrome Framework.framework/Versions/143.0.7499.193/Helpers/Google Chrome Helper (Renderer).app/Contents/MacOS/Google Chrome Helper (Renderer)
  262   0.7  0.8  69048 /System/Library/Frameworks/CoreServices.framework/Frameworks/Metadata.framework/Versions/A/Support/mds_stores
28129   0.0  0.8  68904 /Applications/Google Chrome.app/Contents/Frameworks/Google Chrome Framework.framework/Versions/143.0.7499.193/Helpers/Google Chrome Helper (Renderer).app/Contents/MacOS/Google Chrome Helper (Renderer)
30473   0.0  0.8  68844 npm exec @agentai/mcp-server
20059   0.0  0.8  67676 /Applications/Google Chrome.app/Contents/Frameworks/Google Chrome Framework.framework/Versions/143.0.7499.193/Helpers/Google Chrome Helper (Renderer).app/Contents/MacOS/Google Chrome Helper (Renderer)
18286   0.0  0.8  66876 /Applications/Google Chrome.app/Contents/Frameworks/Google Chrome Framework.framework/Versions/143.0.7499.193/Helpers/Google Chrome Helper (Renderer).app/Contents/MacOS/Google Chrome Helper (Renderer)
54437   0.0  0.8  66868 /Applications/Google Chrome.app/Contents/Frameworks/Google Chrome Framework.framework/Versions/143.0.7499.193/Helpers/Google Chrome Helper (Renderer).app/Contents/MacOS/Google Chrome Helper (Renderer)
```

**Key directory sizes**
```
1.9G	~/.antigravity
2.8G	~/.gemini
```

## Changes Made (What / Where / Why / Impact)

### 1) Removed Docker Desktop leftovers (disk + background overhead)
**What**: Deleted user-level Docker Desktop data that was taking large disk and contributing to sluggishness.

**Where**:
- `~/Library/Containers/com.docker.docker`
- `~/Library/Group Containers/group.com.docker`

**Status**:
```
~/Library/Containers/com.docker.docker: REMOVED
~/Library/Group Containers/group.com.docker: REMOVED
```

**Notes / Impact**:
- Frees a large amount of space (previously included huge `Docker.raw`).
- If you need Docker again, reinstall Docker Desktop.

**Leftover helper** (may persist until reboot):
- Process still running: `284 /Library/PrivilegedHelperTools/com.docker.vmnetd`
- File on disk: `com.docker.vmnetd: NOT PRESENT ON DISK`

### 2) Prevented runaway MCP server from pegging CPU
**What**: Stopped and removed auto-start config for `notebooklm-mcp` (was repeatedly running and consuming CPU).

**Where**:
- Removed `notebooklm` + `MCP_DOCKER` entries from:
  - `~/.gemini/settings.json`
  - `~/.gemini/antigravity/mcp_config.json`

**Current MCP server config summary**:
- `~/.gemini/settings.json` mcpServers: `['agentai']`
- `~/.gemini/antigravity/mcp_config.json` mcpServers: `['alloydb-postgres-admin', 'bigquery', 'cloud-sql-postgresql', 'cloud-sql-postgresql-admin', 'cloudrun', 'gcp-vector-db', 'github', 'perplexity-ask', 'puppeteer', 'remote-github', 'sequential-thinking', 'supabase-mcp-server']`

**Impact**:
- Antigravity no longer auto-spawns `npx notebooklm-mcp@latest`.
- If you want it back, restore from backup (see “Backups”) or re-add the MCP server in Antigravity.

### 3) Reduced Antigravity/Gemini background indexing cost
**What**: Added a context exclusion file and tuned settings to reduce indexing / codebase awareness.

**Where**:
- Added: `~/Dev/projects/EventRelay/.aiexclude` (present: True)
- Modified: `~/Dev/projects/EventRelay/.gitignore` (adds `.aiexclude`)

**Repo diff**:
```
.gitignore | 1 +
 1 file changed, 1 insertion(+)
```

**Antigravity settings updated**:
- File: `~/Library/Application Support/Antigravity/User/settings.json`
- `cloudcode.autoDependencies` = `'off'`
- `cloudcode.verboseLogging` = `False`
- `geminicodeassist.contextExclusionFile` = `'.aiexclude'`
- `geminicodeassist.contextExclusionGitignore` = `True`
- `geminicodeassist.localCodebaseAwareness` = `False`
- `geminicodeassist.verboseLogging` = `False`
- `antigravity.searchMaxWorkspaceFileCount` = `1000`

**Impact**:
- Less filesystem watching + less codebase “RAG” workload.
- Particularly important on an 8GB machine to reduce swap pressure.

### 4) Stabilized extension host noise
**What**: Created a missing VSCodeVim registers file that was causing repeated ENOENT errors.

**Where**:
- `~/Library/Application Support/Antigravity/User/globalStorage/vscodevim.vim/.registers`

**Impact**:
- Reduces extension-host churn/log spam.

### 5) Disabled problematic extensions (to reduce freezes)
**What**: Disabled extensions that were contributing to extension host unresponsiveness / errors.

**Where / Which**:
```
19:github.vscode-pull-request-github@0.118.2
23:google.geminicodeassist@2.68.0-insiders.0
24:googlecloudtools.cloudcode@2.39.0-insiders.1
```

**Notes / Impact**:
- `googlecloudtools.cloudcode` was frequently blamed in “UNRESPONSIVE extension host” profiling.
- Disabling it can remove Cloud Code features; re-enable by reinstalling the extension or re-enabling it in Antigravity’s Extensions UI.

### 6) Kept Google Drive disconnected (known slowdown source)
**What**: Google Drive File Provider domain remains temporarily disconnected and Drive is not running.

**Where**:
- File Provider domain: `com.google.drivefs.fpext/gdrive-100819125745700103222`

**Status**:
```
- Google Drive [FPFS] (⏹  temporarily disconnected: Google Drive needs to be running in order to sync these files.)
	com.google.drivefs.fpext/gdrive-100819125745700103222
	<FPFS>/G{24}l.com
 - iCloud Drive (hidden)
	com.apple.CloudDocs.MobileDocumentsFileProvider
	~/L{5}y/M{14}s
Google Drive: not running
```

**Impact**:
- Avoids heavy DriveFS CPU/disk activity.

### 7) Removed leftover Cursor IDE data (Cursor not installed)
**What**: Removed Cursor caches/support files even though `Cursor.app` was not present.

**Where**:
- `~/Library/Application Support/Cursor` (~25M)
- `~/Library/Caches/com.todesktop.230313mzl4w4u92.ShipIt` (~585M)
- plus associated `~/Library/HTTPStorages/...`, prefs, saved state.

**Status**:
```
Cursor leftovers removed
```

### 8) Browser duplicates check (Chromium/Firefox)
**What**: Found multiple cached Chromium/Firefox installs from Playwright/Puppeteer (not “real” apps in /Applications).

**Where**:
- `~/.cache/puppeteer/chrome` (Chromium)
- `~/Library/Caches/ms-playwright` (Chromium + Firefox Nightly + WebKit)

**Sizes**:
```
271M	~/.cache/puppeteer/chrome
1.5G	~/Library/Caches/ms-playwright
```

**Impact**:
- These can be safely deleted if you’re not using Playwright/Puppeteer right now; they will re-download later.

## Backups / Rollback
- `~/.gemini/settings.json.bak-20260112T211110`
- `~/.gemini/settings.json.bak-20260112T214138`
- `~/.gemini/antigravity/mcp_config.json.bak-20260112T211110`
- `~/.gemini/antigravity/mcp_config.json.bak-20260112T214138`
- `~/Library/Application Support/Antigravity/User/globalStorage/state.vscdb.bak-20260112T213149`

Rollback suggestions:
- To revert `.aiexclude` behavior: remove `~/Dev/projects/EventRelay/.aiexclude` and revert `~/Dev/projects/EventRelay/.gitignore`.
- To restore MCP servers: copy the relevant `.bak-*` file back over the active JSON.
- To restore Antigravity auth DB: replace `state.vscdb` with the `.bak-*` copy (only if you understand the risk; this file contains secrets).

## Open Issues / Next Steps
- Antigravity language server still reports auth/timeout issues in logs ("You are not logged into Antigravity" / `deadline_exceeded`).
  - Primary log to inspect: `~/Library/Application Support/Antigravity/logs/*/window*/exthost/google.antigravity/Antigravity.log`
  - This may be related to token refresh, backend connectivity, or extension host health.
- Swap remains high on an 8GB machine; a reboot is the fastest way to clear swap.
- If Cloud Code is required, consider re-enabling `googlecloudtools.cloudcode` after swap pressure is reduced (reboot) and exclusions are in place.

## Security / Secrets
- Treat these as sensitive and **do not paste into chats/logs**:
  - `~/Library/Application Support/Antigravity/User/globalStorage/state.vscdb` (contains `antigravityAuthStatus` with an OAuth access token).
  - `~/.gemini/settings.json` (may contain MCP env vars / API keys).
- Backups were created before risky edits (see “Backups”).
