# Run-Workload.ps1 - Isolated workload execution and telemetry capture
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$CaseFile,

    [Parameter(Mandatory = $true)]
    [ValidateSet("A", "C", "B")]
    [string]$State,

    [Parameter(Mandatory = $true)]
    [string]$OutputDirectory
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $CaseFile)) {
    throw "CaseFile not found: $CaseFile"
}

if (-not (Test-Path -LiteralPath $OutputDirectory)) {
    New-Item -ItemType Directory -Path $OutputDirectory -Force | Out-Null
}

# 1. Parse Case Configuration without evaluating arbitrary code
$caseContent = Get-Content -LiteralPath $CaseFile -Raw -Encoding utf8
$caseJson = $caseContent | ConvertFrom-Json

if (-not $caseJson.workload_name) { throw "Missing 'workload_name' in case file" }
if (-not $caseJson.executable) { throw "Missing 'executable' in case file" }
if ($null -eq $caseJson.arguments) { throw "Missing 'arguments' array in case file" }

$protocolVersion = if ($caseJson.protocol_version) { [int]$caseJson.protocol_version } else { 1 }
$timeoutSec = if ($caseJson.timeout_seconds) { [int]$caseJson.timeout_seconds } else { 120 }
$exePath = $caseJson.executable

# Resolve executable path to prevent PATH hijacking
$resolvedCmd = Get-Command $exePath -ErrorAction SilentlyContinue
if (-not $resolvedCmd) {
    throw "Executable '$exePath' could not be resolved or found in system PATH"
}
$resolvedExePath = $resolvedCmd.Source

# Compute SHA256 hashes of inputs
$caseHash = (Get-FileHash -LiteralPath $CaseFile -Algorithm SHA256).Hash
$exeHash = if (Test-Path -LiteralPath $resolvedExePath) {
    (Get-FileHash -LiteralPath $resolvedExePath -Algorithm SHA256).Hash
} else { "RESOLVED_SYSTEM_COMMAND" }

$stdoutFile = Join-Path $OutputDirectory "stdout.txt"
$stderrFile = Join-Path $OutputDirectory "stderr.txt"
$telemetryFile = Join-Path $OutputDirectory "gpu-telemetry.csv"

# Pre-run GPU telemetry snapshot
$hasNvidiaSmi = [bool](Get-Command nvidia-smi -ErrorAction SilentlyContinue)
if ($hasNvidiaSmi) {
    try {
        & nvidia-smi --query-gpu=timestamp,name,pci.bus_id,driver_version,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw,clocks.sm --format=csv |
            Set-Content -LiteralPath $telemetryFile -Encoding utf8
    } catch {
        # Telemetry is non-fatal if GPU is not available
    }
}

# 2. Launch Process with direct argument passing (NO Invoke-Expression)
$argList = @($caseJson.arguments | ForEach-Object { [string]$_ })

$startUtc = [DateTime]::UtcNow
$sw = [System.Diagnostics.Stopwatch]::StartNew()

$pinfo = New-Object System.Diagnostics.ProcessStartInfo
$pinfo.FileName = $resolvedExePath
$pinfo.UseShellExecute = $false
$pinfo.RedirectStandardOutput = $true
$pinfo.RedirectStandardError = $true
$pinfo.CreateNoWindow = $true

if ($pinfo.PSObject.Properties['ArgumentList'] -and $pinfo.ArgumentList -ne $null) {
    foreach ($a in $argList) {
        $pinfo.ArgumentList.Add($a)
    }
} else {
    $escaped = @(foreach ($a in $argList) {
        if ($a -match '[\s"]') {
            '"' + ($a -replace '(\\*)"', '$1$1\"' -replace '(\\+)$', '$1$1') + '"'
        } else {
            $a
        }
    }) -join ' '
    $pinfo.Arguments = $escaped
}

$proc = New-Object System.Diagnostics.Process
$proc.StartInfo = $pinfo

[void]$proc.Start()
$stdOutTask = $proc.StandardOutput.ReadToEndAsync()
$stdErrTask = $proc.StandardError.ReadToEndAsync()

