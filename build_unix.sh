#!/usr/bin/env sh

set -u

APP_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)

find_python() {
    if command -v python3 >/dev/null 2>&1; then
        printf '%s' "python3"
        return 0
    fi

    if command -v python >/dev/null 2>&1; then
        printf '%s' "python"
        return 0
    fi

    return 1
}

OS_NAME=$(uname -s 2>/dev/null || printf '%s' "Unknown")

case "$OS_NAME" in
    Darwin)
        DOWNLOAD_LINK="https://www.python.org/downloads/macos/"
        APP_NAME="PlaylistGenerator"
        ;;
    Linux)
        DOWNLOAD_LINK="https://www.python.org/downloads/"
        APP_NAME="PlaylistGenerator"
        ;;
    *)
        DOWNLOAD_LINK="https://www.python.org/downloads/"
        APP_NAME="PlaylistGenerator"
        ;;
esac

PYTHON_CMD=$(find_python || true)

if [ -z "$PYTHON_CMD" ]; then
    printf '\n%s\n\n' "Python belum tersedia di komputer ini."
    printf '%s\n' "Untuk build aplikasi, install Python 3.10 atau yang lebih baru."
    printf '%s\n\n' "Download resmi: $DOWNLOAD_LINK"

    if [ "$OS_NAME" = "Linux" ]; then
        printf '%s\n' "Di Linux, kamu juga bisa install lewat package manager distro."
        printf '%s\n' "Contoh Ubuntu/Debian: sudo apt install python3 python3-pip python3-tk"
        printf '\n'
    fi

    exit 1
fi

if ! "$PYTHON_CMD" --version >/dev/null 2>&1; then
    printf '\n%s\n\n' "Python belum bisa dijalankan dari terminal ini."
    printf '%s\n\n' "Install Python resmi dari: $DOWNLOAD_LINK"
    exit 1
fi

if ! "$PYTHON_CMD" -m pip --version >/dev/null 2>&1; then
    printf '\n%s\n\n' "Python ditemukan, tetapi pip belum tersedia."
    printf '%s\n' "Install pip terlebih dahulu agar proses build bisa berjalan."
    printf '%s\n\n' "Panduan resmi: https://pip.pypa.io/en/stable/installation/"

    if [ "$OS_NAME" = "Linux" ]; then
        printf '%s\n' "Contoh Ubuntu/Debian: sudo apt install python3-pip python3-tk"
        printf '\n'
    fi

    exit 1
fi

printf '\n%s\n' "Menyiapkan dependency aplikasi..."
"$PYTHON_CMD" -m pip install --upgrade pip
"$PYTHON_CMD" -m pip install --user -r "$APP_DIR/requirements.txt" || exit 1

printf '\n%s\n' "Menyiapkan PyInstaller..."
"$PYTHON_CMD" -m pip install --user pyinstaller || exit 1

printf '\n%s\n' "Membersihkan hasil build lama..."
rm -rf "$APP_DIR/build" "$APP_DIR/dist" "$APP_DIR/PlaylistGenerator.spec"

printf '\n%s\n' "Membuild Playlist Generator..."
"$PYTHON_CMD" -m PyInstaller \
    --onefile \
    --windowed \
    --name "$APP_NAME" \
    --collect-all tkinterdnd2 \
    --collect-all tinytag \
    --collect-all mutagen \
    "$APP_DIR/playlist_generator.py"

if [ $? -ne 0 ]; then
    printf '\n%s\n' "Build gagal. Cek pesan error di atas."
    exit 1
fi

printf '\n%s\n' "Build selesai."
printf '%s\n' "File aplikasi ada di:"
printf '%s\n\n' "$APP_DIR/dist/$APP_NAME"
