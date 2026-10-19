# VENUS-8 — Roadmap de desenvolvimento

<p align="center"><img src="docs/venus-8-mockup.png" alt="Venus-8: interface final de referência" width="100%"></p>

**Escopo de plataformas (até nova orientação): somente Windows 10/11 x64, instalador e portátil em `.exe`. Nenhum build macOS/Linux.**

Este arquivo é o **checklist oficial por etapa**. Cada recurso só deve receber `[x]` quando existir no código e passar na validação apropriada. As marcações verdes representam recursos implementados no código; testes de hardware e homologação são etapas independentes.

**Legenda:** `✅` = implementado em nível especificado; `[ ]` = pendente, incompleto ou sem validação suficiente. Não marcar apenas por existir no mockup.

## Diretriz visual — interface hiper-realista

- [ ] Criar sistema de interface **hiper-realista** com elementos nativos e camadas gráficas em alta resolução, sem ampliação de miniaturas.
- [ ] Manter a estética do mockup oficial como referência; permitir novo layout apenas quando um recurso realmente exigir evolução do painel.
- [ ] Renderizar knobs, sliders, botões, chaves, LEDs e teclado como componentes interativos independentes, com movimento e estado visível em tempo real.
- [ ] Suportar diferentes resoluções, dimensionamento Windows e futura operação touchscreen sem perda de nitidez.
- [ ] Preservar compatibilidade de parâmetros, patches, mapeamentos MIDI, configuração e atualização ao evoluir o layout.
- [ ] Elaborar e validar uma prévia visual da nova interface antes de substituir a anterior.
- [ ] Usar ícone próprio de um sintetizador compacto com teclas e knobs no executável, janela, barra de tarefas e atalhos.

**Princípio:** o mockup é uma referência estética; imagens de painel não substituem controles reais. Layout novo é permitido quando tecnicamente justificado e mantém a identidade Venus-8.

## v0.1 — Fundação, interface e Windows

- ✅ Código inicial do aplicativo Windows em Python/Tkinter
- ✅ Interface vintage inicial, redimensionável
- ✅ Teclado virtual com clique do mouse
- ✅ Quatro formas de onda e geração básica de áudio estéreo
- ✅ Polifonia inicial com limite de 16 vozes
- ✅ Seleção básica da saída de áudio
- ✅ Detecção e seleção de entrada MIDI
- ✅ Indicadores superiores de CPU, RAM e vozes
- ✅ Controle Master Volume e botão Panic
- ✅ Salvamento e carregamento simples de patches JSON
- ✅ Arquivos de workflow Windows, PyInstaller e script Inno Setup
- ✅ Compilação do executável Windows 10/11 x64 confirmada para v0.1.0
- ✅ Publicação de instalador Setup e portátil na Release v0.1.0
- [ ] Teste real da instalação, inicialização, áudio e MIDI em Windows 10/11
- [ ] Interface final em tela cheia conforme mockup aprovado
- [ ] Knobs, sliders, switches e display animados/operacionais
- [ ] Áudio configurável: WASAPI/ASIO, sample rate, buffer e latência
- [ ] Motor centralizado de parâmetros com sincronização mouse/MIDI/patch
- [ ] Isolamento robusto do processamento de áudio em tempo real
- [ ] Monitor DSP, latência, underruns, pico e atividade MIDI
- [ ] Logs, diagnóstico e mensagens de falha compreensíveis

## v0.2.10 — Motor de áudio mais leve e limpo

