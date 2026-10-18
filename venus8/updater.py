"""Windows standalone updater for GitHub releases. No UI calls from worker threads."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import threading
import urllib.request

from . import __version__

REPO = "alexpmr/venus-8"
API = f"https://api.github.com/repos/{REPO}/releases?per_page=15"
AGENT = "Venus-8-Windows-Updater/0.2"

def version_tuple(value):
    m = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", str(value))
    return tuple(map(int, m.groups())) if m else None

def is_newer(candidate, current=__version__):
    a, b = version_tuple(candidate), version_tuple(current)
    return bool(a and b and a > b)

def _request(url):
    return urllib.request.Request(url, headers={"User-Agent": AGENT, "Accept":"application/vnd.github+json"})

def latest_release():
    with urllib.request.urlopen(_request(API), timeout=12) as r:
        data = json.load(r)
    valid = [r for r in data if not r.get("draft") and version_tuple(r.get("tag_name"))]
    return max(valid, key=lambda r: version_tuple(r["tag_name"])) if valid else None

def release_asset(release, portable=False):
    suffix = "-Windows-Portable.exe" if portable else "-Windows-Setup.exe"
    return next((a for a in release.get("assets", []) if a["name"].endswith(suffix)), None)

def download_verified(release, destination, portable=False, progress=None):
    """HTTPS release download with optional SHA256SUMS supplied by same release."""
    asset = release_asset(release, portable)
    if not asset:
        raise RuntimeError("Esta versão não possui instalador Windows compatível.")
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(".partial")
    try:
        with urllib.request.urlopen(_request(asset["browser_download_url"]), timeout=30) as source:
            total = int(source.headers.get("Content-Length", asset.get("size", 0)))
            received = 0
            digest = hashlib.sha256()
            with temporary.open("wb") as output:
                while True:
                    chunk = source.read(256 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
                    digest.update(chunk)
                    received += len(chunk)
                    if progress:
                        progress(received, total)
        if asset.get("size") and received != asset["size"]:
            raise RuntimeError("Download incompleto.")
        if received < 100000:
            raise RuntimeError("Arquivo executável inválido.")
        checksums = next((a for a in release.get("assets", []) if a["name"] == "SHA256SUMS.txt"), None)
        if not checksums:
            raise RuntimeError("Release sem SHA256SUMS.txt. Atualização automática bloqueada por segurança.")
        with urllib.request.urlopen(_request(checksums["browser_download_url"]), timeout=15) as r:
            entries = r.read().decode("utf-8")
        match = re.search(r"(?im)^([0-9a-f]{64})\s+\*?" + re.escape(asset["name"]) + r"\s*$", entries)
        if not match or digest.hexdigest().lower() != match.group(1).lower():
            raise RuntimeError("Falha na verificação SHA-256 do arquivo.")
        temporary.replace(destination)
        return destination
    finally:
        if temporary.exists():
            temporary.unlink()

def start_check(callback):
    def worker():
        try:
            callback(latest_release(), None)
        except Exception as exc:
            callback(None, str(exc))
    threading.Thread(target=worker, daemon=True).start()

def run_installer(path):
    if os.name != "nt":
        raise RuntimeError("Atualizações executáveis somente no Windows.")
    # Launch only; the application should shut down after a successful launch.
    subprocess.Popen([str(path), "/SILENT", "/CLOSEAPPLICATIONS", "/RESTARTAPPLICATIONS"],
                     close_fds=True)

def run_portable(path):
    if os.name != "nt":
        raise RuntimeError("Atualizações executáveis somente no Windows.")
    # Starts the new portable EXE from a versioned directory. The old executable is not overwritten.
    subprocess.Popen([str(path)], close_fds=True)

def is_portable():
    return "portable" in Path(sys.executable).stem.lower()
