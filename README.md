# VENUS-8 — Virtual Analog Synthesizer

![VENUS-8 — mockup da interface final](docs/venus-8-mockup.jpg)

*Mockup conceitual — a interface da versão 0.1 ainda é um protótipo e não corresponde integralmente à imagem.*

## ⬇️ Download da versão mais recente

**[Baixar a última versão disponível — GitHub Releases](https://github.com/alexpmr/venus-8/releases/latest)**

**Enquanto o instalador não estiver disponível:** [baixar o projeto atual como ZIP](https://github.com/alexpmr/venus-8/archive/refs/heads/main.zip).

> **Windows 10/11 64 bits:** somente haverá instalador para download após a conclusão bem-sucedida do workflow de compilação e publicação.

| Plataforma | Download | Contagem por instalador |
|---|---|---|
| Windows x64 — Setup | [Última versão](https://github.com/alexpmr/venus-8/releases/latest) | ![Downloads Setup](https://img.shields.io/github/downloads/alexpmr/venus-8/latest/Venus-8-v0.1.0-Windows-Setup.exe?label=downloads) |
| Windows x64 — Portable | [Última versão](https://github.com/alexpmr/venus-8/releases/latest) | ![Downloads Portable](https://img.shields.io/github/downloads/alexpmr/venus-8/latest/Venus-8-v0.1.0-Windows-Portable.zip?label=downloads) |
| macOS | Ainda não disponível | — |
| Linux | Ainda não disponível | — |

Os contadores consultam downloads reais dos assets do GitHub Releases: **não** representam usuários únicos nem instalações. Novas plataformas serão exibidas apenas quando houver binários publicados. A versão nominal dos badges deve acompanhar cada lançamento.

### Instalação

1. Abra **[Releases/latest](https://github.com/alexpmr/venus-8/releases/latest)**.
2. Em **Assets**, escolha o instalador Windows Setup, ou o ZIP Portable.
3. No Windows 10/11 x64, execute o Setup ou extraia e abra o executável portátil.

## Primeira versão — v0.1.0

Base funcional: interface vintage inicial, teclado clicável, oscilador com quatro formas de onda, até 16 vozes, MIDI USB, áudio estéreo, controles básicos, patches JSON, monitor de CPU/RAM e botão Panic.

**Não implementados ainda:** VST3, síntese analógica completa, MIDI Learn avançado, multitoque verdadeiro, atualizador interno e reprodução exata do mockup.

## Compilar e testar

```powershell
py -3.11 -m pip install -r requirements.txt
py -3.11 -m unittest discover -s tests -v
py -3.11 run.py
```

O workflow **Build & Release Windows** compila e entrega artefatos em GitHub Actions. Uma tag `v0.1.0` inicia publicação em Releases **se o build concluir sem erros**.

Consulte [ROADMAP.md](ROADMAP.md) para todas as versões planejadas.
