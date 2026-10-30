# Decisões de Arquitetura e Evidência — Dell G15 5530 (RTX 3050 Laptop GA107)

> Documento de rastreabilidade de decisões técnicas segundo o plano W0–W9.
> Data: 29/10/2026.

---

## 1. Evidência Coletada do Sistema (W1)

O inventário sanitizado em host Windows (`windows/local/diagnostics/inventory.json`) comprovou as seguintes características concretas:

| Parâmetro | Valor Verificado no Host | Fonte de Evidência |
|---|---|---|
| **Modelo Notebook** | Dell G15 5530 | Win32_BIOS (Dell Inc.) |
| **Versão BIOS** | 1.34.0 (2026-05-25) | Win32_BIOS SMBIOSBIOSVersion |
| **OS** | Windows 11 Home Single Language, Build 26200 | Win32_OperatingSystem |
| **GPU Primária / dGPU** | NVIDIA GeForce RTX 3050 6GB Laptop GPU | nvidia-smi / Win32_VideoController |
| **PCI IDs dGPU** | `10DE:25EC`, Subsystem `1028:0BF8`, Rev `A1` | PCI PNPDeviceID / nvidia-smi |
| **Localização PCI** | BDF `00000000:01:00.0` (Bus 1, Dev 0, Fun 0) | nvidia-smi |
| **VBIOS dGPU** | `94.07.82.40.2f` | nvidia-smi query |
| **Driver NVIDIA** | `610.88` (WDDM 3.2, CUDA UMD 13.3) | nvidia-smi query |
| **VRAM Total** | 6144 MiB (GDDR6) | nvidia-smi query |
| **GPU Integrada (iGPU)** | Intel(R) UHD Graphics (`8086:A78B`, Subsystem `1028:0BF8`) | Win32_VideoController |
| **Estado Secure Boot** | **ATIVO (`UEFISecureBootEnabled = 1`)** | `HKLM:\SYSTEM\CurrentControlSet\Control\SecureBoot\State` |
| **ESP Windows Real (GUID)** | `{0d381b23-ebd2-43b1-ac69-9b33273b73ce}` (Partição 1, NVMe 200 MiB) | `Get-Partition -DiskNumber 0` |
| **Estado BitLocker** | Protegido / Requer verificação prévia de Chave de Recuperação | `manage-bde -status` (acesso restrito) |
| **Pressão de Memória** | ~845 MiB livres no momento da coleta (~16 GB total) | Win32_OperatingSystem |

---

## 2. Decisão de Topologia e Exibição (W3)

No ambiente pré-boot (UEFI DXE), a propriedade do console de saída (GOP - Graphics Output Protocol) pode estar configurada de três maneiras diferentes. Nenhuma é presumida a partir do driver de vídeo do Windows:

| Rota | Descrição Técnica | Condição de Adoção | Impacto no Unlock |
|---|---|---|---|
| **Rota 1: Intel GOP Independente** | O firmware UEFI conecta a tela interna diretamente ao controlador GOP Intel Graphics (`8086:A78B`). A dGPU NVIDIA não possui manipuladores ConOut abertos. | Protocolo GOP presente e ativo exclusivamente no handle PCI Intel; nenhum handle filho de ConOut na dGPU. | **Ideal para unlock sem perda de vídeo:** dGPU pode ser liberada e reconfigurada sem desativar a tela do usuário. |
| **Rota 2: NVIDIA GOP / Headless Necessário** | A dGPU NVIDIA é o controlador GOP primário (ou exclusivo em MUX discreto). Liberar o driver UEFI da NVIDIA desativa a exibição até a carga do driver Windows. | Handle de vídeo ConOut associado ao BDF `01:00.0`. | **Exige modo headless estrito:** gravação de progresso em arquivo de log USB/ESP, sem exibição em tela até a transição para o Windows. |
| **Rota 3: Combinação Não Reconhecida / MUX Dinâmico Bloqueado** | Topologia não mapeada (ex: GOP compartilhado por protocolo proprietário Dell sem separação limpa de ownership). | Protocolos proprietários ou openers que recusam disconnect com erro de recurso. | **BLOQUEIO IMEDIATO:** O EFI não deve prosseguir para a fase de escrita/transação se não for comprovada a independência ou a rota headless segura. |

---

## 3. Diretrizes de Segurança do Probe de Observação

1. **Separação Rígida de Fases:**
   - O primeiro boot diagnóstico executa **exclusivamente leitura** (`GU_DIAGNOSTIC_ONLY`, `GU_PROBE_GENERIC`).
   - É terminantemente proibida qualquer escrita em registradores PCI de comando (zero BME toggle descontrolado), MMIO de controle, DMA, FLR forçado ou modificação de NVRAM.
2. **Auditoria de Janela MMIO GA107:**
   - O chip GA107 (RTX 3050 Laptop) possui layout de registradores da família Ampere, mas dimensões e offsets de BAR0 devem ser validados contra o VBIOS real e o BAR reportado pelo UEFI antes de qualquer leitura PROM profunda.
3. **Preservação de Integridade:**
   - O pacote diagnóstico só é montado para o disco/pendrive após confirmação de partição real fornecida pelo operador, impedindo substituição acidental de bootloader do Windows.

---

## 4. Confirmação Empírica da Rota 1 no Boot Físico (W4)

