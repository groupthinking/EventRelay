import os
import re
import json
import time
import hashlib
import logging
import asyncio
import subprocess
import httpx
import shutil
from pathlib import Path
from fastapi import FastAPI, Query, Request, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Dict, Any, List, Optional
from datetime import datetime

# --- App and Logging Setup ---
app = FastAPI(title="Codebase Monitoring & Management Server")
logger = logging.getLogger("proxy")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("[%(levelname)s] [%(name)s] %(message)s"))
if not logger.handlers:
    logger.addHandler(handler)

# --- Global State and Config ---
BASE_DIR = Path(__file__).resolve().parent
REQ_FILE = BASE_DIR / "requirements.txt"  # legacy stub; installs now use pyproject extras
BACKUP_DIR = BASE_DIR / "requirements_backups"
BACKUP_DIR.mkdir(exist_ok=True)
MAX_BACKUPS = 5

alerts_config: Dict[str, Any] = {"webhook_url": None, "filters": None, "dedup_seconds": 0}
last_sent: Dict[tuple, float] = {}

# --- Helper Functions ---
def run_cmd(cmd: List[str]) -> str:
    try:
        return subprocess.check_output(cmd, text=True, cwd=BASE_DIR).strip()
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Command failed: {e.output}")

def parse_deps(lines: List[str]) -> Dict[str, str]:
    deps = {}
    for line in lines:
        if "==" in line:
            pkg, ver = line.split("==", 1)
            deps[pkg.lower()] = ver
    return deps

async def push_alert(signal: Dict[str, Any]):
    if not alerts_config.get("webhook_url"): return
    signal_type = signal.get("type")
    if alerts_config.get("filters") and signal_type not in alerts_config["filters"]: return

    details_hash = hashlib.sha256(json.dumps(signal.get("details", {}), sort_keys=True).encode()).hexdigest()
    key = (signal_type, details_hash)
    now = time.time()
    dedup_window = alerts_config.get("dedup_seconds", 0)

    if key in last_sent and now - last_sent[key] < dedup_window:
        logger.info(f"Suppressed duplicate signal: {signal_type}")
        return

    try:
        async with httpx.AsyncClient() as client:
            await client.post(alerts_config["webhook_url"], json=signal, timeout=5)
        logger.info(f"Sent alert for {signal_type}")
        last_sent[key] = now
    except Exception as e:
        logger.error(f"Failed to send alert: {e}")

# --- Core Logic Functions ---
def diff_requirements() -> dict:
    if not REQ_FILE.exists(): return {}
    wanted = parse_deps(REQ_FILE.read_text().splitlines())
    frozen = parse_deps(run_cmd(["pip", "freeze"]).splitlines())
    
    added = {k: v for k, v in frozen.items() if k not in wanted}
    removed = {k: v for k, v in wanted.items() if k not in frozen}
    changed = {k: {"wanted": wanted[k], "actual": frozen[k]} for k in wanted.keys() & frozen.keys() if wanted[k] != frozen[k]}
    return {"added": added, "removed": removed, "changed": changed}

# --- Endpoints ---
@app.get("/status")
async def status():
    return {"alive": True, "base_dir": str(BASE_DIR)}

@app.get("/list")
async def list_files():
    files = []
    for path in BASE_DIR.rglob("*"):
        if path.is_file():
            try:
                stat = path.stat()
                files.append({
                    "path": str(path.relative_to(BASE_DIR)),
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                })
            except Exception:
                continue
    return files

@app.get("/file")
async def read_file(path: str):
    file_path = BASE_DIR.joinpath(path)
    if not file_path.is_file() or not str(file_path.resolve()).startswith(str(BASE_DIR.resolve())):
        raise HTTPException(status_code=404, detail="File not found or access denied")
    return {"path": path, "content": file_path.read_text(errors="ignore")}

@app.post("/alerts/config")
async def configure_alerts(config: Dict[str, Any]):
    alerts_config.update(config)
    last_sent.clear()
    logger.info(f"Alerts configured: {config}")
    return {"configured": True, "config": alerts_config}

@app.get("/signals")
async def get_signals():
    drift = diff_requirements()
    signals = []
    if any(drift.values()):
        signals.append({"type": "dependency_drift", "details": drift})
    # Add other signal scans here
    return signals

@app.post("/dependencies/sync")
async def sync_deps():
    timestamp = datetime.utcnow().strftime("%Y-%m-%dT%H%M%S")
    backup_file = BACKUP_DIR / f"requirements.{timestamp}.txt"
    if REQ_FILE.exists():
        shutil.copy2(REQ_FILE, backup_file)
    REQ_FILE.write_text(run_cmd(["pip", "freeze"]) + "\n")
    
    signal = {"type": "dependency_drift", "details": diff_requirements()}
    await push_alert(signal)
    return {"status": "synced", "backup_created": str(backup_file)}

@app.get("/dependencies/backups")
async def list_backups():
    backups = sorted(BACKUP_DIR.glob("*.txt"), key=os.path.getmtime, reverse=True)
    return [{"file": b.name, "timestamp": b.stem.split('.')[-1]} for b in backups[:MAX_BACKUPS]]

@app.post("/dependencies/restore/{timestamp}")
async def restore_deps(timestamp: str):
    backup_file = BACKUP_DIR / f"requirements.{timestamp}.txt"
    if not backup_file.exists():
        raise HTTPException(status_code=404, detail="Backup not found")
    shutil.copy2(backup_file, REQ_FILE)
    logger.info(f"Restored requirements.txt from {backup_file.name}")
    return {"restored": backup_file.name}

@app.post("/api/analyze")
async def analyze_video(request: Request):
    data = await request.json()
    video_url = data.get("videoUrl")
    if not video_url:
        raise HTTPException(status_code=400, detail="videoUrl is required")
    # Mock analysis
    await asyncio.sleep(2)
    return {"analysis": f"Analysis of {video_url} is complete."}

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    # Mock upload
    await asyncio.sleep(2)
    return {"message": f"File '{file.filename}' uploaded successfully."}

# --- Startup Hook ---
@app.on_event("startup")
async def startup_check():
    logger.info("Server starting up...")
    drift = diff_requirements()
    if any(drift.values()):
        signal = {"type": "dependency_drift", "details": drift}
        logger.warning(f"Drift detected at startup: {json.dumps(signal)}")
        await push_alert(signal)
    else:
        logger.info("No dependency drift detected at startup.")
