param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectDirectory,

    [Parameter(Mandatory = $true)]
    [ValidatePattern("^\d{2}:\d{2}$")]
    [string]$DailyAt,

    [string]$TaskName = "AttendanceLogin"
)

$ErrorActionPreference = "Stop"
$ResolvedProjectDirectory = (
    Resolve-Path -LiteralPath $ProjectDirectory
).Path
$Runner = Join-Path `
    $ResolvedProjectDirectory `
    "scripts\run_attendance_login.ps1"
$PowerShellExecutable = Join-Path `
    $env:SystemRoot `
    "System32\WindowsPowerShell\v1.0\powershell.exe"

if (-not (Test-Path $Runner)) {
    throw "実行スクリプトが見つかりません: $Runner"
}
if (-not (Test-Path $PowerShellExecutable)) {
    throw "PowerShellが見つかりません: $PowerShellExecutable"
}

$Action = New-ScheduledTaskAction `
    -Execute $PowerShellExecutable `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$Runner`" -ProjectDirectory `"$ResolvedProjectDirectory`"" `
    -WorkingDirectory $ResolvedProjectDirectory
$Trigger = New-ScheduledTaskTrigger -Daily -At $DailyAt
$Settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$CurrentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$Principal = New-ScheduledTaskPrincipal `
    -UserId $CurrentUser `
    -LogonType Interactive `
    -RunLevel Limited

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Salesforce勤怠管理システム自動入力" `
    -Force
