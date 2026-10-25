"""Update README with release sizes, dates, links and numeric download counts."""
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
def badge(key):
    owner,name=repo.split("/",1)
    return f"![downloads](https://img.shields.io/endpoint?url=https%3A%2F%2Fraw.githubusercontent.com%2F{owner}%2F{name}%2Fbadges%2Fdownloads%2F{key}.json)"
for label,suffix in (("Instalador","Setup"),("Portátil (EXE único)","Portable")):
    name=f"Venus-8-{tag}-Windows-{suffix}.exe"
    asset=assets.get(name)
    if not asset:
        raise RuntimeError("Missing release asset "+name)
    size=asset["size"]/(1024*1024)
    date=asset["created_at"][:10]
    url=asset["browser_download_url"]
    count=int(asset["download_count"])
    rows.append(f"| Windows 10/11 x64 | {label} | [`{name}`]({url}) | {size:.1f} MB | {date} | {count} | {badge(suffix.lower())} |")
path=Path("README.md")
readme=path.read_text(encoding="utf-8")
start=readme.index("## Downloads")
end=readme.index("![VENUS-8",start)
header=f"""## Downloads — Venus-8 {tag} (Windows)

| Plataforma | Pacote | Download | Tamanho | Data | Downloads da versão | Todas as versões |
|---|---|---|---|---|---|---|
"""
header += "\n".join(rows) + f"""

**Total (todas as versões):** {badge("total")}

**Downloads:** quantidade de downloads por arquivo desta versão no GitHub Releases; "Todas as versões" soma as versões já publicadas (atualizada a cada hora) (não representa instalações ou usuários únicos). Atualização periódica da tabela. [Histórico de versões](https://github.com/{repo}/releases).

"""
path.write_text(readme[:start]+header+readme[end:],encoding="utf-8")
print("README updated for",tag)
