# test_runner.ps1 - Test suite for Run-Workload.ps1
$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$runnerScript = Join-Path (Split-Path -Parent $scriptDir) "Run-Workload.ps1"

Write-Host "Running tests for Run-Workload.ps1..."

if (-not (Test-Path $runnerScript)) {
    Write-Error "FAIL: Run-Workload.ps1 not found at $runnerScript"
    exit 1
}

$tmpDir = Join-Path ([System.IO.Path]::GetTempPath()) ("runner_test_" + [Guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tmpDir -Force | Out-Null

try {
    # Test 1: Invalid State parameter rejected
    $invalidStatePassed = $false
    try {
        & $runnerScript -CaseFile "nonexistent.json" -State "INVALID" -OutputDirectory (Join-Path $tmpDir "out1") 2>$null
        $invalidStatePassed = $true
    } catch {
        # Expected
    }
    if ($invalidStatePassed) {
        Write-Error "FAIL: Expected validation error on invalid state"
        exit 1
    }
    Write-Host "PASS: Invalid State rejected by parameter validation."

    # Test 2: Successful mock run writes complete.json
    $case1Path = Join-Path $tmpDir "case_success.json"
    @{
        workload_name = "test_mock_success"
        protocol_version = 1
        executable = "powershell.exe"
        arguments = @("-NoProfile", "-Command", "Write-Output 'HELLO_BENCHMARK_OK'")
        expected_stdout_regex = "HELLO_BENCHMARK_OK"
        timeout_seconds = 10
    } | ConvertTo-Json | Set-Content -LiteralPath $case1Path -Encoding utf8

    $outSuccess = Join-Path $tmpDir "out_success"
    & $runnerScript -CaseFile $case1Path -State "A" -OutputDirectory $outSuccess

    $completeFile = Join-Path $outSuccess "complete.json"
    if (-not (Test-Path -LiteralPath $completeFile)) {
        Write-Error "FAIL: complete.json was not created on successful run"
        exit 1
    }
    $completeData = Get-Content -LiteralPath $completeFile -Raw | ConvertFrom-Json
    if ($completeData.quality_pass -ne $true -or $completeData.exit_code -ne 0) {
        Write-Error "FAIL: complete.json does not reflect quality_pass == true"
        exit 1
    }
    Write-Host "PASS: Successful run generates complete.json and validates quality."

    # Test 3: Non-zero exit code does NOT write complete.json
    $case2Path = Join-Path $tmpDir "case_fail.json"
    @{
        workload_name = "test_mock_fail"
        protocol_version = 1
        executable = "powershell.exe"
        arguments = @("-NoProfile", "-Command", "exit 42")
        timeout_seconds = 10
    } | ConvertTo-Json | Set-Content -LiteralPath $case2Path -Encoding utf8

    $outFail = Join-Path $tmpDir "out_fail"
    & $runnerScript -CaseFile $case2Path -State "A" -OutputDirectory $outFail
    if (Test-Path -LiteralPath (Join-Path $outFail "complete.json")) {
        Write-Error "FAIL: complete.json was written despite non-zero exit code"
        exit 1
    }
    Write-Host "PASS: Non-zero exit code prevents complete.json emission."

    # Test 4: Quality regex mismatch does NOT write complete.json
    $case3Path = Join-Path $tmpDir "case_regex_fail.json"
    @{
        workload_name = "test_mock_regex_fail"
        protocol_version = 1
        executable = "powershell.exe"
        arguments = @("-NoProfile", "-Command", "Write-Output 'UNEXPECTED_OUTPUT'")
        expected_stdout_regex = "EXPECTED_STRING_NEVER_FOUND"
        timeout_seconds = 10
    } | ConvertTo-Json | Set-Content -LiteralPath $case3Path -Encoding utf8

    $outRegexFail = Join-Path $tmpDir "out_regex_fail"
    & $runnerScript -CaseFile $case3Path -State "A" -OutputDirectory $outRegexFail
    if (Test-Path -LiteralPath (Join-Path $outRegexFail "complete.json")) {
        Write-Error "FAIL: complete.json was written despite quality check failure"
        exit 1
    }
    Write-Host "PASS: Quality check failure prevents complete.json emission."

    # Test 5: Timeout terminates process and raises error
    $case4Path = Join-Path $tmpDir "case_timeout.json"
    @{
        workload_name = "test_mock_timeout"
        protocol_version = 1
        executable = "powershell.exe"
        arguments = @("-NoProfile", "-Command", "Start-Sleep -Seconds 15")
        timeout_seconds = 2
    } | ConvertTo-Json | Set-Content -LiteralPath $case4Path -Encoding utf8

    $outTimeout = Join-Path $tmpDir "out_timeout"
    $timeoutRaised = $false
    try {
        & $runnerScript -CaseFile $case4Path -State "A" -OutputDirectory $outTimeout
    } catch {
        $timeoutRaised = $true
    }
    if (-not $timeoutRaised) {
        Write-Error "FAIL: Timeout did not raise expected exception"
        exit 1
    }
    if (Test-Path -LiteralPath (Join-Path $outTimeout "complete.json")) {
        Write-Error "FAIL: complete.json was written despite timeout"
        exit 1
    }
    Write-Host "PASS: Timeout enforcement verified."

} finally {
    Remove-Item -Recurse -Force $tmpDir -ErrorAction SilentlyContinue
}

Write-Host "All test_runner.ps1 tests PASSED."
exit 0
