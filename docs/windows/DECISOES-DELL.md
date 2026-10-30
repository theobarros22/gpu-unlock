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
| **Estado Secure Boot** | Acesso negado sem elevação (não consultado com bypass) | Confirm-SecureBootUEFI |
| **Estado BitLocker** | Volume C: acesso negado sem elevação | Get-BitLockerVolume |
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
