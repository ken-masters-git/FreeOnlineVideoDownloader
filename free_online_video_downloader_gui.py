#!/usr/bin/env python3
from __future__ import annotations

import argparse
import threading
import tkinter as tk
from pathlib import Path
import sys
from tkinter import filedialog, messagebox, ttk

import free_online_video_downloader as backend


DEFAULT_SAVE_DIR = backend.APP_DIR
STATUS_BAR_BG = "white"
STATUS_PROGRESS_IDLE_STYLE = "StatusIdle.Horizontal.TProgressbar"
STATUS_PROGRESS_ACTIVE_STYLE = "StatusActive.Horizontal.TProgressbar"
APP_ICON_PNG = backend.RESOURCE_DIR / "assets" / "free_online_video_downloader_icon.png"
APP_ICON_ICO = backend.RESOURCE_DIR / "assets" / "free_online_video_downloader.ico"


class HoverHelp:
    def __init__(self, widget: tk.Widget, text: str, delay_ms: int = 3000) -> None:
        self.widget = widget
        self.text = text
        self.delay_ms = delay_ms
        self._after_id: str | None = None
        self._tip_window: tk.Toplevel | None = None

        widget.bind("<Enter>", self._schedule, add="+")
        widget.bind("<Leave>", self._hide, add="+")
        widget.bind("<ButtonPress>", self._hide, add="+")
        widget.bind("<Destroy>", self._hide, add="+")

    def _schedule(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self._cancel()
        self._after_id = self.widget.after(self.delay_ms, self._show)

    def _cancel(self) -> None:
        if self._after_id is not None:
            self.widget.after_cancel(self._after_id)
            self._after_id = None

    def _show(self) -> None:
        if self._tip_window is not None or not self.text:
            return

        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 10

        self._tip_window = tk.Toplevel(self.widget)
        self._tip_window.wm_overrideredirect(True)
        self._tip_window.wm_attributes("-topmost", True)
        self._tip_window.wm_geometry(f"+{x}+{y}")

        label = ttk.Label(
            self._tip_window,
            text=self.text,
            justify="left",
            padding=(8, 6),
            relief="solid",
            borderwidth=1,
            wraplength=320,
        )
        label.pack()

    def _hide(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        self._cancel()
        if self._tip_window is not None:
            self._tip_window.destroy()
            self._tip_window = None


class FreeOnlineVideoDownloaderApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(backend.APP_NAME)
        self._window_icon_image: tk.PhotoImage | None = None
        self.style = ttk.Style(self.root)

        self.url_var = tk.StringVar(value=backend.DEFAULT_URL)
        self.format_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Enter a video URL, then click Detect.")
        self.title_var = tk.StringVar(value="-")
        self.uploader_var = tk.StringVar(value="-")
        self.reachability_var = tk.StringVar(value="-")
        self.subtitle_summary_var = tk.StringVar(value="-")
        self.output_var = tk.StringVar(value=str(DEFAULT_SAVE_DIR))
        self.progress_var = tk.DoubleVar(value=0.0)

        self.detect_result: dict[str, object] | None = None
        self.subtitle_choices: list[dict[str, object] | None] = [None]
        self._busy = False
        self._help_refs: list[HoverHelp] = []
        self._expected_download_parts = 1
        self._download_part_progress: dict[str, float] = {}
        self._progress_visible = True

        self._apply_window_icon()
        self._configure_styles()
        self._build_ui()
        self._bind_help()
        self._reset_progress()
        self._finalize_window_size()

    def _build_ui(self) -> None:
        content = ttk.Frame(self.root, padding=(16, 16, 16, 0))
        content.pack(fill="both", expand=True)
        content.columnconfigure(0, weight=1)

        self.title_label = ttk.Label(
            content,
            text=backend.APP_NAME,
            font=("Segoe UI", 16, "bold"),
        )
        self.title_label.grid(row=0, column=0, sticky="w")

        self.intro_label = ttk.Label(
            content,
            text="Detect a valid video URL, choose a format, then download a merged MP4 when possible.",
        )
        self.intro_label.grid(row=1, column=0, sticky="w", pady=(6, 14))

        self.url_frame = ttk.LabelFrame(content, text="Source")
        self.url_frame.grid(row=2, column=0, sticky="ew")
        self.url_frame.columnconfigure(1, weight=1)

        self.url_label = ttk.Label(self.url_frame, text="Video URL")
        self.url_label.grid(row=0, column=0, sticky="w", padx=(12, 8), pady=12)

        self.url_entry = ttk.Entry(self.url_frame, textvariable=self.url_var)
        self.url_entry.grid(row=0, column=1, sticky="ew", pady=12)
        self.url_entry.bind("<Return>", self._handle_detect)

        self.detect_button = ttk.Button(self.url_frame, text="Detect", command=self._handle_detect)
        self.detect_button.grid(row=0, column=2, padx=(10, 12), pady=12)

        self.details_frame = ttk.LabelFrame(content, text="Detected Video")
        self.details_frame.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        self.details_frame.columnconfigure(1, weight=1)

        self.video_title_label = ttk.Label(self.details_frame, text="Title")
        self.video_title_label.grid(row=0, column=0, sticky="nw", padx=(12, 8), pady=(12, 6))
        self.title_value = ttk.Label(
            self.details_frame,
            textvariable=self.title_var,
            wraplength=700,
            justify="left",
        )
        self.title_value.grid(row=0, column=1, sticky="w", padx=(0, 12), pady=(12, 6))

        self.video_uploader_label = ttk.Label(self.details_frame, text="Uploader")
        self.video_uploader_label.grid(row=1, column=0, sticky="nw", padx=(12, 8), pady=6)
        self.uploader_value = ttk.Label(
            self.details_frame,
            textvariable=self.uploader_var,
            wraplength=700,
            justify="left",
        )
        self.uploader_value.grid(row=1, column=1, sticky="w", padx=(0, 12), pady=6)

        self.video_detection_label = ttk.Label(self.details_frame, text="Detection")
        self.video_detection_label.grid(row=2, column=0, sticky="nw", padx=(12, 8), pady=(6, 12))
        self.reachability_value = ttk.Label(
            self.details_frame,
            textvariable=self.reachability_var,
            wraplength=700,
            justify="left",
        )
        self.reachability_value.grid(row=2, column=1, sticky="w", padx=(0, 12), pady=(6, 12))

        self.video_subtitles_label = ttk.Label(self.details_frame, text="Subtitles")
        self.video_subtitles_label.grid(row=3, column=0, sticky="nw", padx=(12, 8), pady=(0, 12))
        self.subtitle_summary_value = ttk.Label(
            self.details_frame,
            textvariable=self.subtitle_summary_var,
            wraplength=700,
            justify="left",
        )
        self.subtitle_summary_value.grid(row=3, column=1, sticky="w", padx=(0, 12), pady=(0, 12))

        self.action_frame = ttk.LabelFrame(content, text="Download Options")
        self.action_frame.grid(row=4, column=0, sticky="ew", pady=(14, 0))
        self.action_frame.columnconfigure(1, weight=1)

        self.save_folder_label = ttk.Label(self.action_frame, text="Save Folder")
        self.save_folder_label.grid(row=0, column=0, sticky="w", padx=(12, 8), pady=(12, 6))

        self.output_entry = ttk.Entry(self.action_frame, textvariable=self.output_var, state="readonly")
        self.output_entry.grid(row=0, column=1, sticky="ew", pady=(12, 6))

        self.select_button = ttk.Button(self.action_frame, text="Select", command=self._handle_select_folder)
        self.select_button.grid(row=0, column=2, padx=(10, 12), pady=(12, 6))

        self.format_label = ttk.Label(self.action_frame, text="Format")
        self.format_label.grid(row=1, column=0, sticky="w", padx=(12, 8), pady=(6, 12))

        self.format_combo = ttk.Combobox(
            self.action_frame,
            textvariable=self.format_var,
            state="disabled",
            width=72,
        )
        self.format_combo.grid(row=1, column=1, sticky="ew", pady=(6, 12))
        self.format_combo.bind("<<ComboboxSelected>>", self._handle_format_selected)

        self.subtitle_label = ttk.Label(self.action_frame, text="Subtitle")
        self.subtitle_label.grid(row=2, column=0, sticky="w", padx=(12, 8), pady=(0, 12))

        self.subtitle_combo = ttk.Combobox(
            self.action_frame,
            state="disabled",
            width=72,
        )
        self.subtitle_combo.grid(row=2, column=1, sticky="ew", pady=(0, 12))

        self.download_button = ttk.Button(
            self.action_frame,
            text="Download",
            command=self._handle_download,
            state="disabled",
        )
        self.download_button.grid(row=2, column=2, padx=(10, 12), pady=(0, 12))

        self.status_strip = tk.Frame(
            self.root,
            bg=STATUS_BAR_BG,
            bd=0,
            highlightthickness=0,
        )
        self.status_strip.pack(side="bottom", fill="x")
        self.status_strip.columnconfigure(0, weight=1)

        self.status_bar = tk.Label(
            self.status_strip,
            textvariable=self.status_var,
            anchor="w",
            padx=8,
            pady=6,
            bg=STATUS_BAR_BG,
        )
        self.status_bar.grid(row=0, column=0, sticky="ew")

        self.status_separator = tk.Frame(self.status_strip, width=1, bg="#d0d0d0")
        self.status_separator.grid(row=0, column=1, sticky="ns", pady=4)

        self.progress_bar = ttk.Progressbar(
            self.status_strip,
            maximum=100,
            variable=self.progress_var,
            mode="determinate",
            length=240,
            style=STATUS_PROGRESS_IDLE_STYLE,
        )
        self.progress_bar.grid(row=0, column=2, sticky="e", padx=(8, 8), pady=6)

    def _configure_styles(self) -> None:
        self.style.configure(
            STATUS_PROGRESS_IDLE_STYLE,
            troughcolor=STATUS_BAR_BG,
            background=STATUS_BAR_BG,
            darkcolor=STATUS_BAR_BG,
            lightcolor=STATUS_BAR_BG,
            bordercolor=STATUS_BAR_BG,
            thickness=14,
        )
        self.style.configure(
            STATUS_PROGRESS_ACTIVE_STYLE,
            troughcolor=STATUS_BAR_BG,
            background="#78b83f",
            darkcolor="#5f9531",
            lightcolor="#9bd25b",
            bordercolor=STATUS_BAR_BG,
            thickness=14,
        )

    def _apply_window_icon(self) -> None:
        try:
            if APP_ICON_ICO.exists():
                self.root.iconbitmap(default=str(APP_ICON_ICO))
            elif APP_ICON_PNG.exists():
                self._window_icon_image = tk.PhotoImage(file=str(APP_ICON_PNG))
                self.root.iconphoto(True, self._window_icon_image)
        except tk.TclError:
            self._window_icon_image = None

    def _bind_help(self) -> None:
        help_map = {
            self.title_label: "The main window title for this downloader.",
            self.intro_label: "Brief summary of the workflow used by this window.",
            self.url_frame: "Source section for entering a video URL and running detection.",
            self.url_label: "Label for the video URL input field.",
            self.url_entry: "Paste a full video URL here before running detection.",
            self.detect_button: "Check whether the URL points to a real downloadable video and load its formats.",
            self.details_frame: "Shows metadata collected from the detected video.",
            self.video_title_label: "Label for the detected video title.",
            self.title_value: "Displays the detected video title after a successful detection.",
            self.video_uploader_label: "Label for the detected uploader name.",
            self.uploader_value: "Displays the detected uploader or channel name.",
            self.video_detection_label: "Label for the detection summary line.",
            self.reachability_value: "Shows whether the URL resolved to a real video and how many formats were found.",
            self.video_subtitles_label: "Label for the detected subtitle summary.",
            self.subtitle_summary_value: "Shows whether manual or auto-generated subtitles were detected, and for which languages.",
            self.action_frame: "Contains the save location, format picker, and download button.",
            self.save_folder_label: "Label for the folder where downloads will be saved.",
            self.output_entry: "Shows the current target folder. By default, this is the folder that contains the executable.",
            self.select_button: "Choose a different target folder for the downloaded file.",
            self.format_label: "Label for the detected format selection box.",
            self.format_combo: "Choose one detected video format. This stays disabled until detection succeeds.",
            self.subtitle_label: "Label for the subtitle selection box.",
            self.subtitle_combo: "Choose whether to download no subtitles or one detected subtitle language.",
            self.download_button: "Download the selected format into the chosen folder. This stays disabled until a format has been selected.",
            self.status_strip: "Combined status area that shows the latest message and the overall progress bar.",
            self.progress_bar: "Shows overall progress for the current operation, including download and post-processing.",
            self.status_separator: "Separates the status text from the inline progress bar.",
            self.status_bar: "Displays the latest status message at the bottom of the window.",
        }
        for widget, text in help_map.items():
            self._help_refs.append(HoverHelp(widget, text))

    def _finalize_window_size(self) -> None:
        self.root.update_idletasks()
        self.root.geometry("")
        self.root.update_idletasks()
        width = max(self.root.winfo_width(), 920)
        height = self.root.winfo_height()
        self.root.geometry(f"{width}x{height}")
        self.root.minsize(width, height)
        self.root.maxsize(width, height)
        self.root.resizable(False, False)

    def _set_progress_style(self, active: bool) -> None:
        style_name = STATUS_PROGRESS_ACTIVE_STYLE if active else STATUS_PROGRESS_IDLE_STYLE
        self.progress_bar.configure(style=style_name)

    def _show_progress_widgets(self) -> None:
        if self._progress_visible:
            return
        self.status_separator.grid()
        self.progress_bar.grid()
        self._progress_visible = True

    def _hide_progress_widgets(self) -> None:
        if not self._progress_visible:
            return
        self.status_separator.grid_remove()
        self.progress_bar.grid_remove()
        self._progress_visible = False

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self.url_entry.configure(state="disabled" if busy else "normal")
        self.detect_button.configure(state="disabled" if busy else "normal")
        self.output_entry.configure(state="readonly")
        self.select_button.configure(state="disabled" if busy else "normal")
        self.format_combo.configure(state="disabled" if busy or not self.detect_result else "readonly")
        subtitle_state = "disabled"
        if not busy and self.detect_result and len(self.subtitle_choices) > 1:
            subtitle_state = "readonly"
        self.subtitle_combo.configure(state=subtitle_state)

        download_state = "disabled"
        if not busy and self.detect_result and self.format_combo.current() >= 0:
            download_state = "normal"
        self.download_button.configure(state=download_state)

    def _reset_progress(self) -> None:
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_var.set(0.0)
        self._set_progress_style(False)
        self._hide_progress_widgets()

    def _start_indeterminate_progress(self, status_text: str) -> None:
        self._show_progress_widgets()
        self.progress_bar.stop()
        self.progress_bar.configure(mode="indeterminate")
        self.progress_var.set(0.0)
        self._set_progress_style(True)
        self.progress_bar.start(12)
        self.status_var.set(status_text)

    def _set_progress_value(self, value: float, status_text: str | None = None) -> None:
        self._show_progress_widgets()
        if self.progress_bar.cget("mode") != "determinate":
            self.progress_bar.stop()
            self.progress_bar.configure(mode="determinate")
        normalized_value = max(0.0, min(100.0, value))
        self.progress_var.set(normalized_value)
        self._set_progress_style(True)
        if status_text is not None:
            self.status_var.set(status_text)

    def _reset_detected_state(self) -> None:
        self.detect_result = None
        self.format_var.set("")
        self.format_combo.configure(values=(), state="disabled")
        self.download_button.configure(state="disabled")
        self.title_var.set("-")
        self.uploader_var.set("-")
        self.reachability_var.set("-")
        self.subtitle_summary_var.set("-")
        self.subtitle_choices = [None]
        self.subtitle_combo.configure(values=(), state="disabled")
        self.subtitle_combo.set("")

    def _handle_select_folder(self) -> None:
        if self._busy:
            return

        current_dir = Path(self.output_var.get()).expanduser()
        initial_dir = current_dir if current_dir.exists() else DEFAULT_SAVE_DIR
        selected = filedialog.askdirectory(
            title="Select Download Folder",
            initialdir=str(initial_dir),
            mustexist=False,
        )
        if selected:
            self.output_var.set(selected)
            self.status_var.set("Save folder updated.")

    def _handle_detect(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        if self._busy:
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Enter a video URL before clicking Detect.")
            return

        self._reset_detected_state()
        self._start_indeterminate_progress("Checking the URL and reading available video formats...")
        self._set_busy(True)

        worker = threading.Thread(target=self._detect_worker, args=(url,), daemon=True)
        worker.start()

    def _detect_worker(self, url: str) -> None:
        try:
            detection = backend.detect_video(url, auto_install=True, assume_yes=True)
        except Exception as exc:
            self.root.after(0, lambda: self._handle_detect_error(str(exc)))
            return

        self.root.after(0, lambda: self._handle_detect_success(detection))

    def _handle_detect_success(self, detection: dict[str, object]) -> None:
        self.detect_result = detection
        rows = detection["rows"]
        values = [backend.format_choice_label(row) for row in rows]

        self.title_var.set(str(detection["title"]))
        self.uploader_var.set(str(detection["uploader"]))
        self.reachability_var.set(
            f"Valid video detected. HTTP {detection['status_code']} to {detection['final_url']}. "
            f"{len(rows)} format(s) available."
        )
        self.subtitle_summary_var.set(str(detection["subtitle_summary"]))
        self.format_combo.configure(values=values, state="readonly")
        self.format_var.set("")
        subtitle_rows = detection["subtitle_rows"]
        if subtitle_rows:
            self.subtitle_choices = [None, *subtitle_rows]
            subtitle_values = ["No subtitles"] + [
                backend.format_subtitle_choice_label(row) for row in subtitle_rows
            ]
            self.subtitle_combo.configure(values=subtitle_values)
            self.subtitle_combo.current(0)
        else:
            self.subtitle_choices = [None]
            self.subtitle_combo.configure(values=("No subtitles detected",), state="disabled")
            self.subtitle_combo.current(0)
        self._reset_progress()
        self.status_var.set("Detection succeeded. Choose a format to enable Download.")
        self._set_busy(False)

    def _handle_detect_error(self, error_text: str) -> None:
        self._reset_detected_state()
        self._reset_progress()
        self.status_var.set(f"Detection failed: {error_text}")
        self._set_busy(False)
        messagebox.showerror("Detection Failed", error_text)

    def _handle_format_selected(self, _event: tk.Event[tk.Misc] | None = None) -> None:
        if self.detect_result and self.format_combo.current() >= 0 and not self._busy:
            self.download_button.configure(state="normal")
            self.status_var.set("Format selected. Download is ready.")

    def _prepare_download_progress(
        self,
        selected_row: dict[str, object],
        has_subtitle_download: bool,
    ) -> None:
        self._expected_download_parts = 1 if selected_row["has_audio"] else 2
        if has_subtitle_download:
            self._expected_download_parts += 1
        self._download_part_progress = {}
        self._set_progress_value(0.0, "Preparing download...")

    def _download_progress_hook(self, data: dict[str, object]) -> None:
        status = data.get("status")
        filename = str(data.get("filename") or data.get("tmpfilename") or f"part-{len(self._download_part_progress) + 1}")

        if status == "downloading":
            downloaded = float(data.get("downloaded_bytes") or 0.0)
            total = float(data.get("total_bytes") or data.get("total_bytes_estimate") or 0.0)
            fraction = downloaded / total if total > 0 else self._download_part_progress.get(filename, 0.0)
            self._download_part_progress[filename] = max(
                self._download_part_progress.get(filename, 0.0),
                min(max(fraction, 0.0), 1.0),
            )
            progress = self._calculate_download_progress()
            self.root.after(0, lambda p=progress: self._set_progress_value(p, "Downloading selected files..."))
        elif status == "finished":
            self._download_part_progress[filename] = 1.0
            progress = self._calculate_download_progress()
            self.root.after(
                0,
                lambda p=progress: self._set_progress_value(
                    p,
                    "Download stage finished. Starting post-processing...",
                ),
            )

    def _postprocessor_progress_hook(self, data: dict[str, object]) -> None:
        status = str(data.get("status") or "")
        postprocessor = str(data.get("postprocessor") or "Post-processing")

        if status == "started":
            self.root.after(0, lambda: self._set_progress_value(92.0, f"{postprocessor} started..."))
        elif status == "processing":
            self.root.after(0, lambda: self._set_progress_value(96.0, f"{postprocessor} in progress..."))
        elif status == "finished":
            self.root.after(0, lambda: self._set_progress_value(99.0, f"{postprocessor} finished."))

    def _calculate_download_progress(self) -> float:
        total_parts = max(self._expected_download_parts, 1)
        completed = min(sum(self._download_part_progress.values()), float(total_parts))
        return (completed / total_parts) * 90.0

    def _handle_download(self) -> None:
        if self._busy or not self.detect_result:
            return

        index = self.format_combo.current()
        if index < 0:
            messagebox.showwarning("Missing Format", "Choose a format before clicking Download.")
            return

        output_dir = Path(self.output_var.get()).expanduser()
        if not output_dir.is_absolute():
            output_dir = output_dir.resolve()

        detection = self.detect_result
        selected_row = detection["rows"][index]
        subtitle_index = self.subtitle_combo.current()
        selected_subtitle = None
        if subtitle_index >= 0 and subtitle_index < len(self.subtitle_choices):
            selected_subtitle = self.subtitle_choices[subtitle_index]
        self._prepare_download_progress(selected_row, selected_subtitle is not None)
        self._set_busy(True)

        worker = threading.Thread(
            target=self._download_worker,
            args=(index, output_dir, selected_subtitle),
            daemon=True,
        )
        worker.start()

    def _download_worker(
        self,
        index: int,
        output_dir: Path,
        selected_subtitle: dict[str, object] | None,
    ) -> None:
        assert self.detect_result is not None
        detection = self.detect_result
        rows = detection["rows"]
        selected_row = rows[index]

        output_dir.mkdir(parents=True, exist_ok=True)
        previous_names = {path.name for path in output_dir.iterdir() if path.is_file()}

        try:
            format_selector = backend.build_format_selector(
                selected_row,
                allow_merge=bool(detection["allow_merge"]),
            )
            backend.download_video(
                str(detection["url"]),
                output_dir,
                detection["yt_dlp_module"],
                format_selector,
                detection["ffmpeg_bin_dir"],
                subtitle_row=selected_subtitle,
                progress_hook=self._download_progress_hook,
                postprocessor_hook=self._postprocessor_progress_hook,
            )
            created_path = self._find_newest_download(previous_names, output_dir)
        except Exception as exc:
            self.root.after(0, lambda: self._handle_download_error(str(exc)))
            return

        self.root.after(0, lambda: self._handle_download_success(created_path, output_dir))

    def _find_newest_download(self, previous_names: set[str], output_dir: Path) -> Path | None:
        candidates = [
            path
            for path in output_dir.iterdir()
            if path.is_file() and path.name not in previous_names
        ]
        if not candidates:
            candidates = [path for path in output_dir.iterdir() if path.is_file()]
        if not candidates:
            return None
        return max(candidates, key=lambda path: path.stat().st_mtime)

    def _handle_download_success(self, created_path: Path | None, output_dir: Path) -> None:
        self._set_progress_value(100.0, "Download completed successfully.")
        self._set_busy(False)

        if created_path is None:
            message = f"Download finished. Files were saved to:\n{output_dir}"
        else:
            message = f"Download finished.\n\nSaved file:\n{created_path}"
        messagebox.showinfo("Download Complete", message)
        self._reset_progress()
        self.status_var.set("Download completed successfully.")

    def _handle_download_error(self, error_text: str) -> None:
        self._reset_progress()
        self.status_var.set(f"Download failed: {error_text}")
        self._set_busy(False)
        messagebox.showerror("Download Failed", error_text)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--self-test-detect")
    parser.add_argument("--self-test-output")
    return parser.parse_args(argv)


def run_self_test(url: str, output_path: Path | None) -> int:
    detection = backend.detect_video(url, auto_install=True, assume_yes=True)
    lines = [
        f"status_code={detection['status_code']}",
        f"allow_merge={detection['allow_merge']}",
        f"formats={len(detection['rows'])}",
        f"subtitles={len(detection['subtitle_rows'])}",
        f"subtitle_summary={detection['subtitle_summary']}",
        f"title={detection['title']}",
        f"first_format={backend.format_choice_label(detection['rows'][0])}",
    ]
    text = "\n".join(lines)
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


def main() -> int:
    backend.configure_stdio()
    args = parse_args(sys.argv[1:])
    if args.self_test_detect:
        output_path = Path(args.self_test_output).expanduser().resolve() if args.self_test_output else None
        return run_self_test(args.self_test_detect, output_path)

    root = tk.Tk()
    app = FreeOnlineVideoDownloaderApp(root)
    app.url_entry.focus_set()
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
