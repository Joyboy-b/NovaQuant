param([switch]$ReverseOrder)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    $benchPython = Join-Path $projectRoot '.venv-bench\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $benchPython)) {
        throw 'Create .venv-bench and install requirements-benchmark.txt first; see docs/PYPERF_NATIVE.md.'
    }
    & "$PSScriptRoot\build_benchmark_windows.cmd"
    if ($LASTEXITCODE -ne 0) { throw 'Native DLL build failed' }
    $runDirectory = Join-Path $projectRoot ('artifacts\pyperf-native-' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
    New-Item -ItemType Directory -Path $runDirectory | Out-Null
    $variants = if ($ReverseOrder) { @('after','before') } else { @('before','after') }
    foreach ($variant in $variants) {
        & $benchPython scripts/benchmark_pyperf.py --adapter $variant -o (Join-Path $runDirectory "$variant.json")
        if ($LASTEXITCODE -ne 0) { throw "$variant benchmark failed" }
    }
    & $benchPython -m pyperf compare_to (Join-Path $runDirectory 'before.json') (Join-Path $runDirectory 'after.json') --table | Tee-Object -FilePath (Join-Path $runDirectory 'comparison.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Comparison failed' }
    & $benchPython -m pyperf check (Join-Path $runDirectory 'before.json') (Join-Path $runDirectory 'after.json') | Tee-Object -FilePath (Join-Path $runDirectory 'stability.txt')
    Write-Host "Results saved to $runDirectory"
} finally {
    Pop-Location
}
