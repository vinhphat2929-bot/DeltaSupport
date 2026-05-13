param([string]$LogPath)
Add-Content -LiteralPath $LogPath -Value "started $(Get-Date -Format o)"
