$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $workspace

$pyInstallerSite = Resolve-Path ".pyinstaller_vendor"

$iconFile = Resolve-Path "assets\free_online_video_downloader.ico"
$ffmpegRoot = Join-Path $workspace "tools\ffmpeg"
$ffmpegExe = Get-ChildItem -Path $ffmpegRoot -Filter "ffmpeg.exe" -Recurse -File |
  Select-Object -First 1
$ffprobeExe = Get-ChildItem -Path $ffmpegRoot -Filter "ffprobe.exe" -Recurse -File |
  Select-Object -First 1

if (-not $ffmpegExe -or -not $ffprobeExe) {
  throw "Could not find ffmpeg.exe and ffprobe.exe under $ffmpegRoot. Download and extract an FFmpeg build into tools\\ffmpeg first."
}

python -c "import sys; sys.path.insert(0, r'$workspace\.vendor'); sys.path.insert(0, r'$($pyInstallerSite.Path)'); import PyInstaller.__main__ as p; p.run(sys.argv[1:])" `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name "FreeOnlineVideoDownloader" `
  --icon "$($iconFile.Path)" `
  --paths "$workspace\.vendor" `
  --collect-all yt_dlp `
  --add-data "$workspace\assets;assets" `
  --add-data "$($ffmpegExe.FullName);tools\ffmpeg\bin" `
  --add-data "$($ffprobeExe.FullName);tools\ffmpeg\bin" `
  free_online_video_downloader_gui.py

if ($LASTEXITCODE -ne 0) {
  throw "PyInstaller build failed with exit code $LASTEXITCODE."
}
