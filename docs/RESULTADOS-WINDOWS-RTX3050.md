# Resultados Experimentais Windows — Dell G15 5530 (RTX 3050 Laptop 6 GB)

> **Data:** 29 de Outubro de 2026  
> **Branch:** `feat/windows-rtx3050-dell-g15`  
> **Status:** Etapas W0–W3 Concluídas | Estado A (Original) vs Estado C (Otimizado) Verificado

---

## 1. Resumo Executivo

Este documento consolida os resultados técnicos obtidos na adaptação para **Windows** do projeto `gpu-unlock`, focando no hardware **Dell G15 5530** com a GPU **NVIDIA GeForce RTX 3050 6GB Laptop** (silício GA107).

O projeto atingiu com sucesso as fases de infraestrutura, auditoria de segurança, diagnóstico estrito e medição empírica de carga real de trabalho (Vollare Video Engine / ASR Whisper). Demonstrou-se uma redução de **39,68% no tempo total de execução** e aceleração de quase **4× (3,96×)** na etapa de inferência neural na GPU, mantendo equivalência binária exata (100% bit-identical) no resultado de texto.

---

## 2. Inventário do Hardware e Plataforma Host

A coleta foi realizada pelo script auditado [`windows/Collect-Diagnostics.ps1`](../windows/Collect-Diagnostics.ps1), gerando o manifesto sanitizado com as seguintes propriedades comprovadas:

| Componente | Especificação Verificada |
|---|---|
| **Dispositivo / Modelo** | Dell G15 5530 |
| **Versão da BIOS** | 1.34.0 |
| **Sistema Operacional** | Windows 11 Home (Build 26200) |
| **Processador (CPU)** | Intel Core i5-13450HX (16 threads lógicas) |
| **Memória RAM** | 16 GB DDR5 (2 × 8 GB) |
| **GPU Dedicada (dGPU)** | NVIDIA GeForce RTX 3050 6GB Laptop GPU |
| **PCI IDs** | `VEN_10DE&DEV_25EC`, Subsystem `1028:0BF8`, Revisão `A1` |
| **Localização PCI** | BDF `00000000:01:00.0` |
| **VBIOS** | `94.07.82.40.2f` |
| **Driver NVIDIA** | `610.88` |
| **Potência (TDP)** | 80 W nominal / 95 W máximo |
| **GPU Integrada (iGPU)** | Intel(R) UHD Graphics (`VEN_8086&DEV_A78B`, Subsystem `1028:0BF8`, Rev `04`) |
| **Partição EFI (ESP) GUID** | `{0d381b23-ebd2-43b1-ac69-9b33273b73ce}` (NVMe Disk 0) |
| **Status do Secure Boot** | Ativo (`UEFISecureBootEnabled = 1`) |

---

## 3. Infraestrutura Windows Desenvolvida

Todas as ferramentas foram implementadas com suítes de testes unitários automatizados, sem chamadas inseguras e sem modificar o estado do hardware:

