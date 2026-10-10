# ============================================================
# QQBot 安全更新脚本
# 用途：更新程序本体（QQBot.exe + _internal），
#       绝不触碰用户配置（config/ data/ stickers/ .env 等）
# 用法：powershell -ExecutionPolicy Bypass -File build.ps1
# ============================================================
param([string]$Target = "dist_final")

$proj = "C:\Users\单长宇\Python项目\qqbot-v3"
Set-Location $proj

Write-Output "== 1/6 关闭运行中的 QQBot =="
Get-Process QQBot -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Sleep -Seconds 2

$final  = Join-Path $proj "$Target\QQBot"
$backup = Join-Path $proj "$Target\QQBot_userdata_backup"

# 用户配置目录（重打包重建目录时，用这份备份恢复）
$userDirs = @("config", "data", "stickers", "logs")

Write-Output "== 2/6 备份当前用户配置 =="
if (Test-Path $final) {
    if (Test-Path $backup) { Remove-Item $backup -Recurse -Force }
    New-Item -ItemType Directory -Path $backup -Force | Out-Null
    foreach ($d in $userDirs) {
        if (Test-Path (Join-Path $final $d)) {
            Copy-Item (Join-Path $final $d) $backup -Recurse -Force
            Write-Output "  备份 $d"
        }
    }
    if (Test-Path (Join-Path $final ".env")) {
        Copy-Item (Join-Path $final ".env") $backup -Force
        Write-Output "  备份 .env"
    }
}

Write-Output "== 3/6 打包到全新目录（不碰现有部署） =="
& "C:\yuzhuang\Anaconda\python.exe" -m PyInstaller --noconfirm --clean --windowed --name QQBot --icon icon.ico --distpath dist_new --exclude-module PySide6.QtNetwork --exclude-module PySide6.QtWebEngineCore --exclude-module PySide6.QtWebEngineWidgets --exclude-module PySide6.QtWebChannel --exclude-module PySide6.QtMultimedia --exclude-module PySide6.QtQml --exclude-module PySide6.QtQuick --exclude-module PySide6.QtSvg --exclude-module PySide6.QtTest --exclude-module PySide6.QtSql main.py
if ($LASTEXITCODE -ne 0) { Write-Output "❌ 打包失败，中止（现有部署未受影响）"; exit 1 }

$new = Join-Path $proj "dist_new\QQBot"
if (-not (Test-Path (Join-Path $new "QQBot.exe"))) {
    Write-Output "❌ 打包产物缺失，中止"; exit 1
}

Write-Output "== 4/6 只替换程序本体 =="
if (-not (Test-Path $final)) { New-Item -ItemType Directory -Path $final -Force | Out-Null }
Copy-Item (Join-Path $new "QQBot.exe") $final -Force
if (Test-Path "$final\_internal") { Remove-Item "$final\_internal" -Recurse -Force }
Copy-Item (Join-Path $new "_internal") $final -Recurse -Force
Write-Output "  已替换 QQBot.exe + _internal"

Write-Output "== 5/6 恢复用户配置（仅补缺失项，绝不覆盖已有） =="
foreach ($d in $userDirs) {
    if (-not (Test-Path (Join-Path $final $d))) {
        if (Test-Path (Join-Path $backup $d)) {
            Copy-Item (Join-Path $backup $d) $final -Recurse -Force
            Write-Output "  恢复 $d"
        }
    } else {
        Write-Output "  $d 已存在，保留"
    }
}
if (-not (Test-Path (Join-Path $final ".env"))) {
    if (Test-Path (Join-Path $backup ".env")) {
        Copy-Item (Join-Path $backup ".env") $final -Force
        Write-Output "  恢复 .env"
    }
}

Write-Output "== 6/6 清理临时目录 =="
Remove-Item (Join-Path $proj "dist_new") -Recurse -Force -ErrorAction SilentlyContinue

Write-Output "✅ 更新完成：程序已替换，用户配置原样保留（$final）"
