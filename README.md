# VENUS-8 — Virtual Analog Synthesizer

![VENUS-8 — mockup da interface final](docs/venus-8-mockup.jpg)

*Mockup conceitual — a interface da versão 0.1 ainda é um protótipo e não corresponde integralmente à imagem.*

## ⬇️ Downloads — situação atual

**✅ [Baixar o projeto v0.1 em ZIP (código-fonte)](https://github.com/alexpmr/venus-8/archive/refs/heads/main.zip)**

**⚠️ Instalador Windows 10/11: ainda indisponível.** O executável ainda não foi publicado no GitHub Releases. Por isso, o link antigo para `releases/latest` podia levar a uma página inexistente.

| Plataforma | Instalador | Downloads |
|---|---|---|
| Windows 10/11 x64 — Setup | Aguardando compilação e publicação | — |
| Windows 10/11 x64 — Portable | Aguardando compilação e publicação | — |
| macOS | Não implementado | — |
| Linux | Não implementado | — |

Quando a primeira Release for publicada com arquivos válidos, os botões e contadores por instalador serão ativados aqui. **Não há download de executável disponível até lá.** Os contadores futuros serão os downloads registrados pelo GitHub para cada arquivo publicado, não o número de instalações.

**[Consultar andamento dos builds Windows](https://github.com/alexpmr/venus-8/actions/workflows/build-windows.yml)**

### Executar o projeto a partir do código-fonte

É necessário Python 3.11 com dependências instaladas. Veja as instruções de compilação abaixo. O ZIP não é um instalador Windows.

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