- ✅ Vozes renderizadas em conjunto (matriz voz × amostra): 16 vozes com delay caem de ~44% para ~13% do tempo de cada bloco de áudio (medido em Linux; Windows a homologar).
- ✅ Filtro ladder de 4 polos ~5× mais rápido, com saída idêntica à anterior (saturação não linear preservada no laço).
- ✅ Delay vetorizado por blocos, com saída idêntica à anterior.
- ✅ Antialiasing PolyBLEP em Saw, Pulse e Sub: 16–18 dB menos aliasing em notas agudas. Triangle e Sine sem alteração.
- ✅ LFO calculado amostra a amostra, sem degraus entre blocos; o som não depende mais do tamanho do buffer.
- ✅ Testes de aliasing, independência do tamanho de bloco, delay contra referência e polifonia de 16 vozes.
- [ ] Homologar no Windows real: ausência de estalos com 16 vozes, delay e MIDI.
- [ ] Filtro por voz e envelope de filtro (depende de um filtro compilado ou de outra estratégia de desempenho).

## v0.2.9 — Controles reais e independentes

- ✅ Teclado real de 85 teclas (C1–C8) com padrão correto de piano; cada tecla é um objeto independente que acende somente com mouse ou MIDI.
- ✅ Teclas acesas e padrão irregular de teclas pretas do mockup removidos da arte.
- ✅ Os 12 knobs ativos redesenhados como componentes giratórios com anel de LEDs; ponteiros pintados removidos da arte.
- ✅ Tampas dos 9 faders ativos removidas da arte e redesenhadas como objetos móveis.
- ✅ Atualização incremental: cada controle se atualiza individualmente, sem recriar o painel a cada evento.
- ✅ Testes automatizados de layout do teclado, limpeza da arte, knobs e teclas.
- ✅ Testes executados em todo pull request (workflow `Tests`), sem compilar ou publicar.
- [ ] Homologar aparência e resposta de mouse/MIDI no Windows real (Full HD, 2K e 4K).
- [ ] Botões de forma de onda, LEDs e controles futuros ainda pintados na arte; converter ao implementar cada recurso.

## v0.2.6 — Arte oficial HD e identidade do Windows

- ✅ Mockup original **1600 × 959 PNG sem perda**, armazenado no GitHub como `docs/venus-8-mockup.png`.
- ✅ README e ROADMAP usam o mesmo PNG em largura total.
- ✅ Instalador e portátil incluem o PNG original no executável; miniaturas são rejeitadas.
- ✅ Interface interativa posicionada sobre a arte oficial, mantendo o layout aprovado.
- ✅ Ícone personalizado de sintetizador vintage com teclado, knobs e LEDs, em múltiplas resoluções.
- ✅ Ícone configurado para Windows EXE, instalador e janela/barra de tarefas.
- ✅ Ajuste de DPI por monitor no Windows para reduzir perda de nitidez.
- ✅ Teste automático para validar a resolução da imagem e a geração do ícone.
- [ ] Testar no Windows 10/11 em monitor Full HD, 2K e 4K.
- ✅ Aperfeiçoar elementos dinâmicos sobre a arte: ponteiros, faders e notas efetivamente pressionadas (v0.2.9).
- [ ] Validar produção sonora e atualizador na v0.2.6.

## v0.2.4 — Validação do layout definitivo Windows

- ✅ Layout reestruturado segundo o mockup aprovado: 3 osciladores, mixer, filtro, 3 envelopes, 2 LFOs, display central, matriz, arp, sequenciador, efeitos e master.
- ✅ Teclado inferior proporcional com pitch bend/mod wheel à esquerda.
- ✅ Controles implementados ativos e módulos futuros visíveis/desabilitados.
- ✅ Indicador de atualização com texto de progresso na barra superior.
- ✅ Pitch Bend virtual retorna ao centro ao soltar o mouse.
- ✅ Tabela do README com quantidades **numéricas** reais de downloads por executável, sem badges.
- ✅ Workflow periódico para atualizar contagens por arquivo a cada seis horas.
- [ ] Confirmação de build e publicação dos dois executáveis Windows v0.2.4.
- [ ] Homologação visual, áudio, MIDI e autoupdate no computador Windows do usuário.
- [ ] Aproximação pixel a pixel do mockup final: gradientes, texturas, tipografia e knobs 3D.

## v0.2.2 — Prévia interativa de testes (incremental)

