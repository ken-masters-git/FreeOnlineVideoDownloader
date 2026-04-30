# AGENTS.md

This file is the single-source handoff/context file for future AI-assisted work on this repository.

If a future session starts on another machine, the safest instruction is:

`Please read AGENTS.md first, then continue working on this project.`

## Project Identity

- Project name: `FreeOnlineVideoDownloader`
- Purpose: a Windows-focused video downloader with both GUI and CLI entry points
- Primary audience: end users who want a packaged Windows `exe`, plus developers who may rebuild it from source
- Current repository branch used during setup: `master`

## Main Capabilities

- Detect a supported video URL and list downloadable formats
- Download selected formats through `yt-dlp`
- Merge separate video/audio streams with `ffmpeg` into `mp4` when possible
- Detect subtitles, including manual and auto-generated tracks when available
- Provide both:
  - a desktop GUI
  - a command-line workflow
- Build a one-file Windows executable with PyInstaller
- Build the executable automatically in GitHub Actions
- Publish the executable automatically to GitHub Releases on `v*` tags

## Key Files

- `free_online_video_downloader.py`
  - core backend logic
  - detection
  - format selection data
  - subtitle inspection
  - download logic
  - ffmpeg discovery

- `free_online_video_downloader_gui.py`
  - Tkinter GUI entry point
  - status/progress UI
  - format/subtitle/save-folder controls

- `build_free_online_video_downloader_exe.ps1`
  - local Windows build script for PyInstaller
  - dynamically locates `ffmpeg.exe` and `ffprobe.exe` under `tools\ffmpeg`
  - bundles icon and ffmpeg binaries into the `exe`

- `clean_free_online_video_downloader_build.ps1`
  - removes old build outputs

- `.github/workflows/build-windows-exe.yml`
  - GitHub Actions workflow
  - auto-builds on push to `master` or `main`
  - supports manual dispatch
  - on `v*` tags, builds and publishes `FreeOnlineVideoDownloader.exe` to GitHub Releases

- `README.md`
  - end-user and developer documentation

- `assets/free_online_video_downloader.ico`
  - Windows icon used by GUI and packaged `exe`

## Runtime Behavior

- Default desktop experience is the packaged `exe`
- GUI is in English
- GUI supports:
  - URL input
  - `Detect`
  - format selection
  - subtitle selection
  - save-folder selection
  - bottom status strip with progress shown only during active work
- Default save folder in GUI is the directory containing the running `exe`
- CLI supports test-only inspection and interactive download

## Supported Sites

- The app is not limited to YouTube
- It relies on `yt-dlp`, so any site currently supported by `yt-dlp` may work
- Verified during development:
  - YouTube
  - Bilibili
  - Facebook video URL detection worked in testing

## Compatibility Notes

- For best playback compatibility in apps such as WeChat, prefer:
  - `MP4`
  - `H.264` video
  - `AAC` audio
- In practice, `720p mp4` is often a safer compatibility/size tradeoff than `1080p`

## Build Layout Assumptions

- Ignored local dependency directories:
  - `.vendor`
  - `.pyinstaller_vendor`
  - `tools`
- They are intentionally not stored in Git
- They are recreated locally or in CI before building

### Local build prerequisites

- Python
- Tkinter available in the Python install
- `yt-dlp` installed into `.vendor`
- PyInstaller installed into `.pyinstaller_vendor`
- FFmpeg extracted somewhere under `tools\ffmpeg`

### Local build output

- expected packaged file:
  - `dist\FreeOnlineVideoDownloader.exe`

## GitHub Actions / Release Workflow

- Workflow file:
  - `.github/workflows/build-windows-exe.yml`

- Trigger behavior:
  - push to `master` or `main`: build `exe` and upload as workflow artifact
  - manual run: build `exe` on demand
  - push tag matching `v*`: build `exe`, upload artifact, then create or update a GitHub Release and attach `FreeOnlineVideoDownloader.exe`

- The workflow was updated to use Node 24 compatible action versions:
  - `actions/checkout@v6`
  - `actions/setup-python@v6`
  - `actions/upload-artifact@v6`

- The release publishing step must run in `pwsh`, not legacy `powershell`, because the logic intentionally tolerates `gh release view` returning "release not found" on a first tag

- The current build flow does not depend on a committed PyInstaller `.spec` file
  - `build_free_online_video_downloader_exe.ps1` passes PyInstaller options directly
  - PyInstaller may auto-generate `FreeOnlineVideoDownloader.spec` during local builds
  - generated `*.spec` files are ignored because they can contain machine-specific absolute paths

## Known Historical Pitfalls

These were already encountered and fixed. Do not reintroduce them.

1. Hard-coded FFmpeg extracted folder name
   - Older build logic assumed a specific directory like `ffmpeg-8.1-essentials_build`
   - Fixed by recursively discovering `ffmpeg.exe` and `ffprobe.exe` under `tools\ffmpeg`

2. PyInstaller build script could look successful even when Python failed
   - Fixed by checking `$LASTEXITCODE` after the PyInstaller invocation and throwing on non-zero

3. GitHub Actions warning about deprecated Node 20 actions
   - Fixed by upgrading workflow action versions to Node 24 compatible major versions

4. First tag release creation failed with `gh : release not found`
   - Root cause: initial release lookup returned non-zero and was treated as fatal
   - Fixed by running the publish step in `pwsh` and explicitly handling the "release does not exist yet" path before calling `gh release create`

## Release Practice

- Recommended public release flow:
  1. Push `master`
  2. Confirm GitHub Actions build succeeds
  3. Create a version tag such as `v0.1.1`
  4. Push the tag
  5. Confirm the tag workflow creates or updates the Release and uploads `FreeOnlineVideoDownloader.exe`
  6. Edit Release notes if needed

- Prefer creating a new version tag rather than repeatedly rewriting a previously published tag

## Recommended First Read Order For Future Sessions

If a future AI session needs to get up to speed fast, this is the recommended order:

1. `AGENTS.md`
2. `README.md`
3. `.github/workflows/build-windows-exe.yml`
4. `build_free_online_video_downloader_exe.ps1`
5. `free_online_video_downloader.py`
6. `free_online_video_downloader_gui.py`

## How To Prompt A Future Session

Use one of these:

- `Please read AGENTS.md first, then help me continue this project.`
- `Please read AGENTS.md and README.md, then inspect the current build/release flow.`
- `Please read AGENTS.md before making changes.`

## Scope Of This File

This file is meant to replace scattered handoff notes. Keep project-state and AI-oriented operational knowledge here.

If a new machine or a new AI session only reads one project-specific context file, it should be this one.
