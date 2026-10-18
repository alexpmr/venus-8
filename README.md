# VENUS-8 — Virtual Analog Synthesizer

![VENUS-8 — mockup da interface final](docs/venus-8-mockup.jpg)

## Downloads

Os instaladores oficiais serão disponibilizados em **[GitHub Releases](https://github.com/alexpmr/venus-8/releases)** após a compilação e validação. No momento, não há instalador publicado.

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
