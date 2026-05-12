from __future__ import annotations

import json
import random
import re
import shutil
import subprocess
import threading
import urllib.request
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from tkinter import (
    BooleanVar,
    Canvas,
    Frame,
    IntVar,
    Scale,
    Spinbox,
    StringVar,
    Text,
    Tk,
    filedialog,
    messagebox,
    ttk,
)

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD

    DND_AVAILABLE = True
except Exception:
    DND_FILES = None
    TkinterDnD = None
    DND_AVAILABLE = False

try:
    from tinytag import TinyTag

    TINYTAG_AVAILABLE = True
except Exception:
    TinyTag = None
    TINYTAG_AVAILABLE = False

try:
    from mutagen import File as MutagenFile

    MUTAGEN_AVAILABLE = True
except Exception:
    MutagenFile = None
    MUTAGEN_AVAILABLE = False


AUDIO_EXTENSIONS = {
    ".aac",
    ".aiff",
    ".alac",
    ".ape",
    ".flac",
    ".m4a",
    ".mp3",
    ".ogg",
    ".opus",
    ".wav",
    ".wma",
}

IMAGE_EXTENSIONS = {
    ".bmp",
    ".gif",
    ".heic",
    ".heif",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}

VIDEO_EXTENSIONS = {
    ".3gp",
    ".avi",
    ".flv",
    ".m4v",
    ".mkv",
    ".mov",
    ".mp4",
    ".mpeg",
    ".mpg",
    ".webm",
    ".wmv",
}

ISO_VIDEO_EXTENSIONS = {".3gp", ".m4v", ".mov", ".mp4"}

PDF_EXTENSIONS = {".pdf"}

FILE_TYPES = {
    "music": ("Musik", AUDIO_EXTENSIONS),
    "image": ("Gambar", IMAGE_EXTENSIONS),
    "video": ("Video", VIDEO_EXTENSIONS),
    "pdf": ("PDF", PDF_EXTENSIONS),
}

SUPPORTED_EXTENSIONS = set().union(*(extensions for _, extensions in FILE_TYPES.values()))

APP_VERSION = "1.1.6"
REPO_URL = "https://github.com/renaldyakb/playlist-generator-tools"
LATEST_RELEASE_URL = f"{REPO_URL}/releases/latest"
LATEST_RELEASE_API_URL = (
    "https://api.github.com/repos/renaldyakb/playlist-generator-tools/releases/latest"
)


@dataclass(frozen=True)
class Song:
    path: Path
    category: str

    @property
    def name(self) -> str:
        return self.path.name

    @property
    def type_label(self) -> str:
        return FILE_TYPES[self.category][0]