$completedInTime = $proc.WaitForExit($timeoutSec * 1000)
$sw.Stop()
$endUtc = [DateTime]::UtcNow
$durationSec = $sw.Elapsed.TotalSeconds

if (-not $completedInTime) {
    try {
        $proc.Kill()
    } catch {}
    [System.IO.File]::WriteAllText($stdoutFile, "", [System.Text.Encoding]::UTF8)
    [System.IO.File]::WriteAllText($stderrFile, "TIMEOUT exceeded ($timeoutSec s)", [System.Text.Encoding]::UTF8)
    throw "Process timed out after $timeoutSec seconds and was terminated"
}

$stdOutText = $stdOutTask.Result
$stdErrText = $stdErrTask.Result

[System.IO.File]::WriteAllText($stdoutFile, $stdOutText, [System.Text.Encoding]::UTF8)
[System.IO.File]::WriteAllText($stderrFile, $stdErrText, [System.Text.Encoding]::UTF8)

$exitCode = $proc.ExitCode

# Post-run GPU telemetry snapshot
if ($hasNvidiaSmi) {
    try {
        & nvidia-smi --query-gpu=timestamp,name,pci.bus_id,driver_version,temperature.gpu,utilization.gpu,memory.used,memory.total,power.draw,clocks.sm --format=csv,noheader |
            Add-Content -LiteralPath $telemetryFile -Encoding utf8
    } catch {}
}

# 3. Quality Validation Check
$qualityPass = ($exitCode -eq 0)
$qualityReason = ""

if ($caseJson.expected_stdout_regex) {
    $outText = $stdOutText
    if (-not ($outText -match $caseJson.expected_stdout_regex)) {
        $qualityPass = $false
        $qualityReason = "Stdout did not match expected regex: $($caseJson.expected_stdout_regex)"
    }
}

# 4. Context Metadata
$context = [ordered]@{
    workload_name = $caseJson.workload_name
    protocol_version = $protocolVersion
    executable_sha256 = $exeHash
    case_file_sha256 = $caseHash
    state = $State
}

$runMeta = [ordered]@{
    workload_name = $caseJson.workload_name
    state = $State
    exit_code = $exitCode
    start_utc = $startUtc.ToString("o")
    end_utc = $endUtc.ToString("o")
    duration_seconds = $durationSec
    quality_pass = $qualityPass
    quality_reason = $qualityReason
    context = $context
}

$runMetaJson = $runMeta | ConvertTo-Json -Depth 5
[System.IO.File]::WriteAllText((Join-Path $OutputDirectory "run-meta.json"), $runMetaJson, [System.Text.Encoding]::UTF8)

# 5. Write complete.json ONLY if exit_code == 0 and qualityPass == true
if ($exitCode -eq 0 -and $qualityPass) {
    $completeData = [ordered]@{
        schema_version = 1
        workload_name = $caseJson.workload_name
        state = $State
        exit_code = $exitCode
        metric_name = "duration_seconds"
        metric_value = [double]$durationSec
        quality_pass = $true
        context = $context
        artifacts = @(
            [ordered]@{ Path = "stdout.txt"; SHA256 = (Get-FileHash -LiteralPath $stdoutFile -Algorithm SHA256).Hash }
            [ordered]@{ Path = "run-meta.json"; SHA256 = (Get-FileHash -LiteralPath (Join-Path $OutputDirectory "run-meta.json") -Algorithm SHA256).Hash }
        )
    }
    $completeJson = $completeData | ConvertTo-Json -Depth 5
    [System.IO.File]::WriteAllText((Join-Path $OutputDirectory "complete.json"), $completeJson, [System.Text.Encoding]::UTF8)
    Write-Host "Workload '$($caseJson.workload_name)' completed successfully in $([math]::Round($durationSec, 3))s (State: $State)"
} else {
    Write-Warning "Workload '$($caseJson.workload_name)' FAILED (ExitCode: $exitCode, QualityPass: $qualityPass, Reason: $qualityReason). complete.json was NOT created."
}
