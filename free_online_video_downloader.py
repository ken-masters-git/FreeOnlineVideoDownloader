#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Callable


APP_NAME = "FreeOnlineVideoDownloader"
DEFAULT_URL = "https://www.youtube.com/watch?v=2fq9wYslV0A"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def get_app_dir() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def get_resource_dir() -> Path:
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS", get_app_dir()))
    return Path(__file__).resolve().parent


APP_DIR = get_app_dir()
RESOURCE_DIR = get_resource_dir()
VENDOR_DIR = RESOURCE_DIR / ".vendor"
OUTPUT_DIR = APP_DIR / "downloads"
TOOLS_DIR = RESOURCE_DIR / "tools"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " \
    "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"


def configure_stdio() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def ensure_vendor_path() -> None:
    vendor = str(VENDOR_DIR)
    if vendor not in sys.path:
        sys.path.insert(0, vendor)


def prompt_yes_no(message: str, default: bool = True) -> bool:
    suffix = "[Y/n]" if default else "[y/N]"
    reply = input(f"{message} {suffix} ").strip().lower()
    if not reply:
        return default
    return reply in {"y", "yes"}


def install_yt_dlp() -> None:
    VENDOR_DIR.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "--disable-pip-version-check",
        "--upgrade",
        "--target",
        str(VENDOR_DIR),
        "yt-dlp",
    ]
    print("Installing yt-dlp into the local .vendor directory...")
    subprocess.run(command, check=True)


def load_yt_dlp(auto_install: bool, assume_yes: bool) -> Any:
    ensure_vendor_path()
    try:
        return importlib.import_module("yt_dlp")
    except ImportError:
        if not auto_install:
            raise SystemExit(
                "yt-dlp is not installed. Run with auto install enabled or install it manually."
            )

        if not assume_yes and not prompt_yes_no("yt-dlp is missing. Install it now?", default=True):
            raise SystemExit("Cancelled because yt-dlp is required.")

        try:
            install_yt_dlp()
        except subprocess.CalledProcessError as exc:
            raise SystemExit(f"Failed to install yt-dlp: {exc}") from exc

        importlib.invalidate_caches()
        ensure_vendor_path()
        return importlib.import_module("yt_dlp")


def test_http_connectivity(url: str) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.status, response.geturl()


def unwrap_video_info(info: dict[str, Any]) -> dict[str, Any]:
    if "entries" in info:
        for entry in info["entries"]:
            if entry:
                return entry
    return info


def extract_video_info(url: str, yt_dlp_module: Any) -> dict[str, Any]:
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "skip_download": True,
    }
    with yt_dlp_module.YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)
    return unwrap_video_info(info)


def has_ffmpeg() -> bool:
    return find_ffmpeg_bin_dir() is not None


def find_ffmpeg_bin_dir() -> Path | None:
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return Path(system_ffmpeg).resolve().parent

    candidates = [
        TOOLS_DIR / "ffmpeg",
        RESOURCE_DIR,
    ]
    for root in candidates:
        if not root.exists():
            continue
        matches = sorted(root.glob("**/ffmpeg.exe"))
        if matches:
            return matches[0].resolve().parent
    return None


def format_filesize(value: Any) -> str:
    if not isinstance(value, (int, float)) or value <= 0:
        return "-"

    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f}{unit}"
        size /= 1024
    return "-"


def format_resolution(fmt: dict[str, Any]) -> str:
    width = fmt.get("width")
    height = fmt.get("height")
    if width and height:
        return f"{width}x{height}"
    if height:
        return f"{height}p"
    return fmt.get("resolution") or "-"


def bitrate_kbps(fmt: dict[str, Any]) -> str:
    value = fmt.get("tbr") or fmt.get("vbr") or fmt.get("abr")
    if not isinstance(value, (int, float)) or value <= 0:
        return "-"
    return f"{int(round(value))}"


