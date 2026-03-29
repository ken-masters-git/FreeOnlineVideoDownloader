$ErrorActionPreference = "Stop"

$workspace = (Resolve-Path (Split-Path -Parent $MyInvocation.MyCommand.Path)).Path
Set-Location $workspace

function Resolve-WorkspacePath {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $absolutePath = [System.IO.Path]::GetFullPath((Join-Path $workspace $RelativePath))
    if (-not $absolutePath.StartsWith($workspace, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to operate outside the workspace: $RelativePath"
    }
    return $absolutePath
}

function Remove-WorkspaceItem {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath
    )

    $absolutePath = Resolve-WorkspacePath -RelativePath $RelativePath
    if (Test-Path -LiteralPath $absolutePath) {
        Remove-Item -LiteralPath $absolutePath -Recurse -Force
        Write-Output "Removed: $RelativePath"
    } else {
        Write-Output "Skipped: $RelativePath"
    }
}

$targets = @(
    "build\FreeOnlineVideoDownloader",
    "build\YouTubeVideoDownloader",
    "dist\FreeOnlineVideoDownloader.exe",
    "dist\YouTubeVideoDownloader.exe",
    "dist\self_test_detect.txt",
    "dist\self_test_detect_v2.txt",
    "dist\self_test_subtitles.txt",
    "__pycache__"
)

foreach ($target in $targets) {
    Remove-WorkspaceItem -RelativePath $target
}

$buildRoot = Resolve-WorkspacePath -RelativePath "build"
if (Test-Path -LiteralPath $buildRoot) {
    $remainingBuildEntries = Get-ChildItem -LiteralPath $buildRoot -Force
    if ($remainingBuildEntries.Count -eq 0) {
        Remove-Item -LiteralPath $buildRoot -Force
        Write-Output "Removed: build"
    }
}
