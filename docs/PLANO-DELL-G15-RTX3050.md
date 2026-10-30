# Implementação Windows para RTX 3050 Laptop — plano revisado

> Revisão 2 — 29/10/2026. Substitui a sequência P0–P8 anterior.
> Para o agente executor: executar por tarefa usando a skill executing-plans, quando disponível. Registrar os itens com caixas de seleção; não transformar etapas de pesquisa em suporte confirmado.

**Objetivo:** implementar neste repositório uma adaptação experimental para o Windows do Dell G15 5530 com RTX 3050 Laptop 6 GB e demonstrar ganho útil, correto e reproduzível em trabalho local.

**Arquitetura:** reutilizar o port UEFI Windows em uma árvore versionada `windows/port/`, fixada por commit, acrescentando suporte restrito a este Dell. PowerShell cuida do inventário e da execução dos ensaios; C/UEFI cuida da etapa anterior ao driver Windows; CUDA/cuBLAS mede o efeito Tensor. Não criar driver Windows novo, serviço residente ou interface gráfica nesta primeira versão.

**Tecnologias:** Windows PowerShell 5.1, Python 3.10+, C/UEFI, LLVM/LLD, MSVC e headers EDK2 do port; CUDA/cuBLAS apenas no ambiente isolado de benchmark.

**Definição de sucesso:** Windows inicia com vídeo e driver funcionais, o caminho experimental produz efeito Tensor verificável, pelo menos um fluxo prioritário ganha desempenho sem perder qualidade, e recuperação/ciclo de vida são demonstrados. Build, teste simulado e mensagem “unlocked” não encerram o projeto.

## 1. Correções de direção

1. **Windows é o único alvo de implementação deste plano.** A receita Linux existente fica como referência técnica; não é pré-requisito, entrega substituta ou etapa de instalação.
2. Medir o Windows original **antes** de preparar qualquer ensaio UEFI. O plano anterior colocou o benchmark tarde demais.
3. O port não se resolve acrescentando `25EC` a uma lista. Há quatro trabalhos independentes: GA107/firmware, energia PCI, topologia híbrida Intel/NVIDIA e passagem para o Windows sem reset que desfaça o efeito.
4. Separar o experimento do unlock dos ajustes de aplicativos. Usar A = original, C = aplicativo otimizado sem unlock e B = mesma configuração de aplicativo com unlock. Comparar C com A para configuração; comparar B com C para desbloqueio. Nunca atribuir B/A inteiro ao firmware.
5. O plano entrega artefatos no repositório indicado pelo usuário. Não deixar o port modificado somente num clone externo.
6. Codex, Claude Code e Antigravity entram na validação somente quando acionarem inferência ou processamento **local**. Tempo de resposta de modelos remotos não será métrica da RTX 3050.
7. Não prometer percentual de ganho antecipadamente. Metas abaixo são critérios propostos de aceitação, não previsões.

## 2. Evidência e estado real

### Máquina identificada na etapa anterior

Estes valores vieram da coleta anterior desta conversa; não foram coletados novamente nesta revisão. Revalidar em W1 antes de executar no hardware.

| Campo | Valor registrado |
|---|---|
| Notebook / BIOS | Dell G15 5530 / 1.34.0 |
| GPU / VRAM reportada | RTX 3050 6GB Laptop / 6144 MiB |
| PCI | VEN 10DE; DEV 25EC; subsistema vendor 1028, device 0BF8; revisão A1 |
| VBIOS | 94.07.82.40.2f |
| Windows / driver NVIDIA | Windows 11 Home build 26200 / 610.88 |
| CPU / RAM | i5-13450HX / 16 GiB (2 × 8 GiB) |
| Outra GPU | Intel UHD presente no Windows; GOP UEFI desconhecido |
| Potência reportada | padrão 80 W; máximo 95 W; não aumentar |
| Secure Boot / criptografia | desconhecidos; consultas anteriores sem elevação negadas |
| Pressão de memória anterior | cerca de 0,8–1 GiB disponível; fotografia histórica, não estado atual |

Somente um smoke test de um frame H.264/HEVC NVENC passou no Windows. Não houve unlock, boot experimental nem medição de ganho. O teste de seleção Linux passou em host; não é validação Windows.

### Fontes verificadas nesta revisão