def collect_video_formats(info: dict[str, Any], allow_merge: bool) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for fmt in info.get("formats", []):
        vcodec = fmt.get("vcodec")
        acodec = fmt.get("acodec")
        has_video = vcodec not in {None, "none"}
        has_audio = acodec not in {None, "none"}
        if not has_video:
            continue
        if not allow_merge and not has_audio:
            continue

        note = "single-file" if has_audio else "ffmpeg-merge"
        rows.append(
            {
                "format_id": fmt.get("format_id", "-"),
                "ext": fmt.get("ext", "-"),
                "resolution": format_resolution(fmt),
                "fps": fmt.get("fps") or "-",
                "bitrate": bitrate_kbps(fmt),
                "filesize": format_filesize(fmt.get("filesize") or fmt.get("filesize_approx")),
                "note": note,
                "height": fmt.get("height") or 0,
                "tbr": fmt.get("tbr") or fmt.get("vbr") or fmt.get("abr") or 0,
                "has_audio": has_audio,
            }
        )

    rows.sort(
        key=lambda item: (
            item["height"],
            item["has_audio"],
            item["tbr"],
        ),
        reverse=True,
    )
    return rows


def format_choice_label(row: dict[str, Any]) -> str:
    return (
        f"{row['format_id']} | {row['ext'].upper()} | {row['resolution']} | "
        f"{row['fps']} fps | {row['bitrate']} kbps | {row['filesize']} | {row['note']}"
    )


