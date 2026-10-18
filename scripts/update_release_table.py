"""Read live GitHub Release assets and update Windows-only README download table."""
import json
import os
import subprocess
from pathlib import Path
from datetime import datetime, timezone

repo=os.environ["GITHUB_REPOSITORY"]
release=json.loads(subprocess.check_output(["gh","api",f"repos/{repo}/releases/tags/v0.1.0"],text=True))
assets={a["name"]:a for a in release["assets"]}
rows=[]
for label,suffix in [("Instalador","Setup"),("Portátil (EXE único)","Portable")]:
    name=f"Venus-8-v0.1.0-Windows-{suffix}.exe"
    if name not in assets:
        raise RuntimeError(f"Release missing asset: {name}")
    asset=assets[name]
    size=asset["size"]/(1024*1024)
    date=asset["created_at"][:10]
    url=asset["browser_download_url"]
    count=asset["download_count"]
    rows.append(f"| Windows 10/11 x64 | {label} | [`{name}`]({url}) | {size:.1f} MB | {date} | {count} |")
path=Path("README.md")
content=path.read_text(encoding="utf-8")
a=content.index("## Downloads")
b=content.index("![VENUS-8",a)
table="""## Downloads — Venus-8 v0.1.0 (Windows)

| Plataforma | Pacote | Download | Tamanho | Data | Downloads |
|---|---|---|---|---|---|
"""+"\n".join(rows)+"""

**Contadores:** registrados pelo GitHub por arquivo, não por instalação; os números da tabela foram apurados na publicação e podem variar. [Consultar contagem atualizada em Releases](https://github.com/"""+repo+"""/releases/tag/v0.1.0).

"""
path.write_text(content[:a]+table+content[b:],encoding="utf-8")
print("README release table updated",datetime.now(timezone.utc).isoformat())
