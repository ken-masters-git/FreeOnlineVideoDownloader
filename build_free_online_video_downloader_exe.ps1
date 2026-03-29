$ErrorActionPreference = "Stop"

$workspace = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $workspace

$pyInstallerSite = Resolve-Path ".pyinstaller_vendor"

$iconFile = Resolve-Path "assets\free_online_video_downloader.ico"
$ffmpegExe = Resolve-Path "tools\ffmpeg\ffmpeg-8.1-essentials_build\bin\ffmpeg.exe"
$ffprobeExe = Resolve-Path "tools\ffmpeg\ffmpeg-8.1-essentials_build\bin\ffprobe.exe"

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
  --add-data "$($ffmpegExe.Path);tools\ffmpeg\ffmpeg-8.1-essentials_build\bin" `
  --add-data "$($ffprobeExe.Path);tools\ffmpeg\ffmpeg-8.1-essentials_build\bin" `
  free_online_video_downloader_gui.py
