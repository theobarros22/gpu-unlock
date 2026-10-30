# Collect-Diagnostics.ps1 - Read-only inventory for Windows GPU Unlock
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $OutputDirectory)) {
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
}

$collectedAtUtc = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ")
$lacunas = [System.Collections.Generic.List[string]]::new()

function Sanitize-Text {
    param([string]$InputText)
    if ([string]::IsNullOrEmpty($InputText)) { return $InputText }
    $user = $env:USERNAME
    if ($user) {
        $InputText = $InputText -replace [regex]::Escape($user), "<REDACTED_USER>"
    }
    $userProfile = $env:USERPROFILE
    if ($userProfile) {
        $InputText = $InputText -replace [regex]::Escape($userProfile), "<USERPROFILE>"
    }
    return $InputText
}

# 1. OS Information
$osData = $null
try {
    $osCim = Get-CimInstance Win32_OperatingSystem -ErrorAction Stop
    $osData = [ordered]@{
        caption = $osCim.Caption
        build_number = $osCim.BuildNumber
        total_visible_memory_kb = [int64]$osCim.TotalVisibleMemorySize
        free_physical_memory_kb = [int64]$osCim.FreePhysicalMemory
        total_virtual_memory_kb = [int64]$osCim.TotalVirtualMemorySize
        free_virtual_memory_kb = [int64]$osCim.FreeVirtualMemory
        reason_unavailable = $null
    }
}
catch {
    $lacunas.Add("Win32_OperatingSystem: $($_.Exception.Message)")
    $osData = [ordered]@{
        caption = $null
        build_number = $null
        total_visible_memory_kb = $null
        free_physical_memory_kb = $null
        total_virtual_memory_kb = $null
        free_virtual_memory_kb = $null
        reason_unavailable = $_.Exception.Message
    }
}

# 2. BIOS Information (strictly without serial numbers)
$biosData = $null
try {
    $biosCim = Get-CimInstance Win32_BIOS -ErrorAction Stop
    $biosData = [ordered]@{
        smbios_version = $biosCim.SMBIOSBIOSVersion
        manufacturer = $biosCim.Manufacturer
        release_date = if ($biosCim.ReleaseDate) { $biosCim.ReleaseDate.ToString("yyyy-MM-dd") } else { $null }
        reason_unavailable = $null
    }
}
catch {
    $lacunas.Add("Win32_BIOS: $($_.Exception.Message)")
    $biosData = [ordered]@{
        smbios_version = $null
        manufacturer = $null
        release_date = $null
        reason_unavailable = $_.Exception.Message
    }
}

# 3. Secure Boot (non-elevated read check)
$secureBootData = [ordered]@{
    enabled = $null
    reason_unavailable = $null
}
try {
    $sb = Confirm-SecureBootUEFI -ErrorAction Stop
    $secureBootData.enabled = [bool]$sb
}
catch {
    $msg = $_.Exception.Message
    $secureBootData.reason_unavailable = "Query failed without elevated privileges or unsupported: $msg"
    $lacunas.Add("SecureBoot: $msg")
}

# 4. BitLocker (non-elevated read check)
$bitlockerData = [ordered]@{
    protection_status = $null
    reason_unavailable = $null
}
try {
    $bl = Get-BitLockerVolume -MountPoint "C:" -ErrorAction Stop
    $bitlockerData.protection_status = "$($bl.ProtectionStatus)"
}
catch {
    $msg = $_.Exception.Message
    $bitlockerData.reason_unavailable = "Query failed without elevated privileges or volume not encrypted: $msg"
    $lacunas.Add("BitLocker: $msg")
}

# 5. Display Adapters via Win32_VideoController
$controllers = [System.Collections.Generic.List[object]]::new()
try {
    $vidControllers = Get-CimInstance Win32_VideoController -ErrorAction Stop
    foreach ($vc in $vidControllers) {
        $pnpId = $vc.PNPDeviceID
        # Redact specific instance path tail if needed, keeping PCI IDs
        $pnpSanitized = if ($pnpId -match "(PCI\\VEN_[0-9A-Fa-f]{4}&DEV_[0-9A-Fa-f]{4}&SUBSYS_[0-9A-Fa-f]{8}&REV_[0-9A-Fa-f]{2})") {
            $matches[1]
        } else {
            Sanitize-Text $pnpId
        }
        $controllers.Add([ordered]@{
            name = $vc.Name
            pnp_device_id = $pnpSanitized
            driver_version = $vc.DriverVersion
            adapter_ram = $vc.AdapterRAM
        })
    }
}
catch {
    $lacunas.Add("Win32_VideoController: $($_.Exception.Message)")
}

