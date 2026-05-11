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
        ;;
    Linux)
        DOWNLOAD_LINK="https://www.python.org/downloads/"
        ;;
    *)
        DOWNLOAD_LINK="https://www.python.org/downloads/"
        ;;
esac

PYTHON_CMD=$(find_python || true)

if [ -z "$PYTHON_CMD" ]; then
    printf '\n%s\n\n' "Python belum tersedia di komputer ini."
    printf '%s\n' "Untuk menjalankan Playlist Generator, install Python 3.10 atau yang lebih baru."
    printf '%s\n\n' "Download resmi: $DOWNLOAD_LINK"

    if [ "$OS_NAME" = "Linux" ]; then
        printf '%s\n' "Di Linux, kamu juga bisa install lewat package manager distro."
        printf '%s\n' "Contoh Ubuntu/Debian: sudo apt install python3 python3-pip python3-tk"
        printf '\n'
    fi

    exit 1
fi

if ! "$PYTHON_CMD" -m pip --version >/dev/null 2>&1; then
    printf '\n%s\n\n' "Python ditemukan, tetapi pip belum tersedia."
    printf '%s\n' "Install pip terlebih dahulu agar setup Python lengkap."
    printf '%s\n\n' "Panduan resmi: https://pip.pypa.io/en/stable/installation/"

    if [ "$OS_NAME" = "Linux" ]; then
        printf '%s\n' "Contoh Ubuntu/Debian: sudo apt install python3-pip python3-tk"
        printf '\n'
    fi

    exit 1
fi

if ! "$PYTHON_CMD" -c "import tkinterdnd2" >/dev/null 2>&1; then
    printf '\n%s\n' "Menyiapkan fitur drag & drop..."
    if ! "$PYTHON_CMD" -m pip install --user -r "$APP_DIR/requirements.txt"; then
        printf '\n%s\n' "Dependency drag & drop belum berhasil dipasang."
        printf '%s\n\n' "Aplikasi tetap bisa dibuka, tetapi gunakan tombol Pilih Folder atau Pilih File."
    fi
fi

printf '\n%s\n\n' "Membuka Playlist Generator..."
"$PYTHON_CMD" "$APP_DIR/playlist_generator.py"