class PlaylistGeneratorApp:
    def __init__(self) -> None:
        self.root = TkinterDnD.Tk() if DND_AVAILABLE and TkinterDnD else Tk()
        self.root.title("Playlist Generator")
        self.root.minsize(1080, 720)
        self.root.configure(bg="#eef3f7")

        self.source_folder = StringVar()
        self.destination_folder = StringVar()
        self.mode = StringVar(value="random")
        self.recursive_scan = BooleanVar(value=False)
        self.status_text = StringVar(value="Pilih folder atau file untuk mulai.")
        self.progress_text = StringVar(value="")
        self.counts_text = StringVar(value="")
        self.type_filters = {
            key: BooleanVar(value=True)
            for key in FILE_TYPES
        }
        self.type_counts = {
            key: IntVar(value=8 if key == "music" else 0)
            for key in FILE_TYPES
        }
        self.count_sliders: dict[str, Scale] = {}
        self.count_spinboxes: dict[str, Spinbox] = {}
        self.song_tree_items: dict[str, Song] = {}
        self.preview_tree_items: dict[str, Song] = {}
        self.locked_preview_keys: set[str] = set()
        self.custom_preview_order: list[str] = []
        self.preview_drag_item: str | None = None
        self.preview_drop_target: str | None = None
        self.update_check_in_progress = False
        self.update_notified_tag: str | None = None
        self.timestamp_preview_revision = 0
        self.timestamp_preview_after_id: str | None = None
        self.timestamp_text = ""
        self.source_paths: list[Path] = []
        self.dropped_paths: list[Path] = []
        self.songs: list[Song] = []
        self.selected_songs: list[Song] = []

        self._configure_theme()
        self._build_layout()
        self.root.after(1400, self.check_for_updates_silent)

    def run(self) -> None:
        self.root.mainloop()

    def open_repository(self) -> None:
        webbrowser.open(REPO_URL)

    def open_latest_release(self) -> None:
        webbrowser.open(LATEST_RELEASE_URL)

    def check_for_updates_silent(self) -> None:
        self.start_update_check(show_current_message=False)

    def check_for_updates_manual(self) -> None:
        self.start_update_check(show_current_message=True)

    def start_update_check(self, show_current_message: bool) -> None:
        if self.update_check_in_progress:
            if show_current_message:
                self.status_text.set("Sedang mengecek update...")
            return

        self.update_check_in_progress = True
        if show_current_message:
            self.status_text.set("Mengecek update terbaru dari GitHub...")

        thread = threading.Thread(
            target=self._check_update_worker,
            args=(show_current_message,),
            daemon=True,
        )
        thread.start()

    def _check_update_worker(self, show_current_message: bool) -> None:
        try:
            release = self.fetch_latest_release()
        except Exception as exc:
            self.root.after(
                0,
                self.finish_update_check,
                None,
                show_current_message,
                str(exc),
            )
            return

        self.root.after(0, self.finish_update_check, release, show_current_message, "")

    def fetch_latest_release(self) -> dict[str, str]:
        request = urllib.request.Request(
            LATEST_RELEASE_API_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": f"PlaylistGenerator/{APP_VERSION}",
            },
        )
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8"))

        tag_name = str(payload.get("tag_name") or "").strip()
        if not tag_name:
            raise RuntimeError("Release terbaru belum ditemukan di GitHub.")

        return {
            "tag_name": tag_name,
            "name": str(payload.get("name") or tag_name).strip(),
            "html_url": str(payload.get("html_url") or LATEST_RELEASE_URL).strip(),
            "published_at": str(payload.get("published_at") or "").strip(),
        }

    def finish_update_check(
        self,
        release: dict[str, str] | None,
        show_current_message: bool,
        error_message: str,
    ) -> None:
        self.update_check_in_progress = False

        if release is None:
            if show_current_message:
                messagebox.showwarning(
                    "Gagal cek update",
                    (
                        "Aplikasi belum bisa mengecek update dari GitHub.\n\n"
                        f"Detail: {error_message}"
                    ),
                )
                self.status_text.set("Gagal mengecek update. Coba lagi nanti.")
            return

        latest_tag = release["tag_name"]
        if self.is_newer_version(latest_tag, APP_VERSION):
            if not show_current_message and self.update_notified_tag == latest_tag:
                return
            self.update_notified_tag = latest_tag
            self.show_update_available_modal(release)
            return

        if show_current_message:
            messagebox.showinfo(
                "Aplikasi sudah terbaru",
                f"Kamu sudah memakai versi terbaru: v{APP_VERSION}",
            )
            self.status_text.set(f"Aplikasi sudah terbaru: v{APP_VERSION}")

    def show_update_available_modal(self, release: dict[str, str]) -> None:
        latest_tag = release["tag_name"]
        latest_name = release["name"]
        release_url = release["html_url"] or LATEST_RELEASE_URL
        message = (
            "Update baru tersedia.\n\n"
            f"Versi kamu: v{APP_VERSION}\n"
            f"Versi terbaru: {latest_tag}\n"
            f"Release: {latest_name}\n\n"
            "Buka halaman release GitHub untuk download sekarang?"
        )
        should_open = messagebox.askyesno("Update tersedia", message)
        self.status_text.set(f"Update tersedia: {latest_tag}")
        if should_open:
            webbrowser.open(release_url)

    def is_newer_version(self, latest_tag: str, current_version: str) -> bool:
        latest = self.parse_version_parts(latest_tag)
        current = self.parse_version_parts(current_version)
        if latest and current:
            return latest > current
        return latest_tag.strip().lower().lstrip("v") != current_version.strip().lower().lstrip("v")

    def parse_version_parts(self, value: str) -> tuple[int, ...]:
        cleaned = value.strip().lower().lstrip("v")
        parts = re.findall(r"\d+", cleaned)
        return tuple(int(part) for part in parts)

    def _configure_theme(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "App.TFrame",
            background="#eef3f7",
        )
        style.configure(
            "Panel.TFrame",
            background="#ffffff",
            bordercolor="#d7e2ea",
            borderwidth=1,
            relief="solid",
        )
        style.configure(
            "Plain.TFrame",
            background="#ffffff",
            borderwidth=0,
            relief="flat",
        )
        style.configure(
            "Header.TLabel",
            background="#eef3f7",
            foreground="#101820",
            font=("Segoe UI", 24, "bold"),
        )
        style.configure(
            "Subheader.TLabel",
            background="#eef3f7",
            foreground="#50616b",
            font=("Segoe UI", 10),
        )
        style.configure(
            "PanelTitle.TLabel",
            background="#ffffff",
            foreground="#101820",
            font=("Segoe UI", 12, "bold"),
        )
        style.configure(
            "Body.TLabel",
            background="#ffffff",
            foreground="#46534d",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Muted.TLabel",
            background="#ffffff",
            foreground="#6f7b75",
            font=("Segoe UI", 9),
        )
        style.configure(
            "Primary.TButton",
            background="#0f766e",
            foreground="#ffffff",
            borderwidth=0,
            focusthickness=0,
            font=("Segoe UI", 10, "bold"),
            padding=(16, 11),
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#115e59"), ("disabled", "#9fb8b2")],
            foreground=[("disabled", "#eef4f2")],
        )
        style.configure(
            "Secondary.TButton",
            background="#edf3f6",
            foreground="#101820",
            borderwidth=0,
            focusthickness=0,
            font=("Segoe UI", 10),
            padding=(14, 8),
        )
        style.map("Secondary.TButton", background=[("active", "#e0eaf0")])
        style.configure(
            "Link.TButton",
            background="#eef3f7",
            foreground="#0f766e",
            borderwidth=0,
            focusthickness=0,
            font=("Segoe UI", 9, "bold"),
            padding=(10, 6),
        )
        style.map("Link.TButton", background=[("active", "#dde8ee")])
        style.configure(
            "Field.TEntry",
            fieldbackground="#fbfdfe",
            background="#fbfdfe",
            foreground="#101820",
            bordercolor="#cfdae2",
            lightcolor="#cfdae2",
            darkcolor="#cfdae2",
            insertcolor="#101820",
            padding=(10, 8),
        )
        style.map("Field.TEntry", bordercolor=[("focus", "#0f766e")])
        style.configure(
            "Clean.TCheckbutton",
            background="#ffffff",
            foreground="#46534d",
            font=("Segoe UI", 10),
            padding=(0, 2),
        )
        style.map("Clean.TCheckbutton", background=[("active", "#ffffff")])
        style.configure(
            "Clean.TRadiobutton",
            background="#ffffff",
            foreground="#46534d",
            font=("Segoe UI", 10),
            padding=(0, 3),
        )
        style.map("Clean.TRadiobutton", background=[("active", "#ffffff")])
        style.configure(
            "File.Treeview",
            background="#fbfdfe",
            fieldbackground="#fbfdfe",
            foreground="#101820",
            bordercolor="#cfdae2",
            borderwidth=1,
            rowheight=25,
            font=("Segoe UI", 10),
        )
        style.configure(
            "File.Treeview.Heading",
            background="#edf3f6",
            foreground="#46534d",
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "File.Treeview",
            background=[("selected", "#0f766e")],
            foreground=[("selected", "#ffffff")],
        )
        style.configure(
            "Drag.Treeview",
            background="#ecfdf8",
            fieldbackground="#ecfdf8",
            foreground="#101820",
            bordercolor="#0f766e",
            borderwidth=1,
            rowheight=25,
            font=("Segoe UI", 10),
        )
        style.map(
            "Drag.Treeview",
            background=[("selected", "#0f766e")],
            foreground=[("selected", "#ffffff")],
        )
        style.configure(
            "Disabled.TButton",
            background="#d6ded9",
            foreground="#7d8a84",
            borderwidth=0,
            focusthickness=0,
            font=("Segoe UI", 10),
            padding=(14, 8),
        )
        style.configure("TProgressbar", background="#0f766e", troughcolor="#dce6ec")

    def _build_layout(self) -> None:
        self.container = ttk.Frame(self.root, style="App.TFrame", padding=26)
        container = self.container
        container.pack(fill="both", expand=True)
        container.columnconfigure(0, weight=0, minsize=360)
        container.columnconfigure(1, weight=1)
        container.rowconfigure(1, weight=1)

        header = ttk.Frame(container, style="App.TFrame")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 20))
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=0)

        ttk.Label(header, text="Playlist Generator", style="Header.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            header,
            text="Pilih folder atau file, susun otomatis, lalu copy ke folder tujuan dengan nomor urut.",
            style="Subheader.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        repo_actions = ttk.Frame(header, style="App.TFrame")
        repo_actions.grid(row=0, column=1, rowspan=2, sticky="ne")
        ttk.Label(
            repo_actions,
            text=f"v{APP_VERSION}",
            style="Subheader.TLabel",
        ).grid(row=0, column=0, sticky="e", padx=(0, 8))
        ttk.Button(
            repo_actions,
            text="GitHub",
            style="Link.TButton",
            command=self.open_repository,
        ).grid(row=0, column=1, sticky="e", padx=(0, 6))
        ttk.Button(
            repo_actions,
            text="Star Repo",
            style="Link.TButton",
            command=self.open_repository,
        ).grid(row=0, column=2, sticky="e", padx=(0, 6))
        ttk.Button(
            repo_actions,
            text="Latest Release",
            style="Link.TButton",
            command=self.open_latest_release,
        ).grid(row=0, column=3, sticky="e", padx=(0, 6))
        ttk.Button(
            repo_actions,
            text="Cek Update",
            style="Link.TButton",
            command=self.check_for_updates_manual,
        ).grid(row=0, column=4, sticky="e")

        self.left_panel = ttk.Frame(container, style="Panel.TFrame", padding=20)
        self.left_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 18))
        self.left_panel.columnconfigure(0, weight=1)
        self.left_panel.rowconfigure(0, weight=1)

        self.right_panel = ttk.Frame(container, style="Panel.TFrame", padding=20)
        self.right_panel.grid(row=1, column=1, sticky="nsew")
        self.right_panel.columnconfigure(0, weight=1)
        self.right_panel.rowconfigure(3, weight=1)

        self._build_settings()
        self._build_song_view()
        self._build_empty_state()

        footer = ttk.Frame(container, style="App.TFrame")
        footer.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(14, 0))
        footer.columnconfigure(0, weight=1)

        ttk.Label(footer, textvariable=self.status_text, style="Subheader.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(footer, textvariable=self.progress_text, style="Subheader.TLabel").grid(
            row=0, column=1, sticky="e"
        )
        self.progress = ttk.Progressbar(footer, mode="determinate")
        self.progress.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.update_source_view()

    def _build_settings(self) -> None:
        scroll_area = ttk.Frame(self.left_panel, style="Plain.TFrame")
        scroll_area.grid(row=0, column=0, sticky="nsew")
        scroll_area.columnconfigure(0, weight=1)
        scroll_area.rowconfigure(0, weight=1)

        self.settings_canvas = Canvas(
            scroll_area,
            bg="#ffffff",
            highlightthickness=0,
            borderwidth=0,
        )
        self.settings_canvas.grid(row=0, column=0, sticky="nsew")

        settings_scrollbar = ttk.Scrollbar(
            scroll_area,
            orient="vertical",
            command=self.settings_canvas.yview,
        )
        settings_scrollbar.grid(row=0, column=1, sticky="ns", padx=(8, 0))
        self.settings_canvas.configure(yscrollcommand=settings_scrollbar.set)

        settings_panel = ttk.Frame(self.settings_canvas, style="Plain.TFrame")
        self.settings_window = self.settings_canvas.create_window(
            (0, 0),
            window=settings_panel,
            anchor="nw",
        )
        settings_panel.columnconfigure(0, weight=1)

        settings_panel.bind(
            "<Configure>",
            lambda _event: self.settings_canvas.configure(
                scrollregion=self.settings_canvas.bbox("all")
            ),
        )
        self.settings_canvas.bind(
            "<Configure>",
            lambda event: self.settings_canvas.itemconfigure(
                self.settings_window,
                width=event.width,
            ),
        )
        self.settings_canvas.bind("<MouseWheel>", self.on_settings_mousewheel)
        self.settings_canvas.bind("<Button-4>", self.on_settings_mousewheel)
        self.settings_canvas.bind("<Button-5>", self.on_settings_mousewheel)

        ttk.Label(settings_panel, text="Sumber File", style="PanelTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        source_row = ttk.Frame(settings_panel, style="Plain.TFrame")
        source_row.grid(row=1, column=0, sticky="ew", pady=(10, 8))
        source_row.columnconfigure(0, weight=1)
        source_entry = ttk.Entry(
            source_row,
            textvariable=self.source_folder,
            style="Field.TEntry",
            font=("Segoe UI", 9),
            state="readonly",
        )
        source_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ttk.Button(
            source_row,
            text="Pilih",
            style="Secondary.TButton",
            command=self.choose_source_folder,
        ).grid(row=0, column=1, sticky="e")

        source_actions = ttk.Frame(settings_panel, style="Plain.TFrame")
        source_actions.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        source_actions.columnconfigure(0, weight=1)
        source_actions.columnconfigure(1, weight=1)
        ttk.Button(
            source_actions,
            text="Tambah Folder",
            style="Secondary.TButton",
            command=self.add_source_folder,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(
            source_actions,
            text="Tambah File",
            style="Secondary.TButton",
            command=self.add_source_files,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        source_list_frame = Frame(settings_panel, bg="#ffffff")
        source_list_frame.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        source_list_frame.columnconfigure(0, weight=1)
        self.source_tree = ttk.Treeview(
            source_list_frame,
            show="tree",
            height=4,
            selectmode="extended",
            style="File.Treeview",
        )
        self.source_tree.grid(row=0, column=0, sticky="ew")
        source_scrollbar = ttk.Scrollbar(
            source_list_frame,
            orient="vertical",
            command=self.source_tree.yview,
        )
        source_scrollbar.grid(row=0, column=1, sticky="ns")
        self.source_tree.configure(yscrollcommand=source_scrollbar.set)

        source_manage = ttk.Frame(settings_panel, style="Plain.TFrame")
        source_manage.grid(row=4, column=0, sticky="ew", pady=(0, 16))
        source_manage.columnconfigure(0, weight=1)
        source_manage.columnconfigure(1, weight=1)
        ttk.Button(
            source_manage,
            text="Hapus Pilihan",
            style="Secondary.TButton",
            command=self.remove_selected_sources,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        ttk.Button(
            source_manage,
            text="Hapus Semua",
            style="Secondary.TButton",
            command=self.clear_sources,
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        ttk.Checkbutton(
            settings_panel,
            text="Scan subfolder juga",
            variable=self.recursive_scan,
            command=self.refresh_songs,
            style="Clean.TCheckbutton",
        ).grid(row=5, column=0, sticky="w", pady=(0, 20))

        ttk.Label(settings_panel, text="Jenis & Jumlah File", style="PanelTitle.TLabel").grid(
            row=6, column=0, sticky="w"
        )
        filter_box = ttk.Frame(settings_panel, style="Plain.TFrame")
        filter_box.grid(row=7, column=0, sticky="ew", pady=(10, 12))
        filter_box.columnconfigure(1, weight=1)
        for index, (key, (label, _extensions)) in enumerate(FILE_TYPES.items()):
            ttk.Checkbutton(
                filter_box,
                text=label,
                variable=self.type_filters[key],
                command=self.apply_filters,
                style="Clean.TCheckbutton",
            ).grid(row=index, column=0, sticky="w", pady=4, padx=(0, 10))

            slider = Scale(
                filter_box,
                from_=0,
                to=0,
                orient="horizontal",
                variable=self.type_counts[key],
                command=lambda _value, item_key=key: self.on_type_count_change(item_key),
                bg="#ffffff",
                fg="#101820",
                troughcolor="#dce6ec",
                highlightthickness=0,
                activebackground="#0f766e",
                font=("Segoe UI", 8),
                showvalue=False,
            )
            slider.grid(row=index, column=1, sticky="ew", pady=4, padx=(0, 8))
            self.count_sliders[key] = slider

            spinbox = Spinbox(
                filter_box,
                from_=0,
                to=0,
                textvariable=self.type_counts[key],
                width=4,
                command=lambda item_key=key: self.on_type_count_change(item_key),
                font=("Segoe UI", 9),
                relief="flat",
                bg="#fbfdfe",
                fg="#101820",
                buttonbackground="#edf3f6",
                highlightthickness=1,
                highlightbackground="#cfdae2",
                highlightcolor="#0f766e",
            )
            spinbox.grid(row=index, column=2, sticky="e", pady=4, ipady=4)
            self.count_spinboxes[key] = spinbox

        ttk.Label(settings_panel, textvariable=self.counts_text, style="Muted.TLabel").grid(
            row=8, column=0, sticky="w", pady=(0, 18)
        )

        ttk.Label(settings_panel, text="Cara Memilih", style="PanelTitle.TLabel").grid(
            row=9, column=0, sticky="w"
        )
        mode_box = ttk.Frame(settings_panel, style="Plain.TFrame")
        mode_box.grid(row=10, column=0, sticky="ew", pady=(10, 20))
        for index, (label, value) in enumerate(
            [
                ("Random", "random"),
                ("Urut sesuai nama file", "alphabetical"),
                ("Pilih manual dari daftar", "manual"),
            ]
        ):
            ttk.Radiobutton(
                mode_box,
                text=label,
                value=value,
                variable=self.mode,
                command=self.update_selection_preview,
                style="Clean.TRadiobutton",
            ).grid(row=index, column=0, sticky="w", pady=3)

        ttk.Label(settings_panel, text="Folder Tujuan", style="PanelTitle.TLabel").grid(
            row=11, column=0, sticky="w"
        )
        destination_row = ttk.Frame(settings_panel, style="Plain.TFrame")
        destination_row.grid(row=12, column=0, sticky="ew", pady=(10, 20))
        destination_row.columnconfigure(0, weight=1)
        destination_entry = ttk.Entry(
            destination_row,
            textvariable=self.destination_folder,
            style="Field.TEntry",
            font=("Segoe UI", 9),
        )
        destination_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ttk.Button(
            destination_row,
            text="Pilih",
            style="Secondary.TButton",
            command=self.choose_destination_folder,
        ).grid(row=0, column=1, sticky="e")

        action_row = ttk.Frame(self.left_panel, style="Plain.TFrame")
        action_row.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        action_row.columnconfigure(0, weight=1)
        self.generate_button = ttk.Button(
            action_row,
            text="Generate & Copy",
            style="Primary.TButton",
            command=self.generate_playlist,
        )
        self.generate_button.grid(row=0, column=0, sticky="ew")

        if DND_AVAILABLE:
            self.register_drop_target(source_row)
            self.register_drop_target(source_list_frame)
            self.register_drop_target(self.source_tree)

        self.bind_settings_mousewheel(settings_panel)

    def bind_settings_mousewheel(self, widget) -> None:
        if not isinstance(widget, (ttk.Treeview, Scale, Spinbox)):
            widget.bind("<MouseWheel>", self.on_settings_mousewheel, add="+")
            widget.bind("<Button-4>", self.on_settings_mousewheel, add="+")
            widget.bind("<Button-5>", self.on_settings_mousewheel, add="+")
        for child in widget.winfo_children():
            self.bind_settings_mousewheel(child)

    def on_settings_mousewheel(self, event) -> str:
        if not hasattr(self, "settings_canvas"):
            return "break"
        if getattr(event, "num", None) == 4:
            delta = -1
        elif getattr(event, "num", None) == 5:
            delta = 1
        else:
            delta = -1 * int(event.delta / 120)
        self.settings_canvas.yview_scroll(delta, "units")
        return "break"

    def _build_song_view(self) -> None:
        title_row = ttk.Frame(self.right_panel, style="Plain.TFrame")
        title_row.grid(row=0, column=0, sticky="ew")
        title_row.columnconfigure(0, weight=1)

        ttk.Label(title_row, text="Daftar File", style="PanelTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.song_total_label = ttk.Label(
            title_row, text="0 file", style="Muted.TLabel"
        )
        self.song_total_label.grid(row=0, column=1, sticky="e")

        toolbar = ttk.Frame(self.right_panel, style="Plain.TFrame")
        toolbar.grid(row=1, column=0, sticky="ew", pady=(12, 10))
        toolbar.columnconfigure(0, weight=1)
        ttk.Button(
            toolbar,
            text="Refresh",
            style="Secondary.TButton",
            command=self.refresh_songs,
        ).grid(row=0, column=1, padx=(8, 0), sticky="e")
        ttk.Button(
            toolbar,
            text="Acak Preview",
            style="Secondary.TButton",
            command=self.shuffle_preview,
        ).grid(row=0, column=2, padx=(8, 0), sticky="e")

        ttk.Label(
            self.right_panel,
            text="Mode manual: klik file pada daftar. Mode random atau urut akan membuat preview otomatis.",
            style="Muted.TLabel",
        ).grid(row=2, column=0, sticky="w", pady=(0, 8))

        tree_frame = Frame(self.right_panel, bg="#ffffff")
        tree_frame.grid(row=3, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self.song_tree = ttk.Treeview(
            tree_frame,
            show="tree",
            selectmode="extended",
            style="File.Treeview",
        )
        self.song_tree.grid(row=0, column=0, sticky="nsew")
        self.song_tree.bind("<<TreeviewSelect>>", lambda _event: self.on_manual_select())

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.song_tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.song_tree.configure(yscrollcommand=scrollbar.set)

        preview_header = ttk.Frame(self.right_panel, style="Plain.TFrame")
        preview_header.grid(row=4, column=0, sticky="ew", pady=(16, 8))
        preview_header.columnconfigure(0, weight=1)
        ttk.Label(preview_header, text="Preview Output", style="PanelTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.preview_summary_label = ttk.Label(
            preview_header,
            text="0 file siap",
            style="Muted.TLabel",
        )
        self.preview_summary_label.grid(row=0, column=1, sticky="e", padx=(0, 10))
        ttk.Button(
            preview_header,
            text="Lock Pilihan",
            style="Secondary.TButton",
            command=self.toggle_preview_locks,
        ).grid(row=0, column=2, sticky="e", padx=(0, 8))
        ttk.Button(
            preview_header,
            text="Unlock Semua",
            style="Secondary.TButton",
            command=self.clear_preview_locks,
        ).grid(row=0, column=3, sticky="e")

        ttk.Label(
            self.right_panel,
            text="Drag file pada preview untuk mengatur urutan. Lock menjaga file tetap di posisi itu saat preview diacak ulang.",
            style="Muted.TLabel",
        ).grid(row=5, column=0, sticky="w", pady=(0, 8))

        preview_frame = Frame(self.right_panel, bg="#ffffff")
        preview_frame.grid(row=6, column=0, sticky="ew")
        preview_frame.columnconfigure(0, weight=1)

        self.preview_tree = ttk.Treeview(
            preview_frame,
            show="tree",
            height=8,
            selectmode="extended",
            style="File.Treeview",
        )
        self.preview_tree.grid(row=0, column=0, sticky="ew")
        self.preview_tree.bind("<ButtonPress-1>", self.on_preview_drag_start)
        self.preview_tree.bind("<B1-Motion>", self.on_preview_drag_motion)
        self.preview_tree.bind("<ButtonRelease-1>", self.on_preview_drag_release)
        self.preview_tree.tag_configure("dragging", background="#d7f3ed", foreground="#101820")
        self.preview_tree.tag_configure("drop-target", background="#bfe8df", foreground="#101820")
        self.preview_tree.tag_configure("moved", background="#e0f5f0", foreground="#101820")

        preview_scrollbar = ttk.Scrollbar(
            preview_frame,
            orient="vertical",
            command=self.preview_tree.yview,
        )
        preview_scrollbar.grid(row=0, column=1, sticky="ns")
        self.preview_tree.configure(yscrollcommand=preview_scrollbar.set)

        timestamp_header = ttk.Frame(self.right_panel, style="Plain.TFrame")
        timestamp_header.grid(row=7, column=0, sticky="ew", pady=(16, 8))
        timestamp_header.columnconfigure(0, weight=1)
        ttk.Label(
            timestamp_header,
            text="Timestamp YouTube",
            style="PanelTitle.TLabel",
        ).grid(row=0, column=0, sticky="w")
        self.copy_timestamp_button = ttk.Button(
            timestamp_header,
            text="Copy Timestamp",
            style="Secondary.TButton",
            command=self.copy_timestamp_to_clipboard,
            state="disabled",
        )
        self.copy_timestamp_button.grid(row=0, column=1, sticky="e")

        timestamp_frame = Frame(self.right_panel, bg="#ffffff")
        timestamp_frame.grid(row=8, column=0, sticky="ew")
        timestamp_frame.columnconfigure(0, weight=1)

        self.timestamp_box = Text(
            timestamp_frame,
            height=8,
            wrap="none",
            borderwidth=0,
            highlightthickness=1,
            highlightcolor="#cfdae2",
            highlightbackground="#cfdae2",
            bg="#fbfdfe",
            fg="#101820",
            font=("Consolas", 9),
        )
        self.timestamp_box.grid(row=0, column=0, sticky="ew")
        self.timestamp_box.configure(state="disabled")

        timestamp_scrollbar = ttk.Scrollbar(
            timestamp_frame,
            orient="vertical",
            command=self.timestamp_box.yview,
        )
        timestamp_scrollbar.grid(row=0, column=1, sticky="ns")
        self.timestamp_box.configure(yscrollcommand=timestamp_scrollbar.set)
        self.set_timestamp_text("Timestamp akan tampil otomatis setelah Preview Output berisi audio atau video.")

    def _build_empty_state(self) -> None:
        self.empty_panel = ttk.Frame(self.container, style="Panel.TFrame", padding=34)
        self.empty_panel.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.empty_panel.columnconfigure(0, weight=1)
        self.empty_panel.rowconfigure(0, weight=1)

        drop_zone = Frame(
            self.empty_panel,
            bg="#fbfdfe",
            highlightthickness=1,
            highlightbackground="#cfdae2",
            highlightcolor="#0f766e",
        )
        drop_zone.grid(row=0, column=0, sticky="nsew")
        drop_zone.columnconfigure(0, weight=1)
        drop_zone.rowconfigure(0, weight=1)

        content = ttk.Frame(drop_zone, style="Plain.TFrame", padding=28)
        content.grid(row=0, column=0)

        ttk.Label(
            content,
            text="Tarik folder atau file ke sini",
            style="PanelTitle.TLabel",
            font=("Segoe UI", 18, "bold"),
        ).grid(row=0, column=0, columnspan=2, pady=(0, 8))

        dnd_message = (
            "Mendukung musik, gambar, video, dan PDF."
            if DND_AVAILABLE
            else "Drag & drop aktif setelah dependency tkinterdnd2 tersedia."
        )
        ttk.Label(
            content,
            text=dnd_message,
            style="Muted.TLabel",
        ).grid(row=1, column=0, columnspan=2, pady=(0, 22))

        ttk.Button(
            content,
            text="Pilih Folder",
            style="Primary.TButton",
            command=self.choose_source_folder,
        ).grid(row=2, column=0, sticky="ew", padx=(0, 8))
        ttk.Button(
            content,
            text="Pilih File",
            style="Secondary.TButton",
            command=self.choose_source_files,
        ).grid(row=2, column=1, sticky="ew", padx=(8, 0))

        if DND_AVAILABLE:
            self.register_drop_target(drop_zone)
            self.register_drop_target(content)
            self.register_drop_target(self.empty_panel)

    def choose_source_folder(self) -> None:
        folder = filedialog.askdirectory(title="Pilih folder yang berisi file")
        if folder:
            self.set_source_paths([Path(folder)], replace=True)

    def add_source_folder(self) -> None:
        folder = filedialog.askdirectory(title="Tambah folder sumber")
        if folder:
            self.set_source_paths([Path(folder)], replace=False)

    def choose_source_files(self) -> None:
        files = filedialog.askopenfilenames(
            title="Pilih file",
            filetypes=[
                ("File yang didukung", self.supported_filetype_pattern()),
                ("Semua file", "*.*"),
            ],
        )
        if files:
            self.set_source_paths([Path(file) for file in files], replace=True)

    def add_source_files(self) -> None:
        files = filedialog.askopenfilenames(
            title="Tambah file sumber",
            filetypes=[
                ("File yang didukung", self.supported_filetype_pattern()),
                ("Semua file", "*.*"),
            ],
        )
        if files:
            self.set_source_paths([Path(file) for file in files], replace=False)

    def choose_destination_folder(self) -> None:
        folder = filedialog.askdirectory(title="Pilih folder tujuan playlist")
        if folder:
            self.destination_folder.set(folder)

    def ask_generate_destination(self) -> Path | None:
        previous_destination = self.destination_folder.get().strip()
        options = {"title": "Pilih folder tujuan untuk hasil generate"}
        if previous_destination and Path(previous_destination).is_dir():
            options["initialdir"] = previous_destination

        folder = filedialog.askdirectory(**options)
        if not folder:
            self.status_text.set("Generate dibatalkan. Folder tujuan belum dipilih.")
            return None

        destination = Path(folder)
        if not destination.exists() or not destination.is_dir():
            messagebox.showwarning("Folder tujuan belum valid", "Pilih folder tujuan yang valid.")
            self.status_text.set("Folder tujuan belum valid.")
            return None

        self.destination_folder.set(str(destination))
        return destination

    def register_drop_target(self, widget) -> None:
        try:
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self.handle_drop)
        except Exception:
            pass

    def handle_drop(self, event) -> None:
        paths = [Path(path) for path in self.root.tk.splitlist(event.data)]
        if not paths:
            return

        self.set_source_paths(paths, replace=not self.source_paths)

    def set_source_paths(self, paths: list[Path], replace: bool) -> None:
        current = [] if replace else self.source_paths.copy()
        current.extend(paths)

        unique_paths: list[Path] = []
        seen: set[str] = set()
        for path in current:
            key = str(path.resolve()) if path.exists() else str(path)
            if key in seen:
                continue
            seen.add(key)
            unique_paths.append(path)

        self.source_paths = unique_paths
        self.dropped_paths = unique_paths
        self.update_source_summary()
        self.refresh_songs()

    def update_source_summary(self) -> None:
        if not self.source_paths:
            self.source_folder.set("")
        elif len(self.source_paths) == 1:
            self.source_folder.set(str(self.source_paths[0]))
        else:
            folder_count = sum(1 for path in self.source_paths if path.is_dir())
            file_count = sum(1 for path in self.source_paths if path.is_file())
            parts = []
            if folder_count:
                parts.append(f"{folder_count} folder")
            if file_count:
                parts.append(f"{file_count} file")
            self.source_folder.set(" + ".join(parts) + " dipilih")

        self.update_source_tree()

    def update_source_tree(self) -> None:
        if not hasattr(self, "source_tree"):
            return

        self.source_tree.delete(*self.source_tree.get_children())
        for index, path in enumerate(self.source_paths):
            label = "Folder" if path.is_dir() else "File" if path.is_file() else "Tidak valid"
            self.source_tree.insert(
                "",
                "end",
                iid=f"source_path_{index}",
                text=f"{label}: {path}",
            )

    def remove_selected_sources(self) -> None:
        selected_indexes = sorted(
            (
                int(item_id.replace("source_path_", ""))
                for item_id in self.source_tree.selection()
                if item_id.startswith("source_path_")
            ),
            reverse=True,
        )
        if not selected_indexes:
            self.status_text.set("Pilih sumber yang ingin dihapus dari daftar.")
            return

        for index in selected_indexes:
            if 0 <= index < len(self.source_paths):
                self.source_paths.pop(index)

        self.dropped_paths = self.source_paths.copy()
        self.update_source_summary()
        self.refresh_songs()

    def clear_sources(self) -> None:
        if not self.source_paths:
            self.status_text.set("Belum ada sumber file yang dipilih.")
            return

        self.source_paths = []
        self.dropped_paths = []
        self.songs = []
        self.selected_songs = []
        self.locked_preview_keys.clear()
        self.custom_preview_order.clear()
        self.update_source_summary()
        self.update_song_list()
        self.update_counts()
        self.update_preview_tree([])
        self.reset_timestamp_box()
        self.update_source_view()
        self.status_text.set("Semua sumber file sudah dihapus.")

    def update_source_view(self) -> None:
        has_source = bool(self.source_paths)
        if has_source:
            self.empty_panel.grid_remove()
            self.left_panel.grid()
            self.right_panel.grid()
        else:
            self.left_panel.grid_remove()
            self.right_panel.grid_remove()
            self.empty_panel.grid()

    @staticmethod
    def supported_filetype_pattern() -> str:
        return " ".join(f"*{extension}" for extension in sorted(SUPPORTED_EXTENSIONS))

    @staticmethod
    def get_category(path: Path) -> str | None:
        suffix = path.suffix.lower()
        for key, (_label, extensions) in FILE_TYPES.items():
            if suffix in extensions:
                return key
        return None

    def collect_files_from_path(self, path: Path) -> list[Path]:
        if path.is_file():
            return [path] if self.get_category(path) else []
        if not path.is_dir():
            return []

        pattern = "**/*" if self.recursive_scan.get() else "*"
        return [
            item
            for item in path.glob(pattern)
            if item.is_file() and self.get_category(item)
        ]

    def refresh_songs(self) -> None:
        files = []
        valid_sources = [path for path in self.source_paths if path.exists()]
        for path in valid_sources:
            files.extend(self.collect_files_from_path(path))

        if not self.source_paths or not valid_sources:
            self.songs = []
            self.update_song_list()
            self.update_counts()
            self.update_source_view()
            self.status_text.set("Pilih folder atau file yang valid.")
            return

        if not files:
            self.songs = []
            self.update_song_list()
            self.update_counts()
            self.update_source_view()
            self.status_text.set("Belum ada file musik, gambar, video, atau PDF yang ditemukan.")
            return

        unique_files = sorted(set(files), key=lambda item: item.name.lower())
        self.songs = [
            Song(path, self.get_category(path) or "music")
            for path in unique_files
        ]
        available_keys = {self.song_key(song) for song in self.songs}
        self.locked_preview_keys.intersection_update(available_keys)
        self.custom_preview_order = [
            key for key in self.custom_preview_order if key in available_keys
        ]

        self.update_song_list()
        self.update_counts()
        self.sync_count_controls(default_if_empty=True)
        self.update_selection_preview()
        self.update_source_view()
        self.status_text.set(
            f"Ditemukan {len(self.songs)} file yang didukung dari {len(valid_sources)} sumber."
        )

    def update_song_list(self) -> None:
        self.song_tree.delete(*self.song_tree.get_children())
        self.song_tree_items.clear()

        filtered = self.filtered_songs()
        grouped = {key: [] for key in FILE_TYPES}
        for song in filtered:
            grouped[song.category].append(song)

        item_index = 0
        for key, songs in grouped.items():
            if not songs:
                continue

            label = FILE_TYPES[key][0]
            parent_id = f"source_{key}"
            self.song_tree.insert("", "end", iid=parent_id, text=f"{label} ({len(songs)})", open=True)

            for song in songs:
                item_id = f"song_{item_index}"
                self.song_tree_items[item_id] = song
                self.song_tree.insert(parent_id, "end", iid=item_id, text=song.name)
                item_index += 1

        self.song_total_label.configure(text=f"{len(filtered)} file ditampilkan")

    @staticmethod
    def song_key(song: Song) -> str:
        return str(song.path)

    def song_by_key(self) -> dict[str, Song]:
        return {self.song_key(song): song for song in self.filtered_songs()}

    def update_counts(self) -> None:
        counts = {key: 0 for key in FILE_TYPES}
        for song in self.songs:
            counts[song.category] += 1

        summary = "  |  ".join(
            f"{label}: {counts[key]}"
            for key, (label, _extensions) in FILE_TYPES.items()
        )
        self.counts_text.set(summary if self.songs else "")

    def filtered_songs(self) -> list[Song]:
        active_types = {
            key
            for key, enabled in self.type_filters.items()
            if enabled.get()
        }
        return [song for song in self.songs if song.category in active_types]

    def songs_by_category(self) -> dict[str, list[Song]]:
        grouped = {key: [] for key in FILE_TYPES}
        for song in self.songs:
            grouped[song.category].append(song)
        return grouped

    def available_count(self, category: str) -> int:
        return sum(1 for song in self.songs if song.category == category)

    def desired_counts(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for key in FILE_TYPES:
            if not self.type_filters[key].get():
                counts[key] = 0
                continue
            try:
                requested = int(self.type_counts[key].get())
            except Exception:
                requested = 0
            counts[key] = max(0, min(requested, self.available_count(key)))
        return counts

    def get_total_count(self) -> int:
        return sum(self.desired_counts().values())

    def sync_count_controls(self, default_if_empty: bool = False) -> None:
        for key in FILE_TYPES:
            available = self.available_count(key)
            self.count_sliders[key].configure(to=available)
            self.count_spinboxes[key].configure(to=available)
            current = self.safe_int(self.type_counts[key].get())
            if current > available:
                self.type_counts[key].set(available)
            elif current < 0:
                self.type_counts[key].set(0)

        if default_if_empty and self.songs and self.get_total_count() == 0:
            for key in FILE_TYPES:
                available = self.available_count(key)
                if available:
                    self.type_filters[key].set(True)
                    self.type_counts[key].set(min(8, available))
                    break

    @staticmethod
    def safe_int(value: object) -> int:
        try:
            return int(value)
        except Exception:
            return 0

    def on_manual_select(self) -> None:
        if self.mode.get() == "manual":
            self.update_selection_preview()

    def apply_filters(self) -> None:
        self.update_song_list()
        self.sync_count_controls()
        available_keys = {self.song_key(song) for song in self.filtered_songs()}
        self.locked_preview_keys.intersection_update(available_keys)
        self.custom_preview_order = [
            key for key in self.custom_preview_order if key in available_keys
        ]
        self.update_selection_preview()

    def on_type_count_change(self, category: str) -> None:
        available = self.available_count(category)
        current = self.safe_int(self.type_counts[category].get())
        if current > available:
            self.type_counts[category].set(available)
        elif current < 0:
            self.type_counts[category].set(0)
        if current > 0 and not self.type_filters[category].get():
            self.type_filters[category].set(True)
            self.update_song_list()
        self.update_selection_preview()

    def shuffle_preview(self) -> None:
        if self.mode.get() != "random":
            self.mode.set("random")
        self.update_selection_preview(force_shuffle=True)

    def update_selection_preview(self, force_shuffle: bool = False) -> None:
        del force_shuffle
        mode = self.mode.get()
        available = self.filtered_songs()
        grouped = self.songs_by_category()
        quotas = self.desired_counts()
        total_count = sum(quotas.values())

        if mode == "manual":
            picked_by_type = {key: 0 for key in FILE_TYPES}
            selected = []
            selected_items = set(self.song_tree.selection())
            for item_id, song in self.song_tree_items.items():
                if item_id not in selected_items:
                    continue
                if picked_by_type[song.category] < quotas[song.category]:
                    selected.append(song)
                    picked_by_type[song.category] += 1
        elif mode == "alphabetical":
            selected = []
            for key in FILE_TYPES:
                selected.extend(grouped[key][: quotas[key]])
            selected.sort(key=lambda song: song.name.lower())
        else:
            selected = []
            for key in FILE_TYPES:
                category_files = grouped[key]
                quota = quotas[key]
                if quota:
                    selected.extend(random.sample(category_files, quota))
            random.shuffle(selected)

        selected = self.apply_locked_preview(selected, quotas)
        self.selected_songs = selected
        self.custom_preview_order = [self.song_key(song) for song in selected]
        self.update_preview_tree(selected)

        if not self.songs:
            self.status_text.set("Belum ada file yang bisa dipilih.")
        elif not available:
            self.status_text.set("Tidak ada file yang cocok dengan filter aktif.")
        elif total_count == 0:
            self.status_text.set("Atur jumlah file minimal 1 pada salah satu jenis file.")
        elif mode == "manual" and len(selected) < total_count:
            self.status_text.set(f"Pilih {total_count} file sesuai kuota jenis file.")
        else:
            self.status_text.set(f"Siap membuat output berisi {len(selected)} file.")

    def apply_locked_preview(
        self,
        candidate_songs: list[Song],
        quotas: dict[str, int],
    ) -> list[Song]:
        if sum(quotas.values()) <= 0 or not self.locked_preview_keys:
            return candidate_songs

        available = self.song_by_key()
        locked_by_key = {
            key: available[key]
            for key in self.locked_preview_keys
            if key in available and quotas.get(available[key].category, 0) > 0
        }
        if not locked_by_key:
            return candidate_songs

        previous_by_category = {key: [] for key in FILE_TYPES}
        candidate_by_category = {key: [] for key in FILE_TYPES}
        available_by_category = {key: [] for key in FILE_TYPES}

        for song in self.selected_songs:
            previous_by_category[song.category].append(song)
        for song in candidate_songs:
            candidate_by_category[song.category].append(song)
        for song in available.values():
            available_by_category[song.category].append(song)

        result: list[Song] = []
        for category in FILE_TYPES:
            quota = quotas.get(category, 0)
            if quota <= 0:
                continue

            category_result: list[Song | None] = [None] * quota
            used_keys: set[str] = set()

            for index, song in enumerate(previous_by_category[category]):
                key = self.song_key(song)
                if index < quota and key in locked_by_key:
                    category_result[index] = locked_by_key[key]
                    used_keys.add(key)

            for key, song in locked_by_key.items():
                if key in used_keys or song.category != category:
                    continue
                for index, current in enumerate(category_result):
                    if current is None:
                        category_result[index] = song
                        used_keys.add(key)
                        break

            for pool in (candidate_by_category[category], available_by_category[category]):
                for song in pool:
                    key = self.song_key(song)
                    if key in used_keys:
                        continue
                    empty_index = next(
                        (index for index, current in enumerate(category_result) if current is None),
                        None,
                    )
                    if empty_index is None:
                        break
                    category_result[empty_index] = song
                    used_keys.add(key)

            result.extend(song for song in category_result if song is not None)

        return result

    def selected_categories(self, songs: list[Song]) -> set[str]:
        return {song.category for song in songs}

    def build_copy_plan(self, songs: list[Song], destination: Path) -> list[tuple[Song, Path]]:
        categories = self.selected_categories(songs)
        use_subfolders = len(categories) > 1
        plan: list[tuple[Song, Path]] = []
        reserved_targets: set[Path] = set()

        if use_subfolders:
            for key in FILE_TYPES:
                category_songs = [song for song in songs if song.category == key]
                if not category_songs:
                    continue
                category_folder = destination / FILE_TYPES[key][0]
                for index, song in enumerate(category_songs, start=1):
                    target = self.unique_target_path(category_folder / f"{index:02d}.{song.name}", reserved_targets)
                    reserved_targets.add(target)
                    plan.append((song, target))
        else:
            for index, song in enumerate(songs, start=1):
                target = self.unique_target_path(destination / f"{index:02d}.{song.name}", reserved_targets)
                reserved_targets.add(target)
                plan.append((song, target))

        return plan

    def update_preview_tree(self, songs: list[Song]) -> None:
        self.preview_tree.delete(*self.preview_tree.get_children())
        self.preview_tree_items.clear()
        locked_count = sum(
            1 for song in songs if self.song_key(song) in self.locked_preview_keys
        )
        self.preview_summary_label.configure(
            text=f"{len(songs)} file siap | {locked_count} locked"
        )
        if not songs:
            self.schedule_timestamp_preview([])
            return

        plan = self.build_copy_plan(songs, Path(self.destination_folder.get().strip() or "."))
        categories = self.selected_categories(songs)

        if len(categories) > 1:
            parents: dict[str, str] = {}
            for key in FILE_TYPES:
                if key not in categories:
                    continue
                parent_id = f"preview_{key}"
                label = FILE_TYPES[key][0]
                count = sum(1 for song in songs if song.category == key)
                self.preview_tree.insert("", "end", iid=parent_id, text=f"{label}/ ({count})", open=True)
                parents[key] = parent_id

            for index, (song, target) in enumerate(plan):
                item_id = f"preview_file_{index}"
                self.preview_tree_items[item_id] = song
                self.preview_tree.insert(
                    parents[song.category],
                    "end",
                    iid=item_id,
                    text=self.preview_item_text(song, target.name),
                )
        else:
            for index, (song, target) in enumerate(plan):
                item_id = f"preview_file_{index}"
                self.preview_tree_items[item_id] = song
                self.preview_tree.insert(
                    "",
                    "end",
                    iid=item_id,
                    text=self.preview_item_text(song, target.name),
                )
        self.schedule_timestamp_preview(songs)

    def preview_item_text(self, song: Song, output_name: str, drag_marker: str = "") -> str:
        prefix = ""
        if drag_marker:
            prefix += f"{drag_marker} "
        if self.song_key(song) in self.locked_preview_keys:
            prefix += "[LOCK] "
        return f"{prefix}{output_name}"

    def selected_preview_songs(self) -> list[Song]:
        selected: list[Song] = []
        for item_id in self.preview_tree.selection():
            if item_id in self.preview_tree_items:
                selected.append(self.preview_tree_items[item_id])
                continue
            for child_id in self.preview_tree.get_children(item_id):
                song = self.preview_tree_items.get(child_id)
                if song:
                    selected.append(song)
        return selected

    def toggle_preview_locks(self) -> None:
        songs = self.selected_preview_songs()
        if not songs:
            self.status_text.set("Pilih file di Preview Output untuk lock atau unlock.")
            return

        keys = {self.song_key(song) for song in songs}
        should_unlock = all(key in self.locked_preview_keys for key in keys)
        if should_unlock:
            self.locked_preview_keys.difference_update(keys)
            action = "di-unlock"
        else:
            self.locked_preview_keys.update(keys)
            action = "di-lock"

        self.custom_preview_order = [self.song_key(song) for song in self.selected_songs]
        self.update_preview_tree(self.selected_songs)
        self.status_text.set(f"{len(songs)} file preview berhasil {action}.")

    def clear_preview_locks(self) -> None:
        if not self.locked_preview_keys:
            self.status_text.set("Belum ada file preview yang terkunci.")
            return
        self.locked_preview_keys.clear()
        self.update_preview_tree(self.selected_songs)
        self.status_text.set("Semua lock preview sudah dilepas.")

    def on_preview_drag_start(self, event) -> None:
        item_id = self.preview_tree.identify_row(event.y)
        self.preview_drag_item = item_id if item_id in self.preview_tree_items else None
        self.preview_drop_target = None
        if self.preview_drag_item:
            self.preview_tree.configure(style="Drag.Treeview")
            self.mark_preview_drag_state(self.preview_drag_item, "dragging")
            self.preview_tree.selection_set(self.preview_drag_item)
            self.status_text.set("Sedang drag file preview. Lepaskan pada posisi tujuan.")

    def on_preview_drag_motion(self, event) -> None:
        if not self.preview_drag_item:
            return

        target_id = self.preview_tree.identify_row(event.y)
        if (
            not target_id
            or target_id == self.preview_drag_item
            or target_id not in self.preview_tree_items
            or self.preview_tree.parent(target_id) != self.preview_tree.parent(self.preview_drag_item)
        ):
            self.clear_preview_drop_target()
            return

        if target_id == self.preview_drop_target:
            return

        self.clear_preview_drop_target()
        self.preview_drop_target = target_id
        self.mark_preview_drag_state(target_id, "drop-target")

    def on_preview_drag_release(self, event) -> None:
        if not self.preview_drag_item:
            return

        target_id = self.preview_tree.identify_row(event.y)
        dragged_id = self.preview_drag_item
        self.preview_drag_item = None
        self.preview_tree.configure(style="File.Treeview")
        self.clear_preview_drag_marks()

        if not target_id or dragged_id == target_id or target_id not in self.preview_tree_items:
            self.preview_drop_target = None
            return

        source_parent = self.preview_tree.parent(dragged_id)
        target_parent = self.preview_tree.parent(target_id)
        if source_parent != target_parent:
            self.status_text.set("Drag preview hanya bisa di dalam jenis file yang sama.")
            self.preview_drop_target = None
            return

        target_index = self.preview_tree.index(target_id)
        self.preview_tree.move(dragged_id, source_parent, target_index)
        self.preview_drop_target = None
        self.sync_preview_order_from_tree([dragged_id, target_id])

    def clear_preview_drop_target(self) -> None:
        if self.preview_drop_target and self.preview_drop_target in self.preview_tree_items:
            self.mark_preview_drag_state(self.preview_drop_target, None)
        self.preview_drop_target = None

    def clear_preview_drag_marks(self) -> None:
        for item_id in list(self.preview_tree_items):
            self.mark_preview_drag_state(item_id, None)

    def mark_preview_drag_state(self, item_id: str, state: str | None) -> None:
        song = self.preview_tree_items.get(item_id)
        if not song or not self.preview_tree.exists(item_id):
            return
        current_text = self.preview_tree.item(item_id, "text")
        output_name = (
            current_text
            .replace("[DRAG] ", "")
            .replace("[DROP HERE] ", "")
            .replace("[MOVED] ", "")
            .replace("[LOCK] ", "")
        )
        marker = ""
        tags: tuple[str, ...] = ()
        if state == "dragging":
            marker = "[DRAG]"
            tags = ("dragging",)
        elif state == "drop-target":
            marker = "[DROP HERE]"
            tags = ("drop-target",)
        elif state == "moved":
            marker = "[MOVED]"
            tags = ("moved",)

        self.preview_tree.item(
            item_id,
            text=self.preview_item_text(song, output_name, marker),
            tags=tags,
        )

    def flash_preview_moved_items(self, item_ids: list[str]) -> None:
        for item_id in item_ids:
            self.mark_preview_drag_state(item_id, "moved")
        self.root.after(
            800,
            lambda: [self.mark_preview_drag_state(item_id, None) for item_id in item_ids],
        )

    def sync_preview_order_from_tree(self, moved_item_ids: list[str] | None = None) -> None:
        ordered: list[Song] = []
        for item_id in self.preview_tree.get_children(""):
            if item_id in self.preview_tree_items:
                ordered.append(self.preview_tree_items[item_id])
                continue
            for child_id in self.preview_tree.get_children(item_id):
                song = self.preview_tree_items.get(child_id)
                if song:
                    ordered.append(song)

        if not ordered:
            return

        self.selected_songs = ordered
        self.custom_preview_order = [self.song_key(song) for song in ordered]
        self.update_preview_tree(self.selected_songs)
        if moved_item_ids:
            moved_keys = {
                self.song_key(song)
                for item_id in moved_item_ids
                if (song := self.preview_tree_items.get(item_id))
            }
            flash_ids = [
                item_id
                for item_id, song in self.preview_tree_items.items()
                if self.song_key(song) in moved_keys
            ]
            self.flash_preview_moved_items(flash_ids)
        self.status_text.set("Urutan preview diperbarui. Generate akan mengikuti urutan ini.")

    def reset_timestamp_box(self) -> None:
        self.cancel_timestamp_preview()
        self.timestamp_text = ""
        self.set_timestamp_text("Timestamp akan tampil otomatis setelah Preview Output berisi audio atau video.")
        self.copy_timestamp_button.configure(state="disabled")

    def cancel_timestamp_preview(self) -> None:
        self.timestamp_preview_revision += 1
        if self.timestamp_preview_after_id is not None:
            try:
                self.root.after_cancel(self.timestamp_preview_after_id)
            except Exception:
                pass
            self.timestamp_preview_after_id = None

    def schedule_timestamp_preview(self, songs: list[Song]) -> None:
        self.cancel_timestamp_preview()
        media_songs = [song for song in songs if song.category in {"music", "video"}]
        if not media_songs:
            self.timestamp_text = ""
            self.set_timestamp_text("Timestamp akan tampil otomatis setelah Preview Output berisi audio atau video.")
            self.copy_timestamp_button.configure(state="disabled")
            return

        revision = self.timestamp_preview_revision
        self.timestamp_text = ""
        self.set_timestamp_text("Membaca durasi audio/video untuk preview timestamp...")
        self.copy_timestamp_button.configure(state="disabled")
        self.timestamp_preview_after_id = self.root.after(
            300,
            self.start_timestamp_preview_worker,
            songs.copy(),
            revision,
        )

    def start_timestamp_preview_worker(self, songs: list[Song], revision: int) -> None:
        self.timestamp_preview_after_id = None
        thread = threading.Thread(
            target=self.build_timestamp_preview_worker,
            args=(songs, revision),
            daemon=True,
        )
        thread.start()

    def build_timestamp_preview_worker(self, songs: list[Song], revision: int) -> None:
        text = self.build_timestamp_text(songs)
        can_copy = any(song.category in {"music", "video"} for song in songs)
        self.root.after(0, self.apply_timestamp_preview, text, can_copy, revision)

    def apply_timestamp_preview(self, text: str, can_copy: bool, revision: int) -> None:
        if revision != self.timestamp_preview_revision:
            return
        self.timestamp_text = text if can_copy else ""
        self.set_timestamp_text(text)
        self.copy_timestamp_button.configure(state="normal" if can_copy else "disabled")

    def set_timestamp_text(self, text: str) -> None:
        self.timestamp_box.configure(state="normal")
        self.timestamp_box.delete("1.0", "end")
        self.timestamp_box.insert("1.0", text)
        self.timestamp_box.configure(state="disabled")

    def copy_timestamp_to_clipboard(self) -> None:
        if not self.timestamp_text.strip():
            messagebox.showinfo("Timestamp belum tersedia", "Generate file terlebih dahulu.")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.timestamp_text)
        self.status_text.set("Timestamp berhasil dicopy ke clipboard.")

    def build_timestamp_text(self, songs: list[Song]) -> str:
        sections = []
        missing_duration: list[str] = []

        for category, title in (("music", "Audio"), ("video", "Video")):
            media_files = [song for song in songs if song.category == category]
            if not media_files:
                continue

            lines = [f"{title} Timestamp"]
            elapsed = 0.0
            for song in media_files:
                lines.append(f"[{self.format_timestamp(elapsed)}] - {song.path.stem}")
                duration = self.read_media_duration(song.path)
                if duration is None:
                    missing_duration.append(song.name)
                    continue
                elapsed += duration
            sections.append("\n".join(lines))

        if missing_duration:
            sections.append(
                "Durasi tidak terbaca\n"
                + "\n".join(f"- {name}" for name in missing_duration)
            )

        return "\n\n".join(sections) if sections else "Tidak ada file audio atau video pada output ini."

    def read_media_duration(self, path: Path) -> float | None:
        duration = self.read_duration_with_ffprobe(path)
        if duration is not None:
            return duration
        duration = self.read_duration_with_mutagen(path)
        if duration is not None:
            return duration
        duration = self.read_duration_from_iso_video_atoms(path)
        if duration is not None:
            return duration
        duration = self.read_duration_from_mp3_frames(path)
        if duration is not None:
            return duration
        return self.read_duration_with_tinytag(path)

    @staticmethod
    def read_duration_with_ffprobe(path: Path) -> float | None:
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
        startupinfo = None
        creationflags = 0
        if hasattr(subprocess, "STARTUPINFO"):
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            creationflags = subprocess.CREATE_NO_WINDOW

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=8,
                startupinfo=startupinfo,
                creationflags=creationflags,
                check=False,
            )
        except Exception:
            return None

        if result.returncode != 0:
            return None
        try:
            duration = float(result.stdout.strip())
        except ValueError:
            return None
        return duration if duration > 0 else None

    @staticmethod
    def read_duration_with_mutagen(path: Path) -> float | None:
        if not MUTAGEN_AVAILABLE or MutagenFile is None:
            return None
        try:
            media = MutagenFile(str(path))
        except Exception:
            return None
        if not media or not getattr(media, "info", None):
            return None
        duration = getattr(media.info, "length", None)
        try:
            duration_value = float(duration)
        except (TypeError, ValueError):
            return None
        return duration_value if duration_value > 0 else None

    @staticmethod
    def read_duration_from_iso_video_atoms(path: Path) -> float | None:
        if path.suffix.lower() not in ISO_VIDEO_EXTENSIONS:
            return None

        try:
            file_size = path.stat().st_size
            with path.open("rb") as file:
                return PlaylistGeneratorApp.read_iso_duration_boxes(file, 0, file_size, 0)
        except Exception:
            return None

    @staticmethod
    def read_iso_duration_boxes(file, start: int, end: int, depth: int) -> float | None:
        if depth > 6 or end <= start:
            return None

        container_boxes = {
            b"moov",
            b"trak",
            b"mdia",
            b"minf",
            b"stbl",
            b"edts",
            b"udta",
            b"mvex",
            b"meta",
        }
        preferred_duration: float | None = None
        fallback_duration: float | None = None
        offset = start

        while offset + 8 <= end:
            file.seek(offset)
            header = file.read(8)
            if len(header) != 8:
                break

            box_size = int.from_bytes(header[:4], "big")
            box_type = header[4:8]
            header_size = 8

            if box_size == 1:
                large_size = file.read(8)
                if len(large_size) != 8:
                    break
                box_size = int.from_bytes(large_size, "big")
                header_size = 16
            elif box_size == 0:
                box_size = end - offset

            if box_size < header_size:
                break

            box_end = min(offset + box_size, end)
            data_start = offset + header_size

            if box_type == b"mvhd":
                duration = PlaylistGeneratorApp.parse_iso_duration_box(file, data_start, box_end)
                if duration is not None:
                    return duration
            elif box_type == b"mdhd":
                duration = PlaylistGeneratorApp.parse_iso_duration_box(file, data_start, box_end)
                if duration is not None:
                    fallback_duration = max(fallback_duration or 0, duration)
            elif box_type in container_boxes:
                child_start = data_start + (4 if box_type == b"meta" else 0)
                child_duration = PlaylistGeneratorApp.read_iso_duration_boxes(
                    file,
                    child_start,
                    box_end,
                    depth + 1,
                )
                if child_duration is not None:
                    if box_type == b"moov":
                        preferred_duration = child_duration
                    else:
                        fallback_duration = max(fallback_duration or 0, child_duration)

            offset = box_end

        return preferred_duration or fallback_duration

    @staticmethod
    def parse_iso_duration_box(file, start: int, end: int) -> float | None:
        if end - start < 16:
            return None

        file.seek(start)
        header = file.read(4)
        if len(header) != 4:
            return None

        version = header[0]
        if version == 1:
            needed = 32
            if end - start < needed:
                return None
            payload = file.read(28)
            if len(payload) != 28:
                return None
            timescale = int.from_bytes(payload[16:20], "big")
            duration_units = int.from_bytes(payload[20:28], "big")
        else:
            needed = 20
            if end - start < needed:
                return None
            payload = file.read(16)
            if len(payload) != 16:
                return None
            timescale = int.from_bytes(payload[8:12], "big")
            duration_units = int.from_bytes(payload[12:16], "big")

        if timescale <= 0 or duration_units <= 0:
            return None

        duration = duration_units / timescale
        return duration if duration > 0 else None

    @staticmethod
    def read_duration_from_mp3_frames(path: Path) -> float | None:
        if path.suffix.lower() != ".mp3":
            return None

        try:
            file_size = path.stat().st_size
            with path.open("rb") as file:
                header = file.read(10)
                audio_start = 0
                if len(header) == 10 and header[:3] == b"ID3":
                    tag_size = (
                        ((header[6] & 0x7F) << 21)
                        | ((header[7] & 0x7F) << 14)
                        | ((header[8] & 0x7F) << 7)
                        | (header[9] & 0x7F)
                    )
                    audio_start = 10 + tag_size
                    if header[5] & 0x10:
                        audio_start += 10

                file.seek(audio_start)
                search_data = file.read(512 * 1024)
        except Exception:
            return None

        frame_offset = None
        frame_info = None
        for index in range(max(0, len(search_data) - 4)):
            candidate = PlaylistGeneratorApp.parse_mp3_frame_header(search_data[index : index + 4])
            if candidate:
                frame_offset = audio_start + index
                frame_info = candidate
                break

        if frame_offset is None or frame_info is None:
            return None

        vbr_duration = PlaylistGeneratorApp.read_vbr_mp3_duration(path, frame_offset, frame_info)
        if vbr_duration is not None:
            return vbr_duration

        audio_size = file_size - frame_offset
        try:
            with path.open("rb") as file:
                if file_size >= 128:
                    file.seek(file_size - 128)
                    if file.read(3) == b"TAG":
                        audio_size -= 128
        except Exception:
            pass

        bitrate = frame_info["bitrate"]
        if audio_size <= 0 or bitrate <= 0:
            return None
        duration = (audio_size * 8) / (bitrate * 1000)
        return duration if duration > 0 else None

    @staticmethod
    def parse_mp3_frame_header(header: bytes) -> dict[str, int] | None:
        if len(header) != 4:
            return None
        value = int.from_bytes(header, "big")
        if (value & 0xFFE00000) != 0xFFE00000:
            return None

        version_bits = (value >> 19) & 0b11
        layer_bits = (value >> 17) & 0b11
        bitrate_index = (value >> 12) & 0b1111
        sample_rate_index = (value >> 10) & 0b11
        channel_mode = (value >> 6) & 0b11

        if version_bits == 0b01 or layer_bits == 0 or bitrate_index in (0, 15) or sample_rate_index == 3:
            return None

        version = {0b00: 25, 0b10: 2, 0b11: 1}[version_bits]
        layer = {0b01: 3, 0b10: 2, 0b11: 1}[layer_bits]

        bitrate_tables = {
            (1, 1): [0, 32, 64, 96, 128, 160, 192, 224, 256, 288, 320, 352, 384, 416, 448],
            (1, 2): [0, 32, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320, 384],
            (1, 3): [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320],
            (2, 1): [0, 32, 48, 56, 64, 80, 96, 112, 128, 144, 160, 176, 192, 224, 256],
            (2, 2): [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
            (2, 3): [0, 8, 16, 24, 32, 40, 48, 56, 64, 80, 96, 112, 128, 144, 160],
        }
        table_version = 1 if version == 1 else 2
        bitrate = bitrate_tables[(table_version, layer)][bitrate_index]

        sample_rates = {
            1: [44100, 48000, 32000],
            2: [22050, 24000, 16000],
            25: [11025, 12000, 8000],
        }
        sample_rate = sample_rates[version][sample_rate_index]

        if layer == 1:
            samples_per_frame = 384
        elif layer == 2:
            samples_per_frame = 1152
        else:
            samples_per_frame = 1152 if version == 1 else 576

        return {
            "version": version,
            "layer": layer,
            "bitrate": bitrate,
            "sample_rate": sample_rate,
            "channel_mode": channel_mode,
            "samples_per_frame": samples_per_frame,
        }

    @staticmethod
    def read_vbr_mp3_duration(path: Path, frame_offset: int, frame_info: dict[str, int]) -> float | None:
        try:
            with path.open("rb") as file:
                file.seek(frame_offset)
                frame_data = file.read(512)
        except Exception:
            return None

        side_info_size = 17 if frame_info["channel_mode"] == 3 else 32
        if frame_info["version"] != 1:
            side_info_size = 9 if frame_info["channel_mode"] == 3 else 17

        xing_offset = 4 + side_info_size
        if len(frame_data) >= xing_offset + 16 and frame_data[xing_offset : xing_offset + 4] in (b"Xing", b"Info"):
            flags = int.from_bytes(frame_data[xing_offset + 4 : xing_offset + 8], "big")
            if flags & 0x0001:
                frames = int.from_bytes(frame_data[xing_offset + 8 : xing_offset + 12], "big")
                if frames > 0:
                    return frames * frame_info["samples_per_frame"] / frame_info["sample_rate"]

        vbri_offset = 36
        if len(frame_data) >= vbri_offset + 18 and frame_data[vbri_offset : vbri_offset + 4] == b"VBRI":
            frames = int.from_bytes(frame_data[vbri_offset + 14 : vbri_offset + 18], "big")
            if frames > 0:
                return frames * frame_info["samples_per_frame"] / frame_info["sample_rate"]

        return None

    @staticmethod
    def read_duration_with_tinytag(path: Path) -> float | None:
        if not TINYTAG_AVAILABLE or TinyTag is None:
            return None
        try:
            duration = TinyTag.get(str(path)).duration
        except Exception:
            return None
        return duration if duration and duration > 0 else None

    @staticmethod
    def format_timestamp(seconds: float) -> str:
        total_seconds = max(0, int(round(seconds)))
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        secs = total_seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def generate_playlist(self) -> None:
        if len(self.selected_songs) != self.get_total_count():
            self.update_selection_preview()

        if not self.songs:
            messagebox.showwarning("Belum ada file", "Pilih folder atau file yang didukung.")
            return
        if not self.selected_songs:
            messagebox.showwarning("Belum ada pilihan", "Belum ada file yang dipilih.")
            return
        if self.get_total_count() == 0:
            messagebox.showwarning(
                "Jumlah file belum dipilih",
                "Atur jumlah file minimal 1 pada salah satu jenis file.",
            )
            return
        if self.mode.get() == "manual" and len(self.selected_songs) < self.get_total_count():
            messagebox.showwarning(
                "Pilihan belum cukup",
                f"Pilih {self.get_total_count()} file sesuai kuota jenis file.",
            )
            return

        destination = self.ask_generate_destination()
        if destination is None:
            return

        thread = threading.Thread(
            target=self.copy_selected_songs,
            args=(self.selected_songs.copy(), destination),
            daemon=True,
        )
        thread.start()

    def copy_selected_songs(self, songs: list[Song], destination: Path) -> None:
        plan = self.build_copy_plan(songs, destination)
        total = len(plan)
        self.root.after(0, self.progress.configure, {"maximum": total, "value": 0})
        copied = 0

        try:
            for song, target in plan:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(song.path, target)
                copied += 1
                self.root.after(0, self.progress.configure, {"value": copied})
                self.root.after(
                    0,
                    self.progress_text.set,
                    f"{copied}/{total}",
                )

            timestamp_text = self.build_timestamp_text(songs)
            has_timestamp_media = any(song.category in {"music", "video"} for song in songs)
            self.root.after(
                0,
                self.apply_generated_timestamp,
                timestamp_text,
                has_timestamp_media,
            )
            self.root.after(
                0,
                self.status_text.set,
                f"Selesai. {copied} file berhasil dicopy ke: {destination}",
            )
            self.root.after(
                0,
                messagebox.showinfo,
                "Playlist selesai",
                self.success_message(copied, songs, destination),
            )
        except Exception as exc:
            self.root.after(0, messagebox.showerror, "Gagal copy file", str(exc))
            self.root.after(0, self.status_text.set, "Proses gagal. Cek folder dan izin file.")
        finally:
            self.root.after(1200, self.progress_text.set, "")

    def apply_generated_timestamp(self, text: str, can_copy: bool) -> None:
        self.timestamp_text = text if can_copy else ""
        self.set_timestamp_text(text)
        self.copy_timestamp_button.configure(state="normal" if can_copy else "disabled")

    def success_message(self, copied: int, songs: list[Song], destination: Path) -> str:
        categories = self.selected_categories(songs)
        if len(categories) <= 1:
            return f"{copied} file berhasil dicopy.\n\nFolder tujuan:\n{destination}"

        folders = "\n".join(
            f"- {destination / FILE_TYPES[key][0]}"
            for key in FILE_TYPES
            if key in categories
        )
        return (
            f"{copied} file berhasil dicopy dan dipisah berdasarkan jenis file."
            f"\n\nFolder tujuan:\n{destination}"
            f"\n\nSubfolder:\n{folders}"
        )

    @staticmethod
    def unique_target_path(path: Path, reserved: set[Path] | None = None) -> Path:
        reserved = reserved or set()
        if not path.exists() and path not in reserved:
            return path

        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        counter = 2
        while True:
            candidate = parent / f"{stem} ({counter}){suffix}"
            if not candidate.exists() and candidate not in reserved:
                return candidate
            counter += 1


if __name__ == "__main__":
    PlaylistGeneratorApp().run()