# 6. NVIDIA GPU details via nvidia-smi
$gpus = [System.Collections.Generic.List[object]]::new()
$nvidiaSmiCmd = Get-Command nvidia-smi -ErrorAction SilentlyContinue
if ($nvidiaSmiCmd) {
    try {
        $smiQuery = & nvidia-smi --query-gpu=name,pci.bus_id,pci.device_id,pci.sub_device_id,driver_version,vbios_version,memory.total,memory.used,temperature.gpu,power.limit --format=csv,noheader,nounits 2>$null
        foreach ($line in ($smiQuery -split "`r?`n")) {
            $line = $line.Trim()
            if (-not $line) { continue }
            $parts = $line.Split(",") | ForEach-Object { $_.Trim() }
            if ($parts.Count -ge 10) {
                $gpus.Add([ordered]@{
                    name = $parts[0]
                    pci_bus_id = $parts[1]
                    pci_device_id = $parts[2]
                    pci_sub_device_id = $parts[3]
                    driver_version = $parts[4]
                    vbios_version = $parts[5]
                    memory_total_mib = $parts[6]
                    memory_used_mib = $parts[7]
                    temperature_gpu_c = $parts[8]
                    power_limit = $parts[9]
                })
            }
        }
    }
    catch {
        $lacunas.Add("nvidia-smi query failed: $($_.Exception.Message)")
    }
}
else {
    $lacunas.Add("nvidia-smi not available in PATH")
}

# 7. Runtimes Inventory
$runtimes = [ordered]@{
    python = [ordered]@{
        version = $null
        path = $null
        reason_unavailable = $null
    }
    cuda_compiler = [ordered]@{
        version = $null
        reason_unavailable = $null
    }
    ollama = [ordered]@{
        version = $null
        reason_unavailable = $null
    }
    faster_whisper = [ordered]@{
        version = $null
        reason_unavailable = $null
    }
    torch = [ordered]@{
        version = $null
        cuda_available = $null
        reason_unavailable = $null
    }
}

$pyCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pyCmd) {
    try {
        $pyVer = & python --version 2>&1
        $runtimes.python.version = ($pyVer -replace "Python\s*", "").Trim()
        $runtimes.python.path = Sanitize-Text $pyCmd.Source
    }
    catch {
        $runtimes.python.reason_unavailable = $_.Exception.Message
    }
}
else {
    $runtimes.python.reason_unavailable = "python not found in PATH"
    $lacunas.Add("runtime: python")
}

$nvccCmd = Get-Command nvcc -ErrorAction SilentlyContinue
if ($nvccCmd) {
    try {
        $nvccOut = & nvcc --version 2>&1
        $runtimes.cuda_compiler.version = ($nvccOut | Select-String "release" | Out-String).Trim()
    }
    catch {
        $runtimes.cuda_compiler.reason_unavailable = $_.Exception.Message
    }
}
else {
    $runtimes.cuda_compiler.reason_unavailable = "nvcc not found in PATH (runtime only)"
    $lacunas.Add("runtime: nvcc")
}

$ollamaCmd = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaCmd) {
    try {
        $olOut = & ollama --version 2>&1
        $runtimes.ollama.version = ($olOut -replace "ollama version is\s*", "").Trim()
    }
    catch {
        $runtimes.ollama.reason_unavailable = $_.Exception.Message
    }
}
else {
    $runtimes.ollama.reason_unavailable = "ollama not found in PATH"
    $lacunas.Add("runtime: ollama")
}

# Check torch in python without downloading models
if ($pyCmd) {
    try {
        $torchCheck = & python -c "import torch; print(torch.__version__); print(torch.cuda.is_available())" 2>$null
        if ($LASTEXITCODE -eq 0 -and $torchCheck) {
            $tLines = $torchCheck -split "`r?`n"
            $runtimes.torch.version = $tLines[0].Trim()
            $runtimes.torch.cuda_available = ($tLines[1].Trim() -eq "True")
        }
        else {
            $runtimes.torch.reason_unavailable = "torch module not installed in current python environment"
            $lacunas.Add("runtime: torch")
        }
    }
    catch {
        $runtimes.torch.reason_unavailable = $_.Exception.Message
    }

    try {
        $fwCheck = & python -c "import faster_whisper; print(faster_whisper.__version__)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $fwCheck) {
            $runtimes.faster_whisper.version = $fwCheck.Trim()
        }
        else {
            $runtimes.faster_whisper.reason_unavailable = "faster_whisper module not installed in current python environment"
            $lacunas.Add("runtime: faster_whisper")
        }
    }
    catch {
        $runtimes.faster_whisper.reason_unavailable = $_.Exception.Message
    }
}

# Build Inventory Structure
$inventory = [ordered]@{
    schema_version = 1
    collected_at_utc = $collectedAtUtc
    os = $osData
    bios = $biosData
    secure_boot = $secureBootData
    bitlocker = $bitlockerData
    controllers = $controllers
    gpus = $gpus
    runtimes = $runtimes
    lacunas = $lacunas
}

$destPath = Join-Path $OutputDirectory "inventory.json"
$jsonString = $inventory | ConvertTo-Json -Depth 6
[System.IO.File]::WriteAllText($destPath, $jsonString, [System.Text.Encoding]::UTF8)

Write-Host "Diagnostics successfully written to $destPath"
