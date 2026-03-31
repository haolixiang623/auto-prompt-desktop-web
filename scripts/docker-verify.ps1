param(
    [string]$ImageName = "auto-prompt-web:verify",
    [string]$ContainerName = "auto-prompt-web-verify",
    [int]$HostPort = 3800
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

function Invoke-Docker {
    param([string[]]$Args)
    & docker @Args
    if ($LASTEXITCODE -ne 0) {
        throw "Docker command failed: docker $($Args -join ' ')"
    }
}

function Wait-Health {
    param([string]$Url, [int]$TimeoutSeconds = 90)

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-RestMethod -Method Get -Uri $Url -TimeoutSec 5
            return $response
        } catch {
            Start-Sleep -Seconds 2
        }
    }

    throw "Timed out waiting for health endpoint: $Url"
}

try {
    Write-Host "Building image $ImageName ..."
    Invoke-Docker @("build", "-t", $ImageName, ".")

    Write-Host "Removing old container if present ..."
    & docker rm -f $ContainerName | Out-Null

    Write-Host "Starting container $ContainerName on port $HostPort ..."
    Invoke-Docker @(
        "run",
        "-d",
        "--name", $ContainerName,
        "-p", "${HostPort}:3000",
        $ImageName
    )

    $healthUrl = "http://127.0.0.1:${HostPort}/api/health"
    $health = Wait-Health -Url $healthUrl
    Write-Host "Health check passed: $($health | ConvertTo-Json -Compress)"

    $loginUrl = "http://127.0.0.1:${HostPort}/api/auth/login"
    $body = @{ username = "admin"; password = "admin123456" } | ConvertTo-Json
    $login = Invoke-RestMethod -Method Post -Uri $loginUrl -ContentType "application/json" -Body $body

    $summary = [ordered]@{
        image = $ImageName
        container = $ContainerName
        port = $HostPort
        health = $health
        login_ok = [bool]($login.token)
        user = $login.user
    }

    Write-Host "Verification summary:"
    $summary | ConvertTo-Json -Depth 8
} catch {
    Write-Error $_
    throw
}