- ✅ Painel vintage de tela inteira, com todas as seções do design em seus lugares.
- ✅ Knobs, sliders e botões gráficos com feedback de mouse.
- ✅ Seções não desenvolvidas presentes em cinza, desabilitadas e identificadas.
- ✅ Três osciladores sonoros com forma de onda, nível e ajuste de afinação individuais.
- ✅ Suboscilador e ruído com controles de nível.
- ✅ Mixer e filtro passa-baixas funcionais (Cutoff).
- ✅ Ataque e Release do amplificador; Decay e Sustain ainda pendentes.
- ✅ LFO 1 com Rate e Depth; LFO 2 pendente.
- ✅ Drive e Delay com Mix, Time e Feedback.
- ✅ Banco local de patches JSON: salvar, abrir e navegar.
- ✅ Entrada MIDI USB, teclado virtual e alterações visuais recebidas por MIDI.
- ✅ Indicador de update e verificação periódica de Releases.
- ✅ Download de atualização com SHA-256 e execução assistida do novo instalador.
- ✅ Portátil: abrir versão nova baixada sem substituir o EXE em uso.
- ✅ Testes unitários de DSP, patches e seleção de atualizações adicionados.
- [ ] Conclusão do GitHub Actions para v0.2.2 verificada.
- [ ] Teste da nova interface e áudio no Windows real.
- [ ] Verificação real da atualização v0.2.2 → versão seguinte.
- [ ] Teste de performance com 16 vozes, áudio ASIO/WASAPI e MIDI físico.
- [ ] Finalizar ADSR completo, antialiasing, resonância e mod matrix.

## v0.2.7 — Banco Factory de timbres vintage

- ✅ Banco Factory **Analog Classics** com 14 timbres originais de inspiração analógica/vintage.
- ✅ Categorias Bass, Lead, Brass, Pad, Keys e FX.
- ✅ Navegador por banco/categoria com prévia da descrição e seleção por duplo clique.
- ✅ Botões anterior/próximo incluem patches Factory e User.
- ✅ Banco Factory somente leitura; salvar versões personalizadas no banco User (JSON).
- ✅ Timbres implementados sobre o DSP, com diferentes parâmetros efetivos de síntese.
- ✅ Envelope ADSR completo: Attack, Decay, Sustain e Release.
- ✅ Filtro passa-baixas ressonante de quatro polos, com comportamento inspirado em ladder analógico.
- ✅ Controles de Resonance, Decay e Sustain habilitados no painel oficial.
- [ ] Validar os novos testes automatizados no GitHub Actions e homologar timbres com áudio/MIDI no Windows real.
- [ ] Modelagem detalhada de circuitos Moog; os timbres atuais são inspirações originais, não emulações oficiais.

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

- ✅ Indicador de atualização/versão na barra superior e download verificado de EXE (prévia v0.2.2).
- ✅ Download HTTPS, SHA-256, progresso e execução do instalador com confirmação (sem substituição em uso no portátil).
- ✅ Exibição inicial de CPU, RAM e número de vozes (sem métricas DSP ainda).
- [ ] Monitor completo DSP, áudio, buffer, latência, picos, underruns e MIDI.
- [ ] Coerência de valores entre MIDI, mouse, touch, preset e automação VST3.
- ✅ README com imagem conceitual e link para página Releases.
- [ ] Release Windows com Setup e Portable realmente testados.
- ✅ Links diretos no README para os instaladores publicados da última Release.
- ✅ Contadores de downloads por arquivo GitHub Releases, sem confundir com instalações.
- [ ] Suporte a outras plataformas: suspenso até autorização explícita.
- [ ] Registrar evidência da implementação e testes para cada checkbox concluído.

## Regra de manutenção

A cada entrega, atualizar este arquivo no **mesmo PR/commit** que implementa os recursos. Não antecipar itens com base em intenção, protótipo visual ou workflow não executado. Reverter a marcação se o recurso regredir. Testes locais, builds CI e homologação em hardware real devem ser distinguidos.