- Fork de destino: [theobarros22/gpu-unlock](https://github.com/theobarros22/gpu-unlock), [PR 1](https://github.com/theobarros22/gpu-unlock/pull/1). Antes desta revisão, head `bfba5053cd90b302a71bdfff22995f432694db22`.
- Linux de referência: [7eb51bcc](https://github.com/Zagitta/gpu-unlock/commit/7eb51bccae0a0b7e599e084d971170e9a1e82d0c).
- Windows de referência atualizado: [263741419ece69bcce73162ad5e98a742db8c6b5](https://github.com/impacifist/Windows-GPU-UNLOCK/commit/263741419ece69bcce73162ad5e98a742db8c6b5), substituindo a referência anterior 23cc0285. A atualização corrige fixtures de atributos PCI e hash PROM por perfil. Não comprova suporte Dell.
- [gpu-family.h](https://github.com/impacifist/Windows-GPU-UNLOCK/blob/263741419ece69bcce73162ad5e98a742db8c6b5/internal-boot/unlock/gpu-family.h) contém GA102/GA104/GA106, não GA107.
- [proven.json](https://github.com/impacifist/Windows-GPU-UNLOCK/blob/263741419ece69bcce73162ad5e98a742db8c6b5/research/profile/proven.json) não inclui 25EC. O gerador LOCAL recusa fora desse conjunto.
- [NEW-MACHINE](https://github.com/impacifist/Windows-GPU-UNLOCK/blob/263741419ece69bcce73162ad5e98a742db8c6b5/docs/NEW-MACHINE.en.md): evidência LOCAL exige **22** resultados de host na revisão atual; o documento anterior citava 21. Isso não equivale a 22 testes novos nossos.
- [build-probe.ps1](https://github.com/impacifist/Windows-GPU-UNLOCK/blob/263741419ece69bcce73162ad5e98a742db8c6b5/research/profile/build-probe.ps1) compila diagnóstico e gera arquivos locais, mas exige GUID real da ESP Windows. Não deve ser executado com GUID fictício como se fosse diagnóstico completo.
- [run-benchmark.ps1](https://github.com/impacifist/Windows-GPU-UNLOCK/blob/263741419ece69bcce73162ad5e98a742db8c6b5/benchmark/run-benchmark.ps1) aceita 3090/3090ti/3070ti, fixa nome/BDF e versões CUDA/cuBLAS. Precisa adaptação específica, não somente execução na 3050.

O [relato Linux do Dell](https://github.com/Zagitta/gpu-unlock/issues/111#issuecomment-6471857518) é referência histórica da investigação anterior: mesmo DEV/subsistema, mas outro VBIOS e outro sistema. Não usar seus percentuais como estimativa Windows. Não transportar valores de registro desse relato para o firmware local.

## 3. Hipóteses a provar e decisões que dependem delas

| Questão | Prova necessária | Se falhar |
|---|---|---|
| GA107 tem layout e firmware compatíveis com a transação? | Mapeamento de fonte e parser, leituras delimitadas, PROM local e replay da transação | Não gerar EFI com escrita; documentar divergência concreta |
| A GPU está acessível e no estado inicial exigido no pré-boot? | PCI/D0/FLR/BAR/atributos em duas capturas independentes | Não forçar D3→D0 ou BME para “fazer funcionar”; abrir tarefa de energia separada |
| Quem dirige a tela interna no UEFI? | Ancestralidade GOP/ConOut/protocolos, não lista de adaptadores do Windows | Projetar a rota constatada, sem escolher perfil AMD/NVIDIA arbitrário |
| É possível liberar somente a NVIDIA e manter o console independente? | Grafo completo antes/depois e replay de ownership | Se não houver independência demonstrada, avaliar headless com logs; caso contrário, bloqueio |
| O handoff Dell preserva o efeito? | Boot único sem reset intermediário, driver recuperado e benchmark Tensor | Port não validado mesmo que a transação tenha terminado |
| O ganho dura durante o trabalho real? | Testes após idle, retomada e execução longa, com controles | Classificar como experimental por sessão ou reprovado para uso diário |
| O fluxo prioritário é limitado por Tensor? | Perfil de carga e comparação controlada | Tratar RAM/VRAM, transferência e configuração; não insistir em GEMM como proxy |

Há um ciclo a evitar: não exigir “hardware já provado” para criar o primeiro experimento e tampouco falsificar a lista de hardware provado para viabilizá-lo. W5/W6 definem uma rota **de pesquisa separada**, restrita à captura local, com as mesmas verificações de transação. Só W9 pode promover o resultado como evidência de hardware.

## 4. Organização no repositório

Preservar a raiz Linux. Importar uma fotografia do código-fonte Windows fixado em `windows/port/`, incluindo licenças, avisos e dependências de fonte necessárias. Não criar outro repositório obrigatório para o usuário nem copiar binários/firmwares privados.

| Caminho proposto | Responsabilidade |
|---|---|
| `windows/UPSTREAM.md` | URL, commit fixado, licença/avisos preservados e lista de alterações locais |
| `windows/port/` | Port upstream versionado; manter caminhos internos para reaproveitar scripts |
| `windows/Collect-Diagnostics.ps1` | Inventário Windows de leitura e razões de indisponibilidade |
| `windows/Run-Workload.ps1` | Execução isolada, captura de saída/telemetria e confirmação de conclusão |
| `windows/Compare-Runs.py` | Comparação offline com recusa de ambientes diferentes e dados incompletos |
| `windows/tests/test_diagnostics.ps1` | Contrato de inventário, redação e erros usando fixtures |
| `windows/tests/test_compare_runs.py` | Cálculo, sentido de ganho, qualidade, ruído e proveniência |
| `windows/tests/test_runner.ps1` | Argumentos, timeout, erro e diretório de resultados; processo falso, sem GPU |
| `windows/workloads/` | Configurações dos casos realmente escolhidos, sem mídia/modelo pessoal |
| `.github/workflows/windows-host.yml` | Testes Windows sem GPU, firmware privado, EFI ou boot |
| `docs/RESULTADOS-WINDOWS-RTX3050.md` | Relatório sanitizado, só ao existir evidência |
| `windows/local/` | Capturas, logs, PROM e resultados privados; ignorado pelo Git |

Também ignorar os caminhos privados do port importado, especialmente `research/profile/local/`, `profile-local.h`, `platform-config.h`, assets e outputs de build. Não confundir dados para uso privado com fixtures sintéticas publicáveis.

## 5. Sequência e marcos

`W0 → W1 → W2 → W3 → W4 → W5 → W6 → W7 → W8 → W9`

W2 estabelece a referência antes do hardware. W3 pode preparar testes/probe enquanto W2 aguarda uma janela de medição. W4 e W8 envolvem o computador real e exigem agendamento e autorização para as ações exatas. Um bloqueio físico não impede escrever/testar código de host que não dependa da captura ausente.

| Marco | Entrega verificável |
|---|---|
| M0 — W0/W1 | Fontes Windows no fork e diagnóstico utilizável |
| M1 — W2 | Benchmark compatível com a 3050 e baseline Windows válido |
| M2 — W3/W4 | Probe não destrutivo e capturas suficientes para decidir a rota |
| M3 — W5/W6/W7 | Port GA107/Dell testado em host e pacote de pesquisa rastreável |
| M4 — W8 | Uma sessão Windows experimental com recuperação e ganho avaliado |
| M5 — W9 | Resultado repetido, limitações e entrega final classificada |

Não fornecer prazo fechado para M3–M5 antes de M2. Topologia e firmware desconhecidos podem exigir pesquisa que não é estimável por contagem de arquivos.

### W0 — Preparar a base Windows no fork

**Modificar/criar:** `windows/port/`, `windows/UPSTREAM.md`, `.gitignore`, `.github/workflows/windows-host.yml`.

- [x] Inspecionar branch, diff e PR. O checkout da sessão anterior tem alterações locais equivalentes a commits feitos via API; não resetar nem sobrescrever.
- [x] Criar branch Windows a partir do estado remoto verificado, preservando o PR existente. O próximo PR de implementação deve ter Windows no título e escopo; a revisão documental pode continuar no PR 1.
- [x] Importar a árvore de fontes do commit Windows fixado, sem reescrever seus caminhos internos. Auditar LICENSE, LICENSES e THIRD_PARTY_NOTICES e preservá-los.
- [x] Registrar versões/localização de Python, MSVC, clang e lld-link. Instalar somente componente ausente em ambiente local acordado; não trocar driver ou CUDA de aplicativos existentes.
- [x] Executar regressões sem captura, a partir de `windows/port/`:

~~~powershell
rtk proxy python -I research/profile/test_family_admission.py
rtk proxy python -I research/profile/test_local_topology.py
rtk proxy python -I research/profile/test_probe_records.py
rtk proxy python -I research/profile/test_compatibility.py
~~~

- [x] Preservar stdout, stderr, exit code e versão. Dependência ausente é BLOQUEADO, não PASSOU. Configurar CI Windows com os mesmos testes que passaram localmente; não acrescentar testes dependentes de ativos privados à CI pública.
- [x] Fazer commit da importação separado dos patches Dell.

**Aceite:** fontes rastreáveis e testes de host reproduzíveis. Nada é inicializado na GPU.

### W1 — Diagnóstico Windows que permita escolher o trabalho

**Criar:** `windows/Collect-Diagnostics.ps1` e `windows/tests/test_diagnostics.ps1`.

**Interface nova proposta:** `-OutputDirectory <diretório novo>`; sem modo “apply”. Gravar `inventory.json`, com `schema_version=1`, timestamp UTC, versões, GPU/PCI, BIOS/VBIOS, RAM disponível/comprometida, estado de energia e lista de lacunas. Campos sem acesso usam `null` e uma razão, nunca “desativado”.

- [x] Começar com testes para ferramenta ausente, acesso negado, duas GPUs NVIDIA, campo N/A e redação de serial/UUID/usuário/caminhos pessoais.
- [x] Usar consultas como estas, selecionando somente campos necessários:

~~~powershell
rtk proxy nvidia-smi --query-gpu=name,pci.bus_id,pci.device_id,driver_version,vbios_version,memory.total,memory.used,temperature.gpu,power.limit --format=csv
rtk proxy powershell -NoProfile -Command "Get-CimInstance Win32_BIOS | Select-Object SMBIOSBIOSVersion"
rtk proxy powershell -NoProfile -Command "Get-CimInstance Win32_OperatingSystem | Select-Object BuildNumber,TotalVisibleMemorySize,FreePhysicalMemory"
rtk proxy powershell -NoProfile -Command "Get-CimInstance Win32_VideoController | Select-Object Name,PNPDeviceID,DriverVersion"
~~~

- [x] Coletar Secure Boot/criptografia com captura explícita de erro; não elevar automaticamente, não coletar chaves. Identidade PNP detalhada fica privada até sanitização.
- [x] Inventariar versões dos runtimes já usados por Whisper, ComfyUI e Ollama, sem importações que baixem modelos ou executem cargas.
- [x] Executar o coletor real, conferir JSON e produzir uma lista de fatos, hipóteses e dados faltantes.
- [x] Anexar ao relatório apenas a versão sanitizada; testar que nenhum serial/chave é incluído.

**Aceite:** diagnóstico repetível que não muda configuração, instala pacote ou inicia modelo. Pressão de RAM é registrada como possível confundidor, não resolvida encerrando processos.

### W2 — Baseline e benchmark próprios da RTX 3050 no Windows

**Modificar no port:** `benchmark/build.ps1`, `run-benchmark.ps1`, `test-runner.ps1`.
**Criar no port:** `benchmark/compute-benchmark-3050.cu`, reutilizando o núcleo existente e as verificações de referência.
**Criar no fork:** runner, comparador e testes listados na seção 4.

- [x] Testar primeiro seleção explícita da 3050, GPU errada, índice/BDF divergente, executável alterado, execução incompleta e dados sem referência numérica.
- [x] Adicionar variante 3050 ao runner e ao manifesto. Selecionar por identidade confirmada, não pelo BDF fixo `01:00.0` de outra máquina.
- [x] Inspecionar as exigências CUDA/cuBLAS existentes. Preservá-las no primeiro build se disponíveis; se mudar a versão, versionar o protocolo de benchmark e impedir comparação entre protocolos diferentes.
- [x] Rodar preflight sem GEMM. Só depois executar carga numa janela adequada, sem interromper tarefas ativas.
- [x] Medir quatro modos: FP32 de controle, FP16 e BF16 com acumulação FP32, TF32. Manter checagem numérica existente, rejeitar NaN/Inf e justificar qualquer mudança de tolerância. Se um modo não puder executar, registrar indisponível.
- [x] Garantir sincronização CUDA antes de encerrar cada tempo. Registrar tamanho de matriz, algoritmo/modo, versão das bibliotecas e aquecimento. Ajustar tamanho à VRAM livre uma vez e congelá-lo para todos os estados.
- [x] Priorizar **faster-whisper e ComfyUI**, pois há caminhos locais Tensor a investigar; executar os dois quando instalados e houver fixture autorizada. Ollama e vídeo entram como avaliação complementar, não condição para começar.
- [x] Para Whisper: mesmo áudio autorizado, modelo/hash, backend, precisão, batch, idioma e parâmetros; registrar RTF, segundos e transcrição. Para ComfyUI: mesmo modelo/hash, workflow, seed, sampler, passos, resolução e batch=1; registrar tempo aquecido e tempo total.
- [x] Para Ollama: congelar modelo/quantização/contexto/prompt, separar carregamento, prefill e decode, registrar distribuição CPU/GPU e memória. Não prometer ganho em decode quantizado.
- [x] Para FFmpeg/editor: selecionar um projeto pequeno reproduzível. Separar exportação sem efeitos (controle NVENC) de efeito/IA que efetivamente use GPU. Validar vídeo decodificável, duração, frames e áudio; congelar qualidade.
- [x] Criar estados A e, somente se houver mudança fundamentada de aplicativo, C. Uma mudança por vez; registrar original e reversão. Congelar C antes do ensaio B.
- [x] Fazer commit dos executores/testes; salvar baseline bruto localmente.

**Contrato proposto de execução:** `Run-Workload.ps1 -CaseFile <JSON> -State A|C|B -OutputDirectory <novo>`. O JSON contém executável e array de argumentos; executar sem `Invoke-Expression`, registrar hashes e nunca aceitar comandos vindos de logs. Timeout encerra somente o processo/filhos iniciados pelo runner. Arquivo `complete.json` só é escrito depois de exit code zero, resultado parseável e validação de qualidade aprovada.

**Contrato de comparação:** `Compare-Runs.py --baseline <pasta> --candidate <pasta> --restored <pasta> --output <arquivo novo>`. Recusar ausência de marcador completo, ambiente/workload/hash/protocolo divergentes, número insuficiente de repetições ou qualidade não aprovada.

Exemplos de assertions para o teste offline do comparador; implementar as funções no comparador e importá-las no teste:

~~~python
assert round(time_reduction_pct(100.0, 80.0), 1) == 20.0
assert round(throughput_gain_pct(100.0, 125.0), 1) == 25.0
assert time_reduction_pct(100.0, 110.0) < 0
assert not comparable({"protocol": 1}, {"protocol": 2})
assert not completed({"exit_code": 1, "quality_pass": True})
~~~

`time_reduction_pct(a,b)=100*(1-b/a)`; `throughput_gain_pct(a,b)=100*(b/a-1)`. As funções recusam zero, valores negativos e não finitos. `comparable` exige todos os campos de contexto definidos em W2; `completed` exige marcador, arquivos íntegros, saída válida e qualidade, não apenas os dois campos do exemplo.

**Aceite:** baseline válido e ferramentas capazes de detectar “sem ganho”. Ausência de modelo/mídia não autoriza download grande ou uso de arquivo pessoal arbitrário.

### W3 — Probe GA107 de observação e decisão de topologia

**Modificar no port:** `internal-boot/boot/probe.c`, `test_probe_generic.c`, `research/profile/build-probe.ps1` e testes de build/records.
**Criar:** `docs/windows/DECISOES-DELL.md`, registrando decisões com evidência.

- [x] Primeiro reproduzir o comportamento atual: 25EC inventariado, sem leitura profunda autorizada. Testar contadores de zero escrita PCI/MMIO, DMA, FLR e detach.
- [x] Separar inventário básico de leitura profunda. O primeiro pode coletar PCI/protocolos/GOP sem admitir a GPU à transação.
- [x] Auditar a janela de leitura GA107 por fontes e limites antes de habilitar MMIO/PROM; leitura MMIO não é automaticamente inofensiva. Não deduzir endereço/limite só do nome Ampere.
- [x] Cobrir no teste GPU duplicada, BAR inválido, energia desconhecida/D3, mudança de identidade, grafo incompleto e falha de gravação do log. Todos recusam a fase não comprovada.
- [x] Preservar exclusão de código de unlock na compilação diagnóstica; demonstrar pelo mapa/símbolos que o executável não pode chamar release/DMA/transação.
- [x] Gerar pacote diagnóstico local apenas após obter GUID real da ESP; build não faz staging, altera boot order ou reinicia.
- [x] Produzir tabela de três rotas: Intel GOP independente; NVIDIA único GOP/headless; combinação não reconhecida. Nenhuma é escolhida pela presença da Intel UHD no Windows.

**Aceite:** testes de observação passam e o probe se mantém não armável. Se leitura profunda não estiver fundamentada, o primeiro boot coleta somente inventário/topologia; um segundo build poderá ser necessário.

### W4 — Captura no Dell e recuperação antes do unlock

**Entrada:** W3 e roteiro concreto de execução. **Saída privada:** duas capturas de estados iniciais independentes, manifestos/hash e relatório sanitizado.

- [ ] Preparar procedimento de voltar diretamente ao Windows Boot Manager sem mídia experimental; confirmar possibilidade de recuperação e acesso do usuário às chaves, sem copiá-las.
- [ ] Determinar Secure Boot e criptografia. Se o EFI não puder executar na política atual, declarar o bloqueio e apresentar as opções reais. Não pressupor que assinatura própria basta ou desligar proteções automaticamente.
- [ ] Apresentar o binário/hash, volume exato, alterações e forma de recuperação antes de pedir autorização para staging/boot. Não usar letra de unidade presumida.
- [ ] Fazer primeiro ensaio de probe sem unlock; depois repetir em um segundo estado inicial comprovado. Fast Startup, reinício e desligamento não são equivalentes sem evidência.
- [ ] Capturar GOP/ConOut, protocolos/openers, ancestralidade PCI, BAR/capacidades, D-state e atributos. PROM/imagens somente no envelope de leitura revisado.
- [ ] Verificar concordância das duas capturas, integridade dos arquivos e sucesso do retorno ao Windows. Falha de log ou campo ausente não pode virar “zero”.
- [ ] Decidir uma rota em DECISOES-DELL.md. Intel preservado exige demonstrar independência completa; headless exige demonstrar cadeia de release e handoff. Topologia desconhecida permanece bloqueada.
- [ ] Registrar lacunas por dado e próximo experimento específico; não pedir genericamente “mais informações”.

**Aceite:** dados suficientes para W5/W6 e recuperação demonstrada. Não executar unlock nesta tarefa.

### W5 — Portar a família GA107 e validar a transação

**Modificar no port:** `internal-boot/unlock/gpu-family.h`, `machine-profile.h`, `checks.c`; arquivos `vendor/layout_610.c`, `vbios_610.c`, `unlock_610.c` somente onde a auditoria demonstrar diferença.
**Testar:** `internal-boot/unlock/tests/test_gpu_families.py`, `test_checks.c`, `test_port.c`, `test_app.c` e testes de firmware existentes.

- [ ] Mapear diferenças entre GA10x Linux e UEFI: identificação de chip, VRAM de registro, seletores, FWSEC, região WPR, alocação/endereçamento e limpeza.
- [ ] Não converter o chip Linux `0x177` diretamente em um dword UEFI inventado. Usar valor efetivamente lido e validar sua relação com a fonte.
- [ ] Escrever teste de admissão experimental exata: 10DE:25EC / 1028:0BF8 / revisão e firmware local constatados. Subsystem correto sozinho não é suficiente.
- [ ] Implementar a menor mudança de família necessária. Não alargar GA106, não reutilizar VRAM física reportada como tamanho de região reservada.
- [ ] Rodar parser de PROM/FWSEC local contra limites e hashes verificados; rejeitar arquivo truncado, tamanho fora da região, overflow, assinatura/asset divergente e layout não coberto.
- [ ] Reproduzir a transação em RAM com os inputs reais autorizados; injetar timeout e falhas após cada etapa. Comprovar contenção e que buffers DMA não são liberados enquanto dispositivo ainda possa acessá-los.
- [ ] Reexecutar regressões de famílias existentes. Fixtures sintéticas devem ser rotuladas; não gerar prova física a partir delas.

**Aceite:** compatibilidade da transação e falhas demonstrada em host; a GPU real ainda não é considerada suportada.

### W6 — Topologia Dell, energia e perfil de pesquisa

**Modificar no port conforme a rota comprovada:** `internal-boot/boot/prepare-console.c`, `full-release.c`, `full-flow.c`, `handoff.c`; `internal-boot/unlock/headless-policy.h`, `ownership.c`, `port.c`, `machine-profile.h`.
**Criar se necessário:** `internal-boot/unlock/profile-dell-research.h` privado/ignorado, `research/profile/build-dell-research.ps1` e teste correspondente. São propostas novas, não scripts já disponíveis.

- [ ] Reutilizar a rota existente somente quando captura e replay corresponderem. Se Intel GOP puder ser preservado, testar que não se desconecta seu controlador nem seus openers. Se NVIDIA for a única saída, testar caminho headless e logs de arquivo.
- [ ] Acrescentar somente a política necessária à topologia constatada. Trocar IDs AMD por Intel não satisfaz ownership nem display independence.
- [ ] Exigir D0/estado inicial e FLR/cleanup conforme a transação. Não copiar parâmetro de gerenciamento D3 Linux para registro Windows.
- [ ] Para o primeiro ensaio, selecionar explicitamente a rota Dell de pesquisa por build; padrão permanece recusando GA107. `proven.json` e geração LOCAL comum continuam sem declarar suporte Dell.
- [ ] Vincular perfil de pesquisa a hashes exatos de fontes, captura, PROM, código GOP, assets e testes. Um JSON editável ou flag “force” não pode dispensar os guards.
- [ ] Reaproveitar verificadores existentes; garantir que a evidência do build de pesquisa cubra os jobs aplicáveis, mais os novos testes Dell. Não fabricar um `test-results.json` para satisfazer o pipeline LOCAL.
- [ ] Testar perfil ausente, dado alterado após teste, família errada, ownership alterado, BME já ativo, incoerência de atributos PCI, falta de FLR, timeout e perda de console.
- [ ] Rejeitar retry no mesmo boot após falha de contenção. Se DMA não estiver quiescente, não seguir o handoff normal.
- [ ] Revisar a rota Dell com uma segunda revisão técnica antes da escrita física. Pode ser revisão posterior separada; não é permissão para ampliar escopo ou delegar automaticamente.

**Aceite:** nenhum caminho normal passa a admitir 25EC; o build experimental exige evidência local íntegra, e falhas conservam as barreiras existentes.

### W7 — Build reproduzível e pacote de ensaio

**Modificar:** scripts de build/pacote do port estritamente necessários; workflow Windows para regressões públicas.

- [ ] Gerar EFI em diretório local, sem copiar para ESP/USB.
- [ ] Verificar PE/mapa, hashes de todos os executáveis e manifesto de fontes/toolchain/perfil/assets/evidência.
- [ ] Rodar testes atuais obrigatórios e os novos Dell. A contagem fixa de 22 pertence ao pipeline LOCAL da revisão fixada; a rota Dell precisa de seu próprio inventário explícito de cobertura, não redução silenciosa.
- [ ] Ensaiar o roteiro de retirada da mídia e boot original; definir quando interromper e como reconhecer uma falha com a tela indisponível.
- [ ] Preparar pacote e instruções da tentativa única com USB, se essa rota foi demonstrada no Dell. Não instalar inicialização automática.
- [ ] Registrar estados separados: HOST_PASS, BUILD_PASS, HARDWARE_NOT_RUN. Nenhum deles equivale a SUPPORTED.

**Aceite:** pacote identificável, revisão técnica concluída e roteiro de tentativa/recuperação pronto para aprovação final do usuário.

### W8 — Primeiro unlock e prova de ganho no Windows

**Entrada:** W7, baseline recente e autorização explícita para a tentativa física descrita.

- [ ] Confirmar identidade/versões inalteradas e usuário presente. Executar uma tentativa, sem repetição automática.
- [ ] Registrar transação, limpeza/FLR, handoff sem reset intermediário e chegada ao Windows.
- [ ] Verificar vídeo, entrada, driver, GPU, eventos novos de erro e ausência de artefatos. Qualquer falha grave interrompe o teste e aciona recuperação.
- [ ] Executar GEMM e workload primário com exatamente o mesmo ambiente de A/C, aquecimento e arquivos.
- [ ] Restaurar o estado original por procedimento demonstrado; retirar USB sozinho não prova relock durante a sessão. Confirmar baseline restaurada e registrar A2/C2.
- [ ] Classificar separadamente: efeito Tensor detectado, ganho de aplicação, qualidade, estabilidade e recuperação.

**Aceite da tentativa:** evidência íntegra e recuperação. Só promover “ganho útil” se passar pelos critérios da seção 6.

### W9 — Persistência, estabilidade e entrega utilizável

- [ ] Repetir o ensaio em pelo menos duas sessões experimentais independentes e comparar com seus controles.
- [ ] Testar separadamente idle por 5 e 30 minutos, uma carga contínua de 30 minutos, restart e suspensão/retomada disponível no notebook; registrar o estado antes/depois e reavaliar efeito Tensor.
- [ ] Avaliar bateria/AC e monitor externo apenas em ensaios separados autorizados, sem misturar com os resultados de desempenho na tomada.
- [ ] Se D3/sleep/reset perderem o efeito, documentar explicitamente a limitação. Não criar keep-awake permanente, serviço de reaplicação ou bloqueio de suspensão para esconder o problema.
- [ ] Se o efeito não sobreviver ao uso prioritário, entregar como experimento por sessão ou declarar inviável para uso diário nas condições testadas.
- [ ] Produzir relatório sanitizado: commits, hashes, configuração, logs relevantes, métricas, qualidade, limitações, recuperação e testes não executados.
- [ ] Fazer commit/PR Windows no repositório do usuário. Código/fixtures públicos; PROM, chaves, dados pessoais e assets restritos permanecem locais.
- [ ] Só declarar Windows suportado para a combinação efetivamente testada. Mudança de BIOS/VBIOS/driver exige nova validação; não ativar automaticamente.

## 6. Protocolo de medição e critérios objetivos

Fixar o protocolo em W2, antes de observar o resultado B. Começar por um caso prioritário por aplicativo, sem dezenas de variantes.

- Mesmo carregador, posição/refrigeração, perfil de energia, driver, versão do aplicativo, dados, configurações e carga de fundo. Não alterar clocks/tensão/TGP.
- Registrar GPU/VRAM, RAM/paginação, temperatura, clocks, potência e motivos de limitação. Campo indisponível fica explícito; telemetria deve ter mesma frequência, inicialmente 1 Hz, em todos os estados.
- Três aquecimentos e ao menos cinco repetições medidas por estado. Não misturar carregamento de modelo com execução aquecida. Não descartar outlier silenciosamente.
- Comparação A1/B/A2 quando não houver otimização C; C1/B/C2 quando C existir. Reportar C/A separadamente.
- Dispersão inicial proposta: IQR/mediana ≤5% em duração positiva. Se ultrapassar, investigar carga/temperatura/paginação e repetir o bloco inteiro, preservando o original.
- Restauração: mediana A2 ou C2 dentro de ±5% da referência correspondente e sem nova diferença relevante de ambiente. Caso contrário, efeito do unlock é INCONCLUSIVO.
- Meta de utilidade: redução mediana de tempo ≥10% em pelo menos um caso prioritário, com qualidade equivalente e sem regressão >5% em outro caso que foi efetivamente medido.
- Na confirmação W9, exigir o mesmo sentido de efeito em duas sessões B independentes. Calcular intervalo bootstrap de 95% da redução com seed fixo, reamostrando blocos/sessões quando existirem; não tratar milhares de iterações internas de GEMM como milhares de experimentos. Se o intervalo incluir zero, resultado inconclusivo.
- Critério numérico: manter tolerâncias documentadas por modo do benchmark, referência aprovada e zero NaN/Inf inesperados. O ganho Tensor não substitui a qualidade de saída do aplicativo.
- Whisper: comparar transcrição e, quando houver referência humana, WER; usar a mesma referência nos estados. ComfyUI: validar dimensões, ausência de corrupção e inspeção visual pareada; seed idêntica não garante imagem bit a bit idêntica entre kernels.
- Vídeo: manter resolução, codec, preset e parâmetros de qualidade, decodificar a saída e verificar duração/frames/áudio. Melhora via redução de qualidade não conta.
- Zero novo travamento, TDR, erro de dispositivo, corrupção ou falha de recuperação nos ensaios executados. Isso não prova confiabilidade de longo prazo.

Exemplo de linguagem correta: “Whisper: mediana de X para Y segundos, redução Z%, em duas sessões, configuração e qualidade preservadas”. Não escrever “3050 ficou Z% mais rápida” a partir de um único caso.

## 7. Regras de execução

As ações de código, documentação, testes de host e publicação no fork já estão no escopo autorizado. Não pedir reconfirmação para cada tarefa reversível.

Boot EFI, reinício, staging em mídia/ESP, alterações de política de boot/segurança ou firmware e mudanças de energia do sistema exigem roteiro concreto e autorização específica antes da ação. Esta revisão é planejamento; não autoriza essas operações implicitamente.

Não desligar Secure Boot/VBS/HVCI, suspender/descriptografar BitLocker, alterar BIOS/VBIOS, elevar TGP/clocks/tensão, fechar aplicativos ou mover/apagar mídia pessoal automaticamente. Não executar benchmark concorrente nem consumir downloads/modelos grandes sem necessidade acordada.

Usar estados PASSOU, FALHOU, BLOQUEADO, NÃO EXECUTADO e INCONCLUSIVO, com motivo e evidência. Se W4 bloquear, continuar apenas tarefas que não inventem a informação faltante. Não promover perfil para “proven” como forma de resolver bloqueio.

## 8. AI Brain: handover para o próximo agente

**Projeto:** Windows GPU Unlock — Dell G15 5530 / RTX 3050 6 GB.

**Objetivo:** implementar no Windows e comprovar ganho útil; Linux é somente referência.

**Regras:** preservar máquina, aplicativos e mídia; trabalhar no fork theobarros22/gpu-unlock; seguir as etapas W0–W9; não confundir teste de host com hardware. Consultar instruções AGENTS/RTK/PONYTAIL vigentes. Não publicar capturas privadas.

**Estado:** plano revisado; receita Linux experimental e teste de seleção já existem no PR 1. Nenhum port Windows Dell implementado, nenhuma captura UEFI Dell disponível, nenhum ganho medido. Esta revisão atualizou fontes e arquitetura, não executou as tarefas Windows propostas.

**Próxima ação:** começar W0 e W1: resolver o estado local sem perder mudanças, importar fonte Windows fixada, executar regressões públicas, construir/coletar inventário somente leitura. Depois implementar W2 e obter baseline. Não começar por instalar módulo Linux, editar proven.json ou gravar EFI em mídia.

**Ponto de decisão seguinte:** após W3/W4, escolher a rota a partir do GOP/energia/firmware reais do Dell. Na ausência desses dados, entregar a lacuna específica e o probe necessário; não fabricar constantes.

**Entrega final esperada:** código Windows no fork, testes e build rastreáveis, procedimento de operação/recuperação e relatório que diga exatamente onde houve ganho, onde não houve e quais estados ainda não foram validados.

