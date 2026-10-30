# test_diagnostics.ps1 - Tests for Collect-Diagnostics.ps1
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$collectorScript = Join-Path (Split-Path -Parent $scriptDir) "Collect-Diagnostics.ps1"

Write-Host "Running tests for Collect-Diagnostics.ps1..."

# Test 1: File exists
if (-not (Test-Path $collectorScript)) {
    Write-Error "FAIL: Collect-Diagnostics.ps1 not found at $collectorScript"
    exit 1
}

# Test 2: Execution with OutputDirectory produces valid inventory.json
$testOutDir = Join-Path ([System.IO.Path]::GetTempPath()) ("gpu_diag_test_" + [Guid]::NewGuid().ToString("N"))
try {
    & $collectorScript -OutputDirectory $testOutDir
    $inventoryPath = Join-Path $testOutDir "inventory.json"
    if (-not (Test-Path $inventoryPath)) {
        Write-Error "FAIL: inventory.json was not created in output directory"
        exit 1
    }

    $rawJson = Get-Content -Raw -Path $inventoryPath
    $data = $rawJson | ConvertFrom-Json

    # Check schema version
    if ($data.schema_version -ne 1) {
        Write-Error "FAIL: schema_version ($($data.schema_version)) != 1"
        exit 1
    }

    # Check timestamp format
    if (-not $data.collected_at_utc -or -not ($data.collected_at_utc -match "^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")) {
        Write-Error "FAIL: collected_at_utc is missing or not ISO8601"
        exit 1
    }

    # Check redaction: username must not appear anywhere in the JSON
    $currentUser = $env:USERNAME
    if ($currentUser -and $rawJson.Contains($currentUser)) {
        Write-Error "FAIL: Redaction check failed: current username '$currentUser' found in inventory.json"
        exit 1
    }

    # Check redaction: serial numbers or MAC-like UUIDs shouldn't be leaked
    if ($data.bios.serial_number) {
        Write-Error "FAIL: BIOS serial number must not be included"
        exit 1
    }

    # Check fields are present
    if ($null -eq $data.os) {
        Write-Error "FAIL: os section missing"
        exit 1
    }

    if ($null -eq $data.gpus) {
        Write-Error "FAIL: gpus section missing"
        exit 1
    }

    if ($null -eq $data.lacunas) {
        Write-Error "FAIL: lacunas section missing"
        exit 1
    }

    Write-Host "PASS: Basic inventory generation, schema and redaction verified."
}
finally {
    if (Test-Path $testOutDir) {
        Remove-Item -Recurse -Force $testOutDir -ErrorAction SilentlyContinue
    }
}

Write-Host "All test_diagnostics.ps1 tests PASSED."
exit 0
