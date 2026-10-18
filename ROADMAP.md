# VENUS-8 — Roadmap de desenvolvimento

Este arquivo é o **checklist oficial por etapa**. Cada recurso só deve receber `[x]` quando existir no código e passar na validação apropriada. A marcação `[x]` na v0.1 indica **implementação básica identificada no repositório**, não homologação Windows, DSP final ou entrega de Release.

**Legenda:** `[x] ✅` = implementado em nível especificado; `[ ]` = pendente, incompleto ou sem validação suficiente. Não marcar apenas por existir no mockup.

## v0.1 — Fundação, interface e Windows

- [x] ✅ Código inicial do aplicativo Windows em Python/Tkinter
- [x] ✅ Interface vintage inicial, redimensionável
- [x] ✅ Teclado virtual com clique do mouse
- [x] ✅ Quatro formas de onda e geração básica de áudio estéreo
- [x] ✅ Polifonia inicial com limite de 16 vozes
- [x] ✅ Seleção básica da saída de áudio
- [x] ✅ Detecção e seleção de entrada MIDI
- [x] ✅ Indicadores superiores de CPU, RAM e vozes
- [x] ✅ Controle Master Volume e botão Panic
- [x] ✅ Salvamento e carregamento simples de patches JSON
- [x] ✅ Arquivos de workflow Windows, PyInstaller e script Inno Setup
- [ ] Compilação comprovada do executável Windows 10/11 x64
- [ ] Publicação de instalador Setup e portátil em Release
- [ ] Teste real da instalação, inicialização, áudio e MIDI em Windows 10/11
- [ ] Interface final em tela cheia conforme mockup aprovado
- [ ] Knobs, sliders, switches e display animados/operacionais
- [ ] Áudio configurável: WASAPI/ASIO, sample rate, buffer e latência
- [ ] Motor centralizado de parâmetros com sincronização mouse/MIDI/patch
- [ ] Isolamento robusto do processamento de áudio em tempo real
- [ ] Monitor DSP, latência, underruns, pico e atividade MIDI
- [ ] Logs, diagnóstico e mensagens de falha compreensíveis

## v0.2 — Síntese analógica

- [ ] Três VCOs independentes e antialiasing
- [ ] Ondas sine/saw/triangle/square/pulse com PWM
- [ ] Coarse/Fine Tune e ajuste de oitavas por VCO
- [ ] Oscillator Sync, Hard Sync, Ring Mod e FM/Cross Mod
- [ ] Suboscillator e ruído branco/rosa
- [ ] Mixer individual VCO1–3, Sub e Noise
- [ ] Filtros LP/HP/BP/Notch e 12/24 dB/oitava
- [ ] Cutoff, Resonance, Key Tracking, Drive e Envelope Amount com DSP real
- [ ] Modelos de caráter analógico/vintage
- [ ] Amplificador VCA e envelopes ADSR de amplitude, filtro e modulação
- [ ] Curvas de envelope e resposta a Velocity
- [ ] LFO 1/2 com múltiplas ondas, Sample & Hold, Fade e Retrigger
- [ ] Sincronismo dos LFOs por BPM

## v0.3 — Polifonia e performance

- [ ] Modos Mono, Poly, Legato, Unison
- [ ] Unison Detune e Stereo Spread
- [ ] Glide/Portamento: tempo e comportamento
- [ ] Pitch Bend e Mod Wheel operacionais e sincronizados na interface
- [ ] Velocity, Channel Pressure, Poly Aftertouch
- [ ] Voice Allocation/Stealing e prioridades Last/Low/High
- [ ] Key Tracking, Master Tune e transposição
- [ ] Gerenciamento de notas presas, Panic/All Notes Off e consumo por voz

## v0.4 — MIDI USB e MIDI Learn

- [ ] Múltiplas entradas MIDI e seleção de canal
- [ ] MIDI Learn contextual em knobs, sliders, botões e pedais
- [ ] Mapeamento, edição, remoção e indicador visual de associação
- [ ] Sincronização visual e sonora em tempo real para cada parâmetro
- [ ] Teclas e wheels refletindo mensagens externas
- [ ] Suporte ampliado MIDI CC 7/14 bits, NRPN, RPN e Aftertouch
- [ ] MIDI Controller Manager e monitor RX/TX
- [ ] Perfis globais, por dispositivo e por patch
- [ ] Importação/exportação de perfis MIDI
- [ ] Curvas, limites, inversão e Soft Takeover/Pickup
- [ ] Uma fonte controlando múltiplos destinos
- [ ] Feedback bidirecional para LEDs/faders motorizados compatíveis
- [ ] Hot-plug e reconexão com restauração de perfis

## v0.5 — Touchscreen

- [ ] Operação touch em knobs, faders, botões e switches
- [ ] Teclado virtual multitoque com acordes
- [ ] Gestos de knobs configuráveis (vertical/horizontal/circular)
- [ ] Uso simultâneo de teclado, filter cutoff e outros controles
- [ ] Pitch Bend e Mod Wheel por toque
- [ ] Modo Touch UI com controles/áreas maiores
- [ ] Realce visual, valores instantâneos e prevenção de toques acidentais
- [ ] Suporte a monitores externos, DPI e escala Windows
- [ ] Ajuste de sensibilidade e convivência mouse/touch/MIDI

## v0.6 — Bancos e patches

