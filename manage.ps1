param (
    [string]$Command
)

$DockerComposeFile = "docker/docker-compose.yml"

function Show-Usage {
    Write-Host "Usage: .\manage.ps1 <command>"
    Write-Host "Commands:"
    Write-Host "  dev   - Start development environment (docker-compose up)"
    Write-Host "  down  - Stop development environment (docker-compose down)"
    Write-Host "  test  - Run backend tests"
}

if ([string]::IsNullOrEmpty($Command)) {
    Show-Usage
    exit 1
}

switch ($Command) {
    "dev" {
        Write-Host "Starting development environment..."
        docker-compose -f $DockerComposeFile up --build
    }
    "down" {
        Write-Host "Stopping development environment..."
        docker-compose -f $DockerComposeFile down
    }
    "test" {
        Write-Host "Running backend tests..."
        docker-compose -f $DockerComposeFile run backend pytest
    }
    default {
        Write-Host "Unknown command: $Command"
        Show-Usage
        exit 1
    }
}
