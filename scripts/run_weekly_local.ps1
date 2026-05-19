# MYP Weekly Local Scan — rodado via Windows Task Scheduler
# Triggered: domingo 01:00 BRT (04:00 UTC). ETA ~6h single-thread.
# Output: C:\Users\mathe\Downloads\myp_weekly_YYYYMMDD_HHmm.xlsx
# Log: C:\Users\mathe\Downloads\myp_weekly_YYYYMMDD_HHmm.log
#
# Manual run: powershell -ExecutionPolicy Bypass -File run_weekly_local.ps1

$ErrorActionPreference = "Continue"
$env:PYTHONIOENCODING = "utf-8"

$scannerDir = "C:\Users\mathe\myp-arbitrage-scanner"
$downloadsDir = "C:\Users\mathe\Downloads"
$stamp = Get-Date -Format "yyyyMMdd_HHmm"
$xlsxPath = "$downloadsDir\myp_weekly_${stamp}.xlsx"
$logPath = "$downloadsDir\myp_weekly_${stamp}.log"

Set-Location $scannerDir

# Header no log
"=== MYP Weekly Local Scan ===" | Tee-Object -FilePath $logPath
"Start: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Tee-Object -FilePath $logPath -Append
"Output XLSX: $xlsxPath" | Tee-Object -FilePath $logPath -Append
"" | Tee-Object -FilePath $logPath -Append

# Auto-pull origin/main pra garantir scanner mais novo em producao.
# Task Scheduler senao roda whatever esta no working tree mesmo com commits novos no remote.
"[wrapper] Fetching origin/main..." | Tee-Object -FilePath $logPath -Append
git fetch origin main --quiet 2>&1 | Tee-Object -FilePath $logPath -Append
if ($LASTEXITCODE -ne 0) {
    "[wrapper] WARN: git fetch failed (offline?) - continuing with working tree (may be stale)" | Tee-Object -FilePath $logPath -Append
} else {
    $behindCount = (git rev-list --count HEAD..origin/main 2>$null).Trim()
    if ($behindCount -and ([int]$behindCount -gt 0)) {
        "[wrapper] Behind origin/main by $behindCount commit(s) - pulling..." | Tee-Object -FilePath $logPath -Append
        git pull --ff-only origin main 2>&1 | Tee-Object -FilePath $logPath -Append
        if ($LASTEXITCODE -ne 0) {
            "[wrapper] ERROR: git pull --ff-only failed (divergent local commits?) - aborting to avoid running stale code" | Tee-Object -FilePath $logPath -Append
            exit 1
        }
    } else {
        "[wrapper] Already up to date with origin/main" | Tee-Object -FilePath $logPath -Append
    }
}
"" | Tee-Object -FilePath $logPath -Append

# Rodar scanner — params idênticos ao GH Actions weekly default
python myp_arbitrage_scanner.py `
    --threshold 25 `
    --min-price 80 `
    --delay 1.5 `
    --output $xlsxPath 2>&1 | Tee-Object -FilePath $logPath -Append

$exitCode = $LASTEXITCODE

"" | Tee-Object -FilePath $logPath -Append
"End: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" | Tee-Object -FilePath $logPath -Append
"Exit code: $exitCode" | Tee-Object -FilePath $logPath -Append

exit $exitCode
