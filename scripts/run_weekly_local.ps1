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
