"""Atualiza nomes de assets Windows nos badges do README em cada release.
Os contadores são fornecidos ao vivo pelo shields.io/GitHub Releases.
Uso: python scripts/update_download_badges.py vX.Y.Z
"""
import re
import sys
from pathlib import Path

if len(sys.argv) != 2 or not re.fullmatch(r"v\d+\.\d+\.\d+(?:[-+][A-Za-z0-9.-]+)?", sys.argv[1]):
    raise SystemExit("Uso: python scripts/update_download_badges.py vX.Y.Z")
version = sys.argv[1]
readme = Path("README.md")
text = readme.read_text(encoding="utf-8")
for suffix in ("Windows-Setup.exe", "Windows-Portable.exe"):
    text = re.sub(
        r"Venus-8-v[^/)]+-" + re.escape(suffix),
        "Venus-8-" + version + "-" + suffix,
        text,
    )
readme.write_text(text, encoding="utf-8")
print("Badges atualizados:", version)
