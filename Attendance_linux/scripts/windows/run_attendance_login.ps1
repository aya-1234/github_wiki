param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectDirectory
)

$ErrorActionPreference = "Stop"
$Executable = Join-Path $ProjectDirectory ".venv\Scripts\attendance-login.exe"

if (-not (Test-Path $Executable)) {
    throw "実行ファイルが見つかりません: $Executable"
}

# タスクスケジューラのプロセスは、登録後に変更されたユーザー環境変数を
# 引き継がない場合がある。実行のたびに永続設定を直接読み込む。
$UserEnvironment = [Environment]::GetEnvironmentVariables("User")
foreach ($Name in $UserEnvironment.Keys) {
    [Environment]::SetEnvironmentVariable(
        [string]$Name,
        [string]$UserEnvironment[$Name],
        "Process"
    )
}

$RequiredVariables = @(
    "CHROME_USER_DATA_DIR",
    "TARGET_ACCOUNT"
)
foreach ($Name in $RequiredVariables) {
    $Value = [Environment]::GetEnvironmentVariable($Name, "Process")
    if ([string]::IsNullOrWhiteSpace($Value)) {
        Write-Error "必須ユーザー環境変数が設定されていません: $Name"
        exit 2
    }
}

Push-Location $ProjectDirectory
try {
    & $Executable
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}