A execução em hardware real via `BOOTX64.EFI` no Dell G15 5530 comprovou os seguintes fatos:

1. **Adoção Formal da Rota 1 (Intel GOP Independente):**
   - O console `ConOut` (`0x5787ca18`) está associado exclusivamente ao controlador gráfico Intel UHD (`010106000002` em Bus 0, Dev 2).
   - A GPU dedicada NVIDIA RTX 3050 (`01:00.0`) não possui display handles ou buffers GOP abertos no pre-boot UEFI.
   - Conclusão: O unlock do chip GA107 pode ser executado em modo acelerador puro sem necessidade de desanexação de console ou interrupção de vídeo.

2. **Captura Frio-Total (Cold State MMIO e VBIOS):**
   - Chip ID: `0xb77000a1` (GA107 Ampere)
   - VRAM: `0x1800` (6144 MiB)
   - BAR0: `0x74000000` (16 MiB)
   - VBIOS ROM extraída com sucesso: `PROM.BIN` (1.048.576 bytes, SHA256: `e8f866920f803f61d67d805ff15ea46b1046c18c588def0f962fdcd8e937057c`)
   - Driver GOP Dell NVIDIA extraído: `IMG70.BIN` (159.456 bytes, versão `6001a`, .text SHA256: `d622c6f68201bf0d79658a844b032e2ecadab7e457e9cd608c16ceadc74cb13b`)
   - FWSEC container: localizado com precisão em `0x42d74`, tamanho `0xea00`, 3 assinaturas válidas.

---

## 5. Auditoria de W6–W8 e evidência das guardas Dell (30/10/2026)

### 5.1. O que as capturas comprovam

| Guarda relaxada no perfil Dell | Evidência | Fonte |
|---|---|---|
| BME já ativo no cold boot | Registrador de comando da dGPU `0x0006` (memória + bus master) nas duas capturas: `cfg dwords=25ec10de 00100006 ...` | `windows/local/captures/dell-g15-5530-capture-{1,2}/DIAG00.TXT` (privado) |
| Sem GOP NVIDIA (`GU_HYBRID_DGPU_NO_CONSOLE`) | 2 GOPs no pré-boot: um com caminho `PciRoot/Pci(2,0)/AcpiAdr` (Intel UHD) e o console agregado sem caminho. Nenhum GOP em `01:00.0` | mesma captura, linhas `gops=0002` |
| Firmware GA102 em chip GA107 | No RM aberto 610.43.03, `kgspGetBinArchiveBooterLoadUcode` e `kgspGetBinArchiveGspRmBoot` usam a variante `_GA102` para `GA102 \| GA103 \| GA104 \| GA106 \| GA107` | `src/nvidia/generated/g_kernel_gsp_nvoc.c` do pacote `NVIDIA-kernel-module-source-610.43.03` |

Limites: os arquivos das duas capturas têm o mesmo horário de gravação, então não há como afirmar que vieram de dois cold boots independentes. Na captura 1, a leitura MMIO foi recusada (`probe-unreviewed-envelope`).

### 5.2. Regressão corrigida

No `486ffc4`, os ramos Dell usavam `#if GU_CONSOLE_CHILD_COUNT == 0`. Uma macro indefinida vale 0 no pré-processador. Em `unlock/headless-policy.h`, incluído por `app.c` sem o padrão de `prepare-console.c`, a regra de console Dell entrou no filho de unlock da B650M 3090 FE, da X870 3090 Ti e da H610M 3060. Correção: os ramos usam `GU_HYBRID_DGPU_NO_CONSOLE`, definido só no perfil Dell. `machine-profile.h` recusa compilar essa macro com outro perfil, e também recusa um perfil Dell que declare filhos de console. Teste: `internal-boot/unlock/tests/test_dell_hybrid_guards.py`, que dá 15 falhas no código do `486ffc4` e passa com a correção.

`handoff.c`: o filtro que tira da tela os registros `pre-release-cold-wpr2-hi` e `pre-release-cold-ss0` agora compara o nome exato. Antes, lia `Event[17]` sem conferir o tamanho da string. Os dois registros levam valores de registrador no campo de status. A falha real da pré-condição (`pre-release-cold-check`) continua aparecendo na tela e pulando o unlock.

### 5.3. Resultado de W8 reclassificado: INCONCLUSIVO

| | C (29/10, 22:56) | B (30/10, 07:49) |
|---|---|---|
| Carregamento do modelo | 9,036 s | 1,310 s |
| Inferência aquecida, mediana de 3 | 1,2015 s (1,08–1,41) | 0,9622 s (0,95–0,99) |
| Duração total do processo | 16,38 s | 6,03 s |

Os 63% comparam a duração total do processo, quase toda feita de carregamento de disco. A inferência aquecida caiu ~20%, com n=3, em sessões diferentes, sem C2 e sem GEMM. A dispersão de C passa dos 5% da §6 do plano.

### 5.4. Pendências que ficam abertas

- `local-profile.ps1` coloca o perfil Dell na lista `$reviewed` do manifesto USB. O plano proíbe promover o Dell sem W9. Fica registrado, sem alteração, até a decisão do operador.
- O plano pede uma única tentativa física. O W8 cita "Ensaio #6", e os logs `HLS000009.TXT` e `AUTO000004` não estão em `windows/local`.
