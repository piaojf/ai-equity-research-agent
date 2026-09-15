param([Parameter(Mandatory=$true)][string]$Target,[Parameter(Mandatory=$true)][string]$Backup)
Copy-Item -LiteralPath $Backup -Destination $Target -Force
$hash=(Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash
Write-Output "RESTORED_SHA256=$hash"
