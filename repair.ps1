$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Python = if ($env:PYTHON) { $env:PYTHON } else { Join-Path $Root '.venv\Scripts\python.exe' }
if (-not (Test-Path $Python)) { $Python = 'python' }
$Report = Join-Path $Root 'logs\startup-report.txt'

$EnvFile = Join-Path $Root '.env'
if (Test-Path $EnvFile) {
    foreach ($Line in Get-Content $EnvFile) {
        $Trimmed = $Line.Trim()
        if (-not $Trimmed -or $Trimmed.StartsWith('#') -or $Trimmed -notmatch '=') { continue }
        $Parts = $Trimmed -split '=', 2
        $Name = $Parts[0].Trim()
        $Value = $Parts[1].Trim()
        if ($Value.Length -ge 2 -and (($Value.StartsWith('"') -and $Value.EndsWith('"')) -or ($Value.StartsWith("'") -and $Value.EndsWith("'")))) {
            $Value = $Value.Substring(1, $Value.Length - 2)
        }
        [Environment]::SetEnvironmentVariable($Name, $Value, 'Process')
    }
}

function Test-InternetService([string]$Label, [string]$Uri, [hashtable]$Headers = @{}) {
    try {
        $Response = Invoke-WebRequest -Uri $Uri -Headers $Headers -TimeoutSec 10 -UseBasicParsing
        if ($Response.StatusCode -ge 200 -and $Response.StatusCode -lt 300) {
            Write-Host "[OK] $Label (HTTP $($Response.StatusCode))"
        } else {
            Write-Host "[SKIP] $Label (HTTP $($Response.StatusCode))"
        }
    } catch {
        $Status = if ($_.Exception.Response) { [int]$_.Exception.Response.StatusCode } else { 000 }
        Write-Host "[SKIP] $Label (HTTP $Status)"
    }
}

function Test-InternetServices {
    Write-Host "`nInternet service checks"
    Test-InternetService 'Discord internet access' 'https://discord.com/api/v10/gateway'
    if ($env:SUPERCELL_ROYALE_API) { Test-InternetService 'Supercell Clash Royale' 'https://proxy.royaleapi.dev/v1/locations' @{ Authorization = "Bearer $env:SUPERCELL_ROYALE_API" } }
    if ($env:SUPERCELL_COC_API) { Test-InternetService 'Supercell Clash of Clans' 'https://cocproxy.royaleapi.dev/v1/locations' @{ Authorization = "Bearer $env:SUPERCELL_COC_API" } }
    if ($env:SUPERCELL_BRAWL_STARS_API) { Test-InternetService 'Supercell Brawl Stars' 'https://bsproxy.royaleapi.dev/v1/locations' @{ Authorization = "Bearer $env:SUPERCELL_BRAWL_STARS_API" } }
    if ($env:NEWS_API_KEY) { Test-InternetService 'News API' 'https://newsapi.org/v2/top-headlines?country=us&pageSize=1' @{ 'X-Api-Key' = $env:NEWS_API_KEY } }
    if ($env:NASA_API_KEY) { Test-InternetService 'NASA API' "https://api.nasa.gov/planetary/apod?api_key=$env:NASA_API_KEY" }
    if ($env:OPEN_WEATHER_API_KEY) { Test-InternetService 'OpenWeather API' "https://api.openweathermap.org/data/2.5/weather?q=London&appid=$env:OPEN_WEATHER_API_KEY" }
    if ($env:IMAGE_FLIP_KEY) { Test-InternetService 'Imgflip API' 'https://api.imgflip.com/get_memes' @{ Authorization = "Bearer $env:IMAGE_FLIP_KEY" } }
}

function Show-Report {
    if (Test-Path $Report) {
        Write-Host "`nStartup report"
        Get-Content $Report
    } else {
        Write-Host "`nNo startup report found yet."
    }
}

function Install-Group([string]$Label, [string[]]$Packages) {
    Write-Host "`nInstalling $Label..."
    & $Python -m pip install @Packages
}

function Set-EnvValue([string]$Name, [bool]$Secret) {
    if ($Secret) {
        $SecureValue = Read-Host "Enter $Name (hidden, leave blank to skip)" -AsSecureString
        $Bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecureValue)
        try { $Value = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($Bstr) }
        finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($Bstr) }
    } else {
        $Value = Read-Host "Enter $Name (leave blank to skip)"
    }

    if (-not $Value) { return }
    $EnvFile = Join-Path $Root '.env'
    $Lines = if (Test-Path $EnvFile) { @(Get-Content $EnvFile) } else { @() }
    $Pattern = '^' + [regex]::Escape($Name) + '='
    $Lines = @($Lines | Where-Object { $_ -notmatch $Pattern })
    $Lines += "$Name=$Value"
    Set-Content -Path $EnvFile -Value $Lines -Encoding utf8
    Write-Host "$Name was written to .env."
}

function Configure-Discord { Set-EnvValue 'DISCORD_BOT_TOKEN' $true }
function Configure-Database {
    Set-EnvValue 'MONGO_URI' $true
    Set-EnvValue 'REDIS_HOST' $false
    Set-EnvValue 'REDIS_PORT' $false
}
function Configure-Lavalink { Set-EnvValue 'LAVALINK_PASSWORD' $true }
function Configure-Supercell {
    Set-EnvValue 'SUPERCELL_ROYALE_API' $true
    Set-EnvValue 'SUPERCELL_COC_API' $true
    Set-EnvValue 'SUPERCELL_BRAWL_STARS_API' $true
}
function Configure-ApiKeys {
    Set-EnvValue 'NEWS_API_KEY' $true
    Set-EnvValue 'NASA_API_KEY' $true
    Set-EnvValue 'OPEN_WEATHER_API_KEY' $true
    Set-EnvValue 'IMAGE_FLIP_KEY' $true
}

Show-Report
Write-Host "`nChoose a repair action:"
Write-Host '  1) Configure Discord bot token'
Write-Host '  2) Install and configure MongoDB/Redis support'
Write-Host '  3) Install and configure Lavalink support'
Write-Host '  4) Configure all Supercell API keys'
Write-Host '  5) Configure News/NASA/Weather/Imgflip API keys'
Write-Host '  6) Install Jishaku and autoreload support'
Write-Host '  7) Install the full requirements file'
Write-Host '  8) Re-run the package/configuration audit'
Write-Host '  0) Exit'
$Choice = Read-Host 'Selection'

switch ($Choice) {
    '1' { Configure-Discord }
    '2' { Install-Group 'database and cache support' @('pymongo', 'redis[hiredis]'); Configure-Database }
    '3' { Install-Group 'music support' @('pomice'); Configure-Lavalink }
    '4' { Configure-Supercell }
    '5' { Configure-ApiKeys }
    '6' { Install-Group 'developer support' @('jishaku[procinfo]', 'watchfiles') }
    '7' { & $Python -m pip install -r (Join-Path $Root 'requirements.txt') }
    '8' { }
    '0' { exit 0 }
    default { Write-Error 'Unknown selection.' }
}

& $Python -c 'from pathlib import Path; from core.startup import audit_startup; audit_startup(Path("logs/startup-report.txt"))'
Show-Report
Test-InternetServices
