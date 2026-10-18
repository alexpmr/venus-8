"""Update README with live asset sizes, dates, links and dynamic download badges."""
import json
import os
from pathlib import Path
import subprocess
import sys

if len(sys.argv)!=2:
    raise SystemExit("usage: update_release_table.py vX.Y.Z")
tag=sys.argv[1]
repo=os.environ["GITHUB_REPOSITORY"]
release=json.loads(subprocess.check_output(["gh","api",f"repos/{repo}/releases/tags/{tag}"],text=True))
assets={a["name"]:a for a in release["assets"]}
rows=[]
for label,suffix in (("Instalador","Setup"),("Portátil (EXE único)","Portable")):
    name=f"Venus-8-{tag}-Windows-{suffix}.exe"
    asset=assets.get(name)
    if not asset:
        raise RuntimeError("Missing release asset "+name)
    size=asset["size"]/(1024*1024)
    date=asset["created_at"][:10]
    url=asset["browser_download_url"]
    badge=f"https://img.shields.io/github/downloads/{repo}/{tag}/{name}?label=downloads"
    rows.append(f"| Windows 10/11 x64 | {label} | [`{name}`]({url}) | {size:.1f} MB | {date} | ![Downloads]({badge}) |")
path=Path("README.md")
readme=path.read_text(encoding="utf-8")
start=readme.index("## Downloads")
end=readme.index("![VENUS-8",start)
header=f"""## Downloads — Venus-8 {tag} (Windows)

| Plataforma | Pacote | Download | Tamanho | Data | Downloads |
|---|---|---|---|---|---|
"""
header += "\n".join(rows) + f"""

**Downloads:** contadores do GitHub Releases por arquivo, não instalações. [Histórico de versões](https://github.com/{repo}/releases).

"""
path.write_text(readme[:start]+header+readme[end:],encoding="utf-8")
print("README updated for",tag)
