from __future__ import annotations

import random
import shutil
import subprocess
import threading
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from tkinter import (
    BooleanVar,
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

PDF_EXTENSIONS = {".pdf"}

FILE_TYPES = {
    "music": ("Musik", AUDIO_EXTENSIONS),
    "image": ("Gambar", IMAGE_EXTENSIONS),
    "video": ("Video", VIDEO_EXTENSIONS),
    "pdf": ("PDF", PDF_EXTENSIONS),
}

SUPPORTED_EXTENSIONS = set().union(*(extensions for _, extensions in FILE_TYPES.values()))

APP_VERSION = "1.1.3"
REPO_URL = "https://github.com/renaldyakb/playlist-generator-tools"
LATEST_RELEASE_URL = f"{REPO_URL}/releases/latest"


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
        self.root.minsize(980, 640)
        self.root.configure(bg="#f3f6f4")

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
        self.timestamp_text = ""
        self.dropped_paths: list[Path] = []
        self.songs: list[Song] = []
        self.selected_songs: list[Song] = []

        self._configure_theme()
        self._build_layout()

    def run(self) -> None:
        self.root.mainloop()

    def open_repository(self) -> None:
        webbrowser.open(REPO_URL)

    def open_latest_release(self) -> None:
        webbrowser.open(LATEST_RELEASE_URL)

    def _configure_theme(self) -> None:
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "App.TFrame",
            background="#f3f6f4",
        )
        style.configure(
            "Panel.TFrame",
            background="#ffffff",
            bordercolor="#dce4df",
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
            background="#f3f6f4",
            foreground="#16211d",
            font=("Segoe UI", 24, "bold"),
        )
        style.configure(
            "Subheader.TLabel",
            background="#f3f6f4",
            foreground="#52605a",
            font=("Segoe UI", 10),
        )
        style.configure(
            "PanelTitle.TLabel",
            background="#ffffff",
            foreground="#16211d",
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
            background="#24705d",
            foreground="#ffffff",
            borderwidth=0,
            focusthickness=0,
            font=("Segoe UI", 10, "bold"),
            padding=(16, 10),
        )
        style.map(
            "Primary.TButton",
            background=[("active", "#1c5b4b"), ("disabled", "#9eb7b1")],
            foreground=[("disabled", "#eef4f2")],
        )
        style.configure(
            "Secondary.TButton",
            background="#e8efeb",
            foreground="#16211d",
            borderwidth=0,
            focusthickness=0,
            font=("Segoe UI", 10),
            padding=(14, 8),
        )
        style.map("Secondary.TButton", background=[("active", "#dbe6e0")])
        style.configure(
            "Link.TButton",
            background="#f3f6f4",
            foreground="#24705d",
            borderwidth=0,
            focusthickness=0,
            font=("Segoe UI", 9, "bold"),
            padding=(10, 6),
        )
        style.map("Link.TButton", background=[("active", "#e7efeb")])
        style.configure(
            "Field.TEntry",
            fieldbackground="#f8faf9",
            background="#f8faf9",
            foreground="#16211d",
            bordercolor="#ccd8d2",
            lightcolor="#ccd8d2",
            darkcolor="#ccd8d2",
            insertcolor="#16211d",
            padding=(10, 8),
        )
        style.map("Field.TEntry", bordercolor=[("focus", "#24705d")])
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
            background="#f8faf9",
            fieldbackground="#f8faf9",
            foreground="#16211d",
            bordercolor="#ccd8d2",
            borderwidth=1,
            rowheight=24,
            font=("Segoe UI", 10),
        )
        style.map(
            "File.Treeview",
            background=[("selected", "#24705d")],
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
        style.configure("TProgressbar", background="#24705d", troughcolor="#dfe7e3")

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
        ).grid(row=0, column=3, sticky="e")

        self.left_panel = ttk.Frame(container, style="Panel.TFrame", padding=20)
        self.left_panel.grid(row=1, column=0, sticky="nsew", padx=(0, 18))
        self.left_panel.columnconfigure(0, weight=1)

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
        ttk.Label(self.left_panel, text="Sumber File", style="PanelTitle.TLabel").grid(
            row=0, column=0, sticky="w"
        )

        source_row = ttk.Frame(self.left_panel, style="Plain.TFrame")
        source_row.grid(row=1, column=0, sticky="ew", pady=(10, 8))
        source_row.columnconfigure(0, weight=1)
        source_entry = ttk.Entry(
            source_row,
            textvariable=self.source_folder,
            style="Field.TEntry",
            font=("Segoe UI", 9),
        )
        source_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        ttk.Button(
            source_row,
            text="Pilih",
            style="Secondary.TButton",
            command=self.choose_source_folder,
        ).grid(row=0, column=1, sticky="e")

        ttk.Checkbutton(
            self.left_panel,
            text="Scan subfolder juga",
            variable=self.recursive_scan,
            command=self.refresh_songs,
            style="Clean.TCheckbutton",
        ).grid(row=2, column=0, sticky="w", pady=(0, 20))

        ttk.Label(self.left_panel, text="Jenis & Jumlah File", style="PanelTitle.TLabel").grid(
            row=3, column=0, sticky="w"
        )
        filter_box = ttk.Frame(self.left_panel, style="Plain.TFrame")
        filter_box.grid(row=4, column=0, sticky="ew", pady=(10, 12))
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
                fg="#16211d",
                troughcolor="#dfe7e3",
                highlightthickness=0,
                activebackground="#24705d",
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
                bg="#f8faf9",
                fg="#16211d",
                buttonbackground="#e8efeb",
                highlightthickness=1,
                highlightbackground="#ccd8d2",
                highlightcolor="#24705d",
            )
            spinbox.grid(row=index, column=2, sticky="e", pady=4, ipady=4)
            self.count_spinboxes[key] = spinbox

        ttk.Label(self.left_panel, textvariable=self.counts_text, style="Muted.TLabel").grid(
            row=5, column=0, sticky="w", pady=(0, 18)
        )

        ttk.Label(self.left_panel, text="Cara Memilih", style="PanelTitle.TLabel").grid(
            row=6, column=0, sticky="w"
        )
        mode_box = ttk.Frame(self.left_panel, style="Plain.TFrame")
        mode_box.grid(row=7, column=0, sticky="ew", pady=(10, 20))
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

        ttk.Label(self.left_panel, text="Folder Tujuan", style="PanelTitle.TLabel").grid(
            row=8, column=0, sticky="w"
        )
        destination_row = ttk.Frame(self.left_panel, style="Plain.TFrame")
        destination_row.grid(row=9, column=0, sticky="ew", pady=(10, 20))
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
        action_row.grid(row=10, column=0, sticky="ew")
        action_row.columnconfigure(0, weight=1)
        ttk.Button(
            action_row,
            text="Generate & Copy",
            style="Primary.TButton",
            command=self.generate_playlist,
        ).grid(row=0, column=0, sticky="ew")

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

        ttk.Label(self.right_panel, text="Preview Output", style="PanelTitle.TLabel").grid(
            row=4, column=0, sticky="w", pady=(16, 8)
        )
        preview_frame = Frame(self.right_panel, bg="#ffffff")
        preview_frame.grid(row=5, column=0, sticky="ew")
        preview_frame.columnconfigure(0, weight=1)

        self.preview_tree = ttk.Treeview(
            preview_frame,
            show="tree",
            height=8,
            selectmode="none",
            style="File.Treeview",
        )
        self.preview_tree.grid(row=0, column=0, sticky="ew")

        preview_scrollbar = ttk.Scrollbar(
            preview_frame,
            orient="vertical",
            command=self.preview_tree.yview,
        )
        preview_scrollbar.grid(row=0, column=1, sticky="ns")
        self.preview_tree.configure(yscrollcommand=preview_scrollbar.set)

        timestamp_header = ttk.Frame(self.right_panel, style="Plain.TFrame")
        timestamp_header.grid(row=6, column=0, sticky="ew", pady=(16, 8))
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
        timestamp_frame.grid(row=7, column=0, sticky="ew")
        timestamp_frame.columnconfigure(0, weight=1)

        self.timestamp_box = Text(
            timestamp_frame,
            height=8,
            wrap="none",
            borderwidth=0,
            highlightthickness=1,
            highlightcolor="#ccd8d2",
            highlightbackground="#ccd8d2",
            bg="#f8faf9",
            fg="#16211d",
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
        self.set_timestamp_text("Timestamp akan dibuat setelah Generate & Copy berhasil.")

    def _build_empty_state(self) -> None:
        self.empty_panel = ttk.Frame(self.container, style="Panel.TFrame", padding=34)
        self.empty_panel.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.empty_panel.columnconfigure(0, weight=1)
        self.empty_panel.rowconfigure(0, weight=1)

        drop_zone = Frame(
            self.empty_panel,
            bg="#f8faf9",
            highlightthickness=1,
            highlightbackground="#ccd8d2",
            highlightcolor="#24705d",
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
            self.dropped_paths = []
            self.source_folder.set(folder)
            self.refresh_songs()

    def choose_source_files(self) -> None:
        files = filedialog.askopenfilenames(
            title="Pilih file",
            filetypes=[
                ("File yang didukung", self.supported_filetype_pattern()),
                ("Semua file", "*.*"),
            ],
        )
        if files:
            self.dropped_paths = [Path(file) for file in files]
            self.source_folder.set(f"{len(self.dropped_paths)} file dipilih")
            self.refresh_songs()

    def choose_destination_folder(self) -> None:
        folder = filedialog.askdirectory(title="Pilih folder tujuan playlist")
        if folder:
            self.destination_folder.set(folder)

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

        self.dropped_paths = paths
        if len(paths) == 1 and paths[0].is_dir():
            self.source_folder.set(str(paths[0]))
            self.dropped_paths = []
        else:
            self.source_folder.set(f"{len(paths)} item dipilih via drag & drop")
        self.refresh_songs()

    def update_source_view(self) -> None:
        has_source = bool(self.source_folder.get().strip() or self.dropped_paths)
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
        if self.dropped_paths:
            files = []
            for path in self.dropped_paths:
                files.extend(self.collect_files_from_path(path))
        else:
            source_text = self.source_folder.get().strip()
            source = Path(source_text) if source_text else None
            if not source or not source.exists() or not source.is_dir():
                self.songs = []
                self.update_song_list()
                self.update_counts()
                self.update_source_view()
                self.status_text.set("Pilih folder atau file yang valid.")
                return
            files = self.collect_files_from_path(source)

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

        self.update_song_list()
        self.update_counts()
        self.sync_count_controls(default_if_empty=True)
        self.update_selection_preview()
        self.update_source_view()
        self.status_text.set(f"Ditemukan {len(self.songs)} file yang didukung.")

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
        self.reset_timestamp_box()

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

        self.selected_songs = selected
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
        if not songs:
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
                self.preview_tree.insert(
                    parents[song.category],
                    "end",
                    iid=f"preview_file_{index}",
                    text=target.name,
                )
        else:
            for index, (_song, target) in enumerate(plan):
                self.preview_tree.insert("", "end", iid=f"preview_file_{index}", text=target.name)

    def reset_timestamp_box(self) -> None:
        self.timestamp_text = ""
        self.set_timestamp_text("Timestamp akan dibuat setelah Generate & Copy berhasil.")
        self.copy_timestamp_button.configure(state="disabled")

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
        destination_text = self.destination_folder.get().strip()

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
        if not destination_text:
            messagebox.showwarning(
                "Folder tujuan belum dipilih",
                "Tentukan folder tujuan terlebih dahulu sebelum generate playlist.",
            )
            self.status_text.set("Pilih folder tujuan terlebih dahulu.")
            return

        destination = Path(destination_text)
        if not destination.exists() or not destination.is_dir():
            messagebox.showwarning("Folder tujuan belum valid", "Pilih folder tujuan yang valid.")
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
