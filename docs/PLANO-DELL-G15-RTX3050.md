# Adaptação RTX 3050 Laptop no Dell G15 5530

> Plano de execução e transferência para outro agente. Estado em 29/10/2026.

**Objetivo:** desenvolver e validar, prioritariamente no Windows, uma adaptação experimental do gpu-unlock para este notebook, medindo o efeito em IA e vídeo.

**Arquitetura:** este repositório contém um módulo Linux. A adaptação Windows depende de port UEFI separado e de evidência própria do firmware, da topologia de vídeo e do estado de energia do Dell. O caminho Linux deste fork é experimental e desativado por padrão. Nenhum dos dois caminhos foi validado em hardware nesta sessão.

**Tecnologias:** C/PCI/kernel Linux; C/UEFI, Python, PowerShell, LLVM e EDK2 no estudo do port Windows; CUDA/cuBLAS para medição quando disponíveis. Instalar ferramentas apenas quando necessário, sem alterar ambientes existentes silenciosamente.

## Memória compartilhada para o agente receptor

### Objetivo e contexto

O usuário trabalha com edição/renderização (DaVinci Resolve, Premiere, CapCut, After Effects e FFmpeg), IA local (Whisper, ComfyUI e Ollama) e agentes de código. Pediu alterações no [fork theobarros22/gpu-unlock](https://github.com/theobarros22/gpu-unlock) e um plano detalhado para outro agente. Preserve projetos e mídias locais. Inferência de modelos na nuvem não usa a GPU local, salvo ferramentas ou modelos locais acionados pelos agentes.

### Hardware observado nesta sessão

| Item | Valor observado | Limite |
|---|---|---|
| Computador | Dell G15 5530, BIOS 1.34.0 | Revalidar antes de ensaio físico. |
| GPU | NVIDIA GeForce RTX 3050 6GB Laptop | 6144 MiB informados por nvidia-smi. |
| PCI | VEN 10DE, DEV 25EC, subsistema 1028:0BF8, revisão A1 | Identificação PCI não comprova layout de firmware. |
| VBIOS | 94.07.82.40.2f | Hash PROM, layout e offsets não capturados. |
| Sistema | Windows 11 Home build 26200; driver 610.88 | Não é evidência de compatibilidade do port. |
| CPU e memória | i5-13450HX; 16 GiB RAM em dois módulos de 8 GiB | Aproximadamente 0,8–1 GiB disponível no instante da consulta; a carga varia. |
| GPU integrada | Intel UHD presente no Windows | Não determina qual GOP UEFI controla a tela. |
| Energia | padrão 80 W; máximo reportado 95 W | O limite dinâmico e a potência efetiva variam. Não elevar limites. |
| Segurança | Secure Boot e BitLocker: **desconhecidos** | Consultas sem elevação retornaram acesso negado. |

Teste mínimo Windows: um frame sintético 1080p foi codificado com FFmpeg h264_nvenc e hevc_nvenc, com saída nula e exit code zero. Isso prova apenas funcionamento básico; não mede desempenho ou estabilidade.

O [relato atualizado da issue 111](https://github.com/Zagitta/gpu-unlock/issues/111#issuecomment-6471857518) usa o mesmo modelo, DEV e subsistema no Linux com patch local e gerenciamento D3 ajustado. Reportou GEMM FP16 +57%, BF16 +73% e TF32 +66%. O VBIOS do relato é **94.07.82.40.96**, diferente do nosso. São números de terceiro em outro sistema, não ganhos medidos aqui.

### Estado de desenvolvimento

- Base Linux analisada: [7eb51bcc](https://github.com/Zagitta/gpu-unlock/commit/7eb51bccae0a0b7e599e084d971170e9a1e82d0c).
- Base do port Windows analisada: [23cc0285](https://github.com/impacifist/Windows-GPU-UNLOCK/commit/23cc028512acbb873cff8de38acdd63c66c98ea9). Revalidar HEAD e documentação ao retomar.
- Este fork acrescenta receita GA107/25EC e restringe sua seleção ao subsistema Dell 1028:0BF8 e ao parâmetro Linux experimental_ga107, desativado por padrão. O alvo também precisa ser escolhido em targets. É código experimental, sem demonstração no VBIOS local, sem instalação e sem alteração no Windows.
- tests/recipes_test.c verifica seleção e recusa no host. Não prova segurança do kernel, boot, firmware ou ganho.
- Ainda não existe implementação Windows para este Dell neste fork. O port citado é projeto separado e não demonstra suporte para esta combinação.

### Próxima ação

Verificar branch e diff deste fork, executar testes de host e CI, confirmar os limites abaixo e iniciar P0–P2. Produzir desenho e testes de host do port Windows. Não declarar que o desbloqueio está operacional nem aplicar uma imagem de boot com base apenas nesta documentação.

## Regras e critérios globais

1. Registrar commits, versões, hashes e estados reais; distinguir NÃO EXECUTADO, BLOQUEADO, PASSOU, FALHOU e INCONCLUSIVO para testes de host, build, boot, estabilidade e desempenho.
2. O código altera permissões internas e seletores antes do driver. Preservar ownership, isolamento DMA, checagens de chip, FLR, WPR, readback e contenção de falhas.
3. Não desativar Secure Boot, VBS/HVCI ou BitLocker; não descriptografar volumes nem modificar BIOS/vBIOS, partições, driver, prioridade de boot ou energia para contornar uma recusa. Apresentar previamente a alteração exata, impacto e recuperação e obter autorização específica para ensaio de firmware/boot.
4. Não fechar programas, apagar caches, usar mídia pessoal, instalar dependências globais ou executar benchmarks concorrentes sem combinar. Preservar arquivos brutos e resultados.
5. Não inferir PROM hash, BAR, offsets, capacidades PCI, assinatura FWSEC, valores de registro ou topologia de outra máquina. Dados sem evidência são bloqueios.
6. Não alterar potência, tensão, clock ou refrigeração. Interromper em artefato, reset de driver, erro PCI, perda de vídeo, comportamento térmico anormal ou falha de recuperação.
7. Windows é o alvo principal. Linux é referência opcional; não migrar o sistema nem apresentar comandos Linux como solução Windows.
8. Não enviar issues, comentários ou resultados a terceiros sem autorização explícita. O repositório é público: não publicar serial, chaves, GUIDs privados, arquivos pessoais ou capturas brutas sem revisão.

## Alternativas

| Caminho | Utilidade | Decisão |
|---|---|---|
| Perfil UEFI Windows adaptado ao Dell | Investigar efeito no sistema atual | Principal para pesquisa, condicionado a capturas e testes próprios. |
| Linux isolado | Há relato promissor para mesmo PCI/subsistema | Laboratório opcional com autorização; VBIOS e ambiente são diferentes. |
| Ajustes de aplicativos sem unlock | Pode melhorar o fluxo independentemente do firmware | Linha paralela de medição/configuração reversível; não prova o efeito Tensor. |

## P0 — Fontes e estado local

**Entrega:** manifesto de versões, diagnóstico e lacunas, sem segredos.

- [ ] Confirmar git status, branch e commit no fork; preservar alterações existentes e ler AGENTS.md.
- [ ] Fixar as referências acima e verificar mudanças upstream antes de portar código.
- [ ] Registrar modelo, BIOS, VBIOS, PCI, RAM, versão do driver e modo de energia usando consultas de leitura. Não registrar número de série.
- [ ] Consultar Secure Boot e criptografia. Se exigir elevação, marcar BLOQUEADO e preparar solicitação específica; não publicar chaves.
- [ ] Registrar ferramenta, versão, comando e resultado de cada coleta.

## P1 — Receita Linux experimental e teste de host

**Arquivos:** kernel/gpu_unlock/recipes.c, recipes.h, main.c, tests/recipes_test.c e job recipe-selection na CI.

- [ ] Confirmar que 25EC seleciona chip 0x177 e família GA10x; requer experimental_ga107=1, subsistema 1028:0BF8 e seleção em targets; recusa outros subsistemas.
- [ ] Verificar que placas previamente suportadas mantêm comportamento e IDs desconhecidos não recebem receita.
- [ ] Compilar e executar o código real de seleção em host:

~~~sh
cc -std=c11 tests/recipes_test.c kernel/gpu_unlock/recipes.c -o /tmp/recipes-test
/tmp/recipes-test
~~~

- [ ] Executar a CI de compilação do módulo Linux contra os kernels previstos. Compilação de host não substitui módulo Linux.
- [ ] Revisar que o parâmetro é somente leitura após carga, que targets=all sozinho não ativa a 25EC e que resume só inclui placas admitidas no início.
- [ ] Aprovação desta tarefa significa seleção testada, não boot ou ganho validado.

## P2 — Limites e mapeamento do port Windows

**Entrada:** [guia de portabilidade](https://github.com/impacifist/Windows-GPU-UNLOCK/blob/23cc028512acbb873cff8de38acdd63c66c98ea9/docs/PORTABILITY.en.md), [compatibilidade](https://github.com/impacifist/Windows-GPU-UNLOCK/blob/23cc028512acbb873cff8de38acdd63c66c98ea9/docs/COMPATIBILITY.en.md) e [novo computador](https://github.com/impacifist/Windows-GPU-UNLOCK/blob/23cc028512acbb873cff8de38acdd63c66c98ea9/docs/NEW-MACHINE.en.md).

O gerador LOCAL possui perfis e códigos revisados específicos. O probe genérico pode inventariar parcialmente a 25EC, mas o envelope atual recusa leitura profunda de MMIO/PROM para ela. Essa recusa não é uma captura completa.

| Componente existente | Investigação necessária |
|---|---|
| internal-boot/boot/probe.c: ProbeEnvelope, GuProbeGpu | Inventário PCI/GOP e elegibilidade de leitura; não liberar MMIO apenas por ID. |
| internal-boot/unlock/gpu-family.h, machine-profile.h e research/profile/make-profile.py | Identidade, chip, VRAM de registro, PROM, BIOS e código; não promover prematuramente proven.json. |
| boot/prepare-console.c, boot/full-release.c, unlock/headless-policy.h | Descobrir GOP Intel no pré-boot e cadeia de ownership; a política atual pode recusá-la. |
| unlock/checks.c, ownership.c, port.c | Preservar D0, FLR, BME, BAR, DMA e falhas. D3 é recusa, não convite para forçar transição. |
| unlock/vendor/unlock_610.c, layout_610.c, vbios_610.c | Verificar compatibilidade do PROM e geometria local com assets e transação. |
| boot/handoff.c, full-flow.c | Preservar recuperação; não fazer retry ou fallback inseguro depois de falha de liberação. |

- [ ] Mapear pré-driver → seleção → console → ownership → transação → FLR/cleanup → Windows → D3/D0.
- [ ] Comparar estruturas e guards Linux/UEFI com links por commit; registrar invariantes e divergências.
- [ ] Decidir rota a partir de captura real. Não substituir identificadores AMD por Intel mecanicamente nem remover checagens para contornar a tela.
- [ ] Criar tabela de dados ausentes e critérios de recusa. Sem topologia/PROM/firmware identificados, manter BLOQUEADO.

## P3 — Testes de host antes do hardware

**Entrega:** proposta de patch isolado e testes reprodutíveis, sem boot.

- [ ] Reproduzir primeiro testes existentes do port fixado, com ferramentas disponíveis; registrar versões e resultados.
- [ ] Cobrir fixtures sintéticas para 25EC correto, subsistema diferente, chip incorreto, PROM/hash divergente, BAR inválido, D3, FLR ausente, BME ativo, GOP inesperado e ownership alterado. Cada erro deve recusar antes de escritas.
- [ ] Separar fixtures sintéticas das capturas reais. Não apresentar fixture como prova física.
- [ ] Se houver GOP Intel preservado, testar grafo de protocolos e identidade do console antes/depois; alterar política somente após evidência e revisão.
- [ ] Testar falhas de alocação, timeout, limpeza DMA e recuperação; não liberar buffers se quiescência não estiver comprovada.
- [ ] Integrar novos testes ao conjunto obrigatório de qualquer perfil novo. CI verde não comprova boot.

Exemplos de testes existentes no port, ainda **não executados nesta sessão**:

~~~powershell
python -I research/profile/test_family_admission.py
python -I research/profile/test_local_topology.py
python -I research/profile/test_probe_records.py
python -I research/profile/test_compatibility.py
~~~

Consultar os scripts da revisão fixada para requisitos LLVM/MSVC. Não tratar new-machine.ps1 como dry-run genérico: pode gerar perfil e construir artefatos nas etapas seguintes.

## P4 — Capturas reais e recuperação

**Pré-requisito:** roteiro concreto revisto e autorização específica antes de executar EFI, reiniciar ou alterar configuração.

- [ ] Preparar recuperação independente pelo Windows Boot Manager e confirmar inicialização sem o dispositivo experimental.
- [ ] Identificar estado de criptografia e onde o usuário guarda a chave de recuperação, sem copiá-la ou expô-la.
- [ ] Planejar probe diagnóstico sem unlock, sem liberação de drivers e sem DMA; auditar suas operações. O boot do probe exige revisão e autorização.
- [ ] Capturar PCI, energia/FLR, BARs, GOPs, ConOut e relações de ownership. Registrar eventual recusa de leitura profunda como recusa.
- [ ] Só propor leitura profunda depois de demonstrar limites do mapa GA107 e pré-condições. Arquivar duas capturas de partidas realmente frias, com hashes e sem publicar dados sensíveis.
- [ ] Validar PROM/FWSEC e geometria com parsers apropriados. Divergência ou ausência mantém o perfil bloqueado.
- [ ] Não assumir que desligamento híbrido, reinício ou retirada do carregador resulta em partida fria. Não abrir o notebook nem desconectar bateria sem autorização.

## P5 — Perfil Windows e build de pesquisa

- [ ] Após P3 e P4, implementar perfil experimental específico para identidade e capturas locais. Não expandir para toda GA107.
- [ ] Reexecutar replays PCI, console, firmware e falha usando capturas autorizadas e assets conferidos.
- [ ] Conferir hashes de inputs: o fetcher upstream reutiliza cache e não comprova autenticidade por si. Valores de referência para os dois inputs 610.43.03 constam no [PKGBUILD fixado](https://github.com/Zagitta/gpu-unlock/blob/7eb51bccae0a0b7e599e084d971170e9a1e82d0c/packaging/arch/PKGBUILD).
- [ ] Construir artefato local sem staging, com manifesto de fontes, toolchain, perfil, assets e hashes. A versão 610.43.03 nos assets não autoriza substituir o driver Windows.
- [ ] Exigir revisão independente e plano de recuperação antes de ensaio físico. Se topologia ou firmware não puderem ser demonstrados, parar com diagnóstico.

## P6 — Primeiro ensaio supervisionado

**Pré-requisito:** P5 aprovado, backup e recuperação demonstrados, usuário presente e autorização explícita para a tentativa e alterações exatas. Preferir ensaio único via USB sem alterar partições ou boot automático, se o fluxo específico tiver sido validado.

- [ ] Confirmar identidade, firmware, energia e integridade dos artefatos.
- [ ] Registrar logs, vídeo/entrada, ownership, DMA, FLR, readback e handoff. Mensagem unlocked isolada não é aceite.
- [ ] Se falhar após liberação ou não houver certeza de quiescência, seguir procedimento de desligamento documentado; não repetir automaticamente nem continuar Windows em estado incerto.
- [ ] Após recuperação, confirmar vídeo, teclado, driver, GPU e logs de erro.
- [ ] Não afirmar persistência após idle, D3, restart ou suspensão sem testes próprios. O parâmetro Linux de D3 não é uma solução Windows demonstrada.

## P7 — Desempenho e correção

**Pré-requisito:** janela de benchmark adequada, sem outras medições concorrentes. Se a pressão de RAM inviabilizar comparação, registrar e interromper; não encerrar processos automaticamente.

- [ ] Fazer A1/B/A2: original, experimental, restauração comprovada. Usar mesmos driver, fonte, posição, carga, versões e dados; documentar diferenças.
- [ ] Aquecer antes de medir. Proposta inicial: três aquecimentos e pelo menos cinco repetições por estado; registrar mediana, dispersão, dados brutos, temperatura, potência, clocks, VRAM, RAM e paginação.
- [ ] Medir FP16/BF16/TF32 com acumulação FP32 demonstrada pelo caminho executado, e controles FP32/INT8. Validar contra referência e tolerâncias por precisão; reprovar NaN/Inf ou corrupção.
- [ ] Medir Whisper com mesmo áudio/modelo/precisão/lote; ComfyUI com modelo/workflow/seed/resolução fixos; Ollama com mesmo modelo/quantização/contexto/prompt e distribuição CPU/GPU.
- [ ] Medir exportação real por editor prioritário e FFmpeg H.264/HEVC, verificando saída e sincronismo. NVENC é bloco distinto; não atribuir ganho de codificação ao Tensor sem prova.
- [ ] Separar carregamento, prefill, primeira execução, execução aquecida, geração e tempo total. Modelos quantizados e tarefas limitadas por memória podem não melhorar.
- [ ] Critérios propostos, não promessas: dispersão baseline ≤5%; A2 dentro de ±5% de A1; ganho mediano ≥10% em pelo menos um fluxo prioritário com incerteza que exclua ganho zero; sem regressão >5% nos demais fluxos ou erros novos. Caso contrário, declarar inconclusivo ou sem ganho prático.

## P8 — Ciclo de vida e entrega

- [ ] Sob autorização para as ações específicas, testar separadamente partida fria, restart, idle/D3/D0, suspensão e retomada; não reaplicar cegamente.
- [ ] Reprovar em travamento, falha de recuperação, corrupção ou instabilidade. Ganho isolado em GEMM não aprova uso cotidiano.
- [ ] Preparar relatório com commits, ambiente, diff, testes executados/não executados, recuperação, dados brutos, resultados A/B/A e limitações.
- [ ] Entregar alteração experimental em branch/PR para revisão. Não marcar suporte Windows concluído sem evidência física e workloads reais.

## Referências

- [Receitas Linux](https://github.com/Zagitta/gpu-unlock/blob/7eb51bccae0a0b7e599e084d971170e9a1e82d0c/kernel/gpu_unlock/recipes.c) e [transação](https://github.com/Zagitta/gpu-unlock/blob/7eb51bccae0a0b7e599e084d971170e9a1e82d0c/kernel/gpu_unlock/unlock_610.c).
- [Compatibilidade e limites Windows](https://github.com/impacifist/Windows-GPU-UNLOCK/blob/23cc028512acbb873cff8de38acdd63c66c98ea9/docs/COMPATIBILITY.en.md).
- [Relato do Dell 25EC em Linux](https://github.com/Zagitta/gpu-unlock/issues/111#issuecomment-6471857518).
- [Diferença entre ganho GEMM e workload real](https://github.com/Zagitta/gpu-unlock/issues/137): outro hardware; não extrapolar para o Dell.