- [ ] Bancos Factory/User com armazenamento persistente
- [ ] Browser, pesquisa, categorias, autor e favoritos
- [ ] Save, Save As, Load, Previous/Next
- [ ] Importação/exportação de patches e bancos completos
- [ ] Histórico, INIT e Random Patch Generator
- [ ] A/B e Undo/Redo
- [ ] Avisos para alterações não salvas e proteção Factory
- [ ] Migração de schema, backup e compatibilidade entre versões
- [ ] Patches demonstrativos Bass/Lead/Pad/Brass/Strings/Keys/FX

## v0.7 — Modulação avançada

- [ ] Modulation Matrix com múltiplas rotas Source/Destination
- [ ] Amount positivo/negativo
- [ ] Destinos Pitch, Cutoff, PWM, Level, Drive e efeitos
- [ ] Velocity, Aftertouch, Mod Wheel e Key Tracking como fontes
- [ ] Macros atribuíveis por patch
- [ ] Exibição visual das rotas de modulação

## v0.8 — Arpeggiator e Step Sequencer

- [ ] Arpeggiator Up/Down/Up-Down/Random e Chord
- [ ] Latch, Hold, Gate, Swing e oitavas
- [ ] Divisões rítmicas e sincronismo BPM/DAW
- [ ] Sequencer 16/32/64 passos
- [ ] Edição de nota, Velocity, Gate, Tie e Rest por passo
- [ ] Transposição, duração, Swing, Play/Stop
- [ ] Automação de parâmetros por passo
- [ ] Salvar sequência no patch e exibir passo ativo

## v0.9 — Efeitos

- [ ] Chorus e Ensemble vintage
- [ ] Phaser e Flanger
- [ ] Stereo Delay, Tape Delay e sincronismo BPM
- [ ] Reverb Room/Hall/Plate
- [ ] Saturation, Soft Distortion, EQ, Stereo Width, Limiter
- [ ] Wet/Dry e bypass individual
- [ ] Ordem de processamento configurável
- [ ] Configuração por patch e controle MIDI/touch
- [ ] Medidores de pico e proteção contra clipping

## v0.10 — Split, Layers e performance

- [ ] Layer de dois timbres, partes Upper/Lower
- [ ] Split e ponto de divisão configurável
- [ ] Volume, transposição e detune independentes
- [ ] Faixas de Velocity e crossfade por layer
- [ ] Zonas e canais MIDI independentes
- [ ] Indicação visual de zonas, enable/disable e memórias de performance

## v0.11 — VST3 e DAWs

- [ ] Plugin VST3 Windows x64 (formato de instrumento)
- [ ] Motor DSP compartilhado com standalone
- [ ] Notas MIDI e automação de parâmetros pela DAW
- [ ] Sincronização de BPM, arp e sequencer
- [ ] Salvar/restaurar estado completo no projeto
- [ ] Múltiplas instâncias e renderização offline
- [ ] UI redimensionável e mapeamento MIDI host/plugin
- [ ] Testes em DAWs e instalador VST3

## v0.12 — Qualidade, testes e entrega

- [ ] Otimizar CPU, DSP, latência e polifonia
- [ ] Parameter smoothing, prevenção de clicks e clipping
- [ ] Testes de MIDI, touch e concorrência de controles
- [ ] Tratamento de troca/falha de áudio e MIDI
- [ ] Logs exportáveis e diagnóstico de performance
- [ ] Manual de usuário, MIDI Learn, áudio e touch
- [ ] Pacote Setup/Portable, hash e validação Windows 10/11
- [ ] Atualização integrada com validação, progresso e rollback seguro
- [ ] Changelog e testes automatizados de regressão
- [ ] Preservação de bancos, patches, preferências e mapas MIDI

## v1.0 — Versão estável

- [ ] Validar critérios de aceite de todos os marcos essenciais
- [ ] Publicar Windows Standalone e VST3 estáveis
- [ ] Disponibilizar biblioteca Factory e documentação
- [ ] Executar testes de instalação, áudio e MIDI em hardware real
- [ ] Publicar Release final com checksums e changelog

## v1.1+ — Evoluções

- [ ] MIDI 2.0 quando suportado
- [ ] MPE e expressividade por nota
- [ ] Wavetable e FM expandida
- [ ] Modelos adicionais de filtros e efeitos vintage
- [ ] Microtuning e importação de escalas
- [ ] Oscilloscope e analisador de espectro
- [ ] Editor visual de envelopes e mod matrix
- [ ] Editor avançado de sequências e morphing A/B
- [ ] Biblioteca online e compartilhamento de timbres
- [ ] Perfis prontos para controladores populares

## Requisitos transversais e publicação

- [ ] Indicador de atualização e número da versão na barra superior; clique inicia atualização integrada.
- [ ] Download autenticado e verificado, indicação de progresso e reinício seguro.
- [x] ✅ Exibição inicial de CPU, RAM e número de vozes (sem métricas DSP ainda).
- [ ] Monitor completo DSP, áudio, buffer, latência, picos, underruns e MIDI.
- [ ] Coerência de valores entre MIDI, mouse, touch, preset e automação VST3.
- [x] ✅ README com imagem conceitual e link para página Releases.
- [ ] Release Windows com Setup e Portable realmente testados.
- [ ] Links diretos para instaladores existentes na versão mais recente.
- [ ] Contadores reais de downloads separados por asset/plataforma, sem confundir com usuários ou instalações.
- [ ] Publicação futura de macOS/Linux, após avaliação de compatibilidade.
- [ ] Registrar evidência da implementação e testes para cada checkbox concluído.

## Regra de manutenção

A cada entrega, atualizar este arquivo no **mesmo PR/commit** que implementa os recursos. Não antecipar itens com base em intenção, protótipo visual ou workflow não executado. Reverter a marcação se o recurso regredir. Testes locais, builds CI e homologação em hardware real devem ser distinguidos.
