# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('C:\\Users\\localAdmin\\Documents\\Playground\\assets', 'assets'), ('C:\\Users\\localAdmin\\Documents\\Playground\\tools\\ffmpeg\\ffmpeg-8.1-essentials_build\\bin\\ffmpeg.exe', 'tools\\ffmpeg\\ffmpeg-8.1-essentials_build\\bin'), ('C:\\Users\\localAdmin\\Documents\\Playground\\tools\\ffmpeg\\ffmpeg-8.1-essentials_build\\bin\\ffprobe.exe', 'tools\\ffmpeg\\ffmpeg-8.1-essentials_build\\bin')]
binaries = []
hiddenimports = []
tmp_ret = collect_all('yt_dlp')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['free_online_video_downloader_gui.py'],
    pathex=['C:\\Users\\localAdmin\\Documents\\Playground\\.vendor'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FreeOnlineVideoDownloader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\localAdmin\\Documents\\Playground\\assets\\free_online_video_downloader.ico'],
)