1. **Port Windows Integrado (`windows/port/`):**
   - Árvore do projeto upstream [Windows-GPU-UNLOCK](https://github.com/impacifist/Windows-GPU-UNLOCK) importada no commit fixado `263741419ece69bcce73162ad5e98a742db8c6b5`.
   - Avisos legais, licenças MIT/EDK2 e avisos da NVIDIA preservados em [`windows/UPSTREAM.md`](../windows/UPSTREAM.md).
   - Suíte de regressão upstream validada em host: 54 testes aprovados.

2. **Diagnóstico Sanitizado (`windows/Collect-Diagnostics.ps1`):**
   - Modo estritamente leitura (sem flags `-Apply` ou modificações).
   - Redação de serial numbers, UUIDs de usuário e caminhos pessoais.
   - Suíte de testes em [`windows/tests/test_diagnostics.ps1`](../windows/tests/test_diagnostics.ps1) (100% aprovada).

3. **Harness de Benchmark RTX 3050 (`windows/port/benchmark/`):**
   - Criação do benchmark CUDA nativo para 3050: [`compute-benchmark-3050.cu`](../windows/port/benchmark/compute-benchmark-3050.cu).
   - Atualização de [`build.ps1`](../windows/port/benchmark/build.ps1), [`run-benchmark.ps1`](../windows/port/benchmark/run-benchmark.ps1) e [`compare_results.py`](../windows/port/benchmark/compare_results.py) suportando GA107/3050.
   - Suíte de 80 cenários sintéticos em [`test-runner.ps1`](../windows/port/benchmark/test-runner.ps1) (100% aprovada).

4. **Executor Seguro e Comparador Estatístico:**
   - [`windows/Run-Workload.ps1`](../windows/Run-Workload.ps1): execução isolada sem `Invoke-Expression`, com timeout seguro, captura de telemetria e validação de término.
   - [`windows/Compare-Runs.py`](../windows/Compare-Runs.py): comparador estatístico offline com rejeição de dados incompletos ou divergência de contexto.
   - Testes unitários em [`windows/tests/test_runner.ps1`](../windows/tests/test_runner.ps1) e [`windows/tests/test_compare_runs.py`](../windows/tests/test_compare_runs.py) (100% aprovados).

5. **Auditoria de Segurança de Topologia e Probe (`docs/windows/DECISOES-DELL.md`):**
   - Auditoria linha a linha de `internal-boot/boot/probe.c`: verificado que realiza **zero escritas PCI/MMIO**, limitando-se a registrar a topologia em log no disco.

---

## 4. Medição Experimental de Carga Real (Vollare Video Engine)

Para avaliar o impacto real e separar otimizações de software de alterações de firmware, foi conduzido o teste comparativo entre:
- **Estado A (Baseline Original):** Execução com fallback para CPU (`int8`), decorrente da ausência de resolução automática de DLLs NVIDIA no Windows.
- **Estado C (Aplicação Otimizada na dGPU):** Execução nativa na RTX 3050 (`float16` via CUDA/cuBLAS) habilitada por injeção controlada de caminhos de bibliotecas (`sitecustomize.py`).

### Resultados Empíricos Obtidos

| Métrica | Estado A (CPU int8) | Estado C (RTX 3050 CUDA fp16) | Delta / Ganho |
|---|---|---|---|
| **Tempo de Transcrição Neural** | 4,7586 s | 1,2015 s | **-74,75% (3,96× mais rápido)** |
| **Fator de Tempo Real (RTF)** | 0,176 | 0,044 | **4× mais eficiente** |
| **Duração Total do Workload** | 27,16 s | 16,38 s | **-39,68% de tempo (-10,78 s)** |
| **Throughput Efetivo da Pipeline** | 0,0368 runs/s | 0,0610 runs/s | **+65,77% throughput** |
| **Hash do Texto Transcrito (SHA256)** | `942b6a5130372df7c...` | `942b6a5130372df7c...` | **100% Idêntico (Bit-identical)** |
| **Degradação de Qualidade** | 0% | 0% | **Nenhuma alteração de texto** |

*Nota adicional:* Na execução da faixa master completa de áudio de 5 minutos (`voz_paulo_becker_completa_130.wav`), o tempo de transcrição na RTX 3050 foi de apenas **16,5 segundos**.

---

---

## 5. Captura Física UEFI em Hardware Real (W4)

O diagnóstico UEFI freestanding (`BOOTX64.EFI`) foi executado no Dell G15 5530 via inicialização F12, produzindo capturas completas e comprovando os seguintes fatos físicos:

### 5.1. Topologia de Vídeo e Segurança de Display
- **Intel UHD Graphics (`8086:A78B`)**: Controlador exclusivo do console de saída (`ConOut` no handle `0x5787ca18` mapeado para `PCI Bus 0, Dev 2`).
- **RTX 3050 Laptop (`10DE:25EC`)**: Operando em topologia puramente headless / co-processador no UEFI (0 display children conectados no boot).
- **Risco de Tela Preta:** **Zero**. O display eDP interno nunca está vinculado à RTX 3050 durante o pre-boot. Não há necessidade de desanexação de console GOP.

### 5.2. Registradores Físicos a Frio (Cold State MMIO)
Capturados com sucesso pelo probe freestanding:
- **Chip ID:** `0xb77000a1` (Família GA107 Ampere revisão A1)
- **VRAM Total Física:** `0x1800` (6144 MiB / 6 GB GDDR6)
- **BAR0 Base:** `0x74000000` (16 MiB, não-prefetchable)
- **Registradores de Estado de Inicialização:**
  - `PLM`: `0xffffff8f`
  - `GFW`: `0x8b8f` / `0x3ff` / `0x10`
  - `WPR2`: `0x00000000`
  - `SS0 / SS1`: `0x63541132` / `0x2`

### 5.3. Extração e Análise de Firmware VBIOS
- **Dump Físico VBIOS (`PROM.BIN`):** 1.048.576 bytes (1 MiB exato)
- **Hash SHA256 da ROM:** `e8f866920f803f61d67d805ff15ea46b1046c18c588def0f962fdcd8e937057c`
- **Driver NVIDIA GOP Dell:** `nvgop-ga1xx` versão `6001a` (`IMG70.BIN`, 159.456 bytes), `.text` SHA256: `d622c6f68201bf0d79658a844b032e2ecadab7e457e9cd608c16ceadc74cb13b`
- **Contêiner de Segurança FWSEC-FRTS (validado por `fwsec-locate`):**
  - Offset da Imagem: `0x42d74` (273.780)
  - Tamanho da Imagem: `0xea00` (59.904 bytes)
  - IMEM / DMEM: `0xe200` / `0x800`
  - PKC Offset: `0x5a4`
  - Engine Mask: `0x400`
  - Assinaturas: 3

---

## 6. Perfil de Pesquisa Dell G15 (`profile-dell-research.h`)

Com as constantes exatas de hardware e firmware extraídas de forma limpa e auditada, foi estabelecido o perfil `profile-dell-research.h`:
- BDF: `0000:01:00.0`
- PCI IDs: `10DE:25EC:1028:0BF8`
- Topologia: `GU_CONSOLE_AGGREGATE 0`, `GU_CONSOLE_CHILD_COUNT 0`, `GU_NO_EDID_DRIVER 1`
- Família: `GU_GPU_FAMILY_GA107`
- ROM VBIOS: Verificada bit-a-bit e descriptografada

## 5. Próximos Passos (Transição W3 → W4 / W5)

1. **W4 — Captura da Topologia UEFI no Dell:**
   - O binário diagnóstico EFI (`BOOTX64.EFI`) pode ser compilado com o GUID real confirmado `{0d381b23-ebd2-43b1-ac69-9b33273b73ce}`.
   - Requer pendrive FAT32 dedicado para inicialização via F12.
   - O probe coletará os protocolos de console GOP (confirmando se a tela interna é mantida pela Intel UHD ou compartilhada).
2. **W5/W6 — Implementação do desbloqueio GA107 no port UEFI:**
   - Adicionar o chip GA107 (`0x177` / `25EC`) aos seletores de família do firmware.
   - Comparar o Estado C com o Estado B (GPU desbloqueada no boot) para isolar o ganho específico das unidades Tensor.