def collect_subtitle_rows(info: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source_map = (
        ("subtitles", "manual", "Manual"),
        ("automatic_captions", "auto", "Auto-generated"),
    )
    for key, source_id, source_label in source_map:
        source_data = info.get(key) or {}
        if not isinstance(source_data, dict):
            continue
        for language, tracks in sorted(source_data.items()):
            if not isinstance(tracks, list) or not tracks:
                continue
            formats = sorted({track.get("ext") for track in tracks if isinstance(track, dict) and track.get("ext")})
            rows.append(
                {
                    "id": f"{source_id}:{language}",
                    "language": language,
                    "source": source_id,
                    "source_label": source_label,
                    "formats": formats,
                }
            )
    return rows


def format_subtitle_choice_label(row: dict[str, Any]) -> str:
    formats = ", ".join(row["formats"]) if row["formats"] else "unknown format"
    return f"{row['source_label']} | {row['language']} | {formats}"


def summarize_subtitle_rows(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return "No subtitles detected."

    def summarize_group(source: str, label: str) -> str | None:
        languages = [row["language"] for row in rows if row["source"] == source]
        if not languages:
            return None
        listed = ", ".join(languages[:5])
        if len(languages) > 5:
            listed = f"{listed}, +{len(languages) - 5} more"
        return f"{label}: {listed}"

    parts = [
        part
        for part in (
            summarize_group("manual", "Manual"),
            summarize_group("auto", "Auto-generated"),
        )
        if part is not None
    ]
    return " | ".join(parts)


def detect_video(url: str, auto_install: bool = True, assume_yes: bool = False) -> dict[str, Any]:
    target_url = url.strip()
    if not target_url:
        raise SystemExit("A video URL is required.")

    status_code, final_url = test_http_connectivity(target_url)
    yt_dlp_module = load_yt_dlp(auto_install=auto_install, assume_yes=assume_yes)
    info = extract_video_info(target_url, yt_dlp_module)

    ffmpeg_bin_dir = find_ffmpeg_bin_dir()
    allow_merge = ffmpeg_bin_dir is not None
    rows = collect_video_formats(info, allow_merge=allow_merge)
    if not rows:
        raise SystemExit("No downloadable video formats were found for the current environment.")
    subtitle_rows = collect_subtitle_rows(info)

    return {
        "url": target_url,
        "final_url": final_url,
        "status_code": status_code,
        "yt_dlp_module": yt_dlp_module,
        "info": info,
        "title": info.get("title", "unknown"),
        "uploader": info.get("uploader", "unknown"),
        "ffmpeg_bin_dir": ffmpeg_bin_dir,
        "allow_merge": allow_merge,
        "rows": rows,
        "subtitle_rows": subtitle_rows,
        "subtitle_summary": summarize_subtitle_rows(subtitle_rows),
    }


def render_table(rows: list[dict[str, Any]]) -> str:
    headers = ["No", "ID", "Ext", "Resolution", "FPS", "Kbps", "Size", "Mode"]
    data_rows = []
    for index, row in enumerate(rows, start=1):
        data_rows.append(
            [
                str(index),
                str(row["format_id"]),
                str(row["ext"]),
                str(row["resolution"]),
                str(row["fps"]),
                str(row["bitrate"]),
                str(row["filesize"]),
                str(row["note"]),
            ]
        )

    widths = [len(header) for header in headers]
    for row in data_rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    def render_line(values: list[str]) -> str:
        return "  ".join(value.ljust(widths[idx]) for idx, value in enumerate(values))

    lines = [render_line(headers), render_line(["-" * width for width in widths])]
    lines.extend(render_line(row) for row in data_rows)
    return "\n".join(lines)


def prompt_format_selection(rows: list[dict[str, Any]]) -> dict[str, Any]:
    while True:
        reply = input(f"Choose a format [1-{len(rows)}], or press Enter to cancel: ").strip()
        if not reply:
            raise SystemExit("Cancelled.")
        if reply.isdigit():
            choice = int(reply)
            if 1 <= choice <= len(rows):
                return rows[choice - 1]
        print("Invalid selection, try again.")


def build_format_selector(selected: dict[str, Any], allow_merge: bool) -> str:
    format_id = str(selected["format_id"])
    if selected["has_audio"]:
        return format_id
    if not allow_merge:
        raise SystemExit("The selected format requires ffmpeg, but ffmpeg was not found.")
    if selected["ext"] == "mp4":
        return f"{format_id}+bestaudio[ext=m4a]/{format_id}+bestaudio/best"
    return f"{format_id}+bestaudio/best"


def download_video(
    url: str,
    output_dir: Path,
    yt_dlp_module: Any,
    format_selector: str,
    ffmpeg_bin_dir: Path | None,
    subtitle_row: dict[str, Any] | None = None,
    progress_hook: Callable[[dict[str, Any]], None] | None = None,
    postprocessor_hook: Callable[[dict[str, Any]], None] | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    options = {
        "noplaylist": True,
        "format": format_selector,
        "outtmpl": str(output_dir / "%(title).200B [%(id)s].%(ext)s"),
    }
    if progress_hook is not None:
        options["progress_hooks"] = [progress_hook]
    if postprocessor_hook is not None:
        options["postprocessor_hooks"] = [postprocessor_hook]
    if subtitle_row is not None:
        options["subtitleslangs"] = [subtitle_row["language"]]
        options["subtitlesformat"] = "best"
        if subtitle_row["source"] == "manual":
            options["writesubtitles"] = True
        else:
            options["writeautomaticsub"] = True
    if ffmpeg_bin_dir is not None:
        options["ffmpeg_location"] = str(ffmpeg_bin_dir)
        options["merge_output_format"] = "mp4"
    with yt_dlp_module.YoutubeDL(options) as ydl:
        ydl.download([url])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Test a video URL, list available formats, and download one interactively."
    )
    parser.add_argument(
        "url",
        nargs="?",
        default=DEFAULT_URL,
        help=f"Video URL to inspect. Defaults to {DEFAULT_URL}",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=str(OUTPUT_DIR),
        help=f"Download directory. Defaults to {OUTPUT_DIR}",
    )
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="Only test connectivity and list formats without downloading.",
    )
    parser.add_argument(
        "--no-auto-install",
        action="store_true",
        help="Do not try to install yt-dlp automatically.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the install confirmation prompt when yt-dlp is missing.",
    )
    return parser.parse_args()


def main() -> int:
    configure_stdio()
    args = parse_args()
    output_dir = Path(args.output).expanduser().resolve()

    try:
        detection = detect_video(
            args.url,
            auto_install=not args.no_auto_install,
            assume_yes=args.yes,
        )
    except urllib.error.URLError as exc:
        raise SystemExit(f"Connectivity test failed: {exc}") from exc
    except Exception as exc:
        raise SystemExit(str(exc)) from exc

    print(f"Target URL: {detection['url']}")
    print(f"HTTP connectivity: {detection['status_code']} -> {detection['final_url']}")
    print(f"Title: {detection['title']}")
    print(f"Uploader: {detection['uploader']}")

    allow_merge = detection["allow_merge"]
    if allow_merge:
        print("ffmpeg detected: all video formats will be shown, including merge-required entries.")
    else:
        print("ffmpeg not found: only single-file formats with built-in audio will be shown.")

    rows = detection["rows"]

    print()
    print(render_table(rows))

    if args.test_only:
        print()
        print("Test completed. No download was started.")
        return 0

    print()
    selected = prompt_format_selection(rows)
    format_selector = build_format_selector(selected, allow_merge=allow_merge)

    print(f"Downloading format {selected['format_id']} into {output_dir} ...")
    download_video(
        detection["url"],
        output_dir,
        detection["yt_dlp_module"],
        format_selector,
        detection["ffmpeg_bin_dir"],
    )
    print("Download completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
