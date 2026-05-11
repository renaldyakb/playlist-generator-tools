# Playlist Generator

[![GitHub stars](https://img.shields.io/github/stars/renaldyakb/playlist-generator-tools?style=for-the-badge&logo=github&color=24705d)](https://github.com/renaldyakb/playlist-generator-tools/stargazers)
[![Total downloads](https://img.shields.io/github/downloads/renaldyakb/playlist-generator-tools/total?style=for-the-badge&logo=github&color=24705d)](https://github.com/renaldyakb/playlist-generator-tools/releases)
[![Latest release](https://img.shields.io/github/v/release/renaldyakb/playlist-generator-tools?style=for-the-badge&logo=github&color=24705d)](https://github.com/renaldyakb/playlist-generator-tools/releases/latest)
[![Windows build](https://img.shields.io/github/actions/workflow/status/renaldyakb/playlist-generator-tools/release.yml?branch=main&style=for-the-badge&logo=githubactions&label=build)](https://github.com/renaldyakb/playlist-generator-tools/actions/workflows/release.yml)

Aplikasi GUI ringan untuk memilih file dari folder atau drag & drop, membuat kumpulan file secara random/manual/urut nama file, lalu meng-copy file ke folder tujuan dengan prefix nomor urut seperti `01.nama-file.mp3`.

## Fitur

- Link GitHub, Star Repo, dan Latest Release langsung dari header aplikasi.
- Pilih folder sumber, pilih beberapa file, atau drag & drop folder/file.
- Deteksi jenis file:
  - Musik
  - Gambar
  - Video
  - PDF
- Tampilkan jumlah file per jenis.
- Filter file yang ingin digenerate dengan checklist jenis file.
- Tentukan jumlah file per jenis dengan slider/spinbox, misalnya Musik 8, Gambar 10, Video 2, PDF 1.
- Mode pilihan:
  - Random
  - Urut sesuai nama file
  - Pilih manual dari daftar
- Copy file terpilih ke folder tujuan.
- Preview file ditampilkan dalam bentuk tree per jenis file.
- Timestamp YouTube otomatis untuk file audio dan video, dipisah per kategori.
- Tombol copy timestamp setelah generate berhasil.
- Jika output berisi lebih dari satu jenis file, aplikasi otomatis membuat subfolder seperti `Musik`, `Gambar`, `Video`, dan `PDF`.
- Jika output hanya berisi satu jenis file, file langsung dicopy ke folder tujuan tanpa subfolder tambahan.
- Prefix urutan otomatis: `01.`, `02.`, `03.`, dan seterusnya.
- Jika nama file tujuan sudah ada, aplikasi membuat nama aman seperti `01.nama-file (2).mp3`.

## Cara Menjalankan

Pastikan Python 3.10 atau lebih baru sudah terpasang.

### Windows

Double click:

```text
run_windows.bat
```

Script akan mengecek apakah Python dan pip tersedia. Jika belum, script akan menampilkan link download resmi. Script juga akan mencoba memasang dependency ringan `tkinterdnd2` untuk fitur drag & drop.

### macOS / Linux

Jalankan dari terminal:

```bash
chmod +x run_unix.sh
./run_unix.sh
```

Script akan mengecek apakah Python dan pip tersedia. Jika belum, script akan menampilkan instruksi dan link download resmi. Script juga akan mencoba memasang dependency ringan `tkinterdnd2` untuk fitur drag & drop.

### Manual

```bash
python playlist_generator.py
```

Di beberapa sistem, perintahnya bisa:

```bash
python3 playlist_generator.py
```

Catatan timestamp: aplikasi akan mencoba membaca durasi audio/video dengan `ffprobe` jika tersedia, lalu fallback ke `mutagen` dan `tinytag`. Untuk video tertentu, `ffprobe` tetap direkomendasikan agar durasinya terbaca akurat.

## Build Menjadi Executable

### Windows

Jalankan:

```text
build_windows.bat
```

Hasil build:

```text
dist\PlaylistGenerator.exe
```

### macOS / Linux

Jalankan:

```bash
chmod +x build_unix.sh
./build_unix.sh
```

Hasil build:

```text
dist/PlaylistGenerator
```

### Manual

Opsional, jika ingin build sendiri:

```bash
pip install pyinstaller
pip install -r requirements.txt
pyinstaller --onefile --windowed --name PlaylistGenerator --collect-all tkinterdnd2 --collect-all tinytag --collect-all mutagen playlist_generator.py
```

Hasil build akan ada di folder `dist`.

Catatan: executable harus dibuild di OS target masing-masing. Build di Windows untuk `.exe`, build di macOS untuk aplikasi macOS, dan build di Linux untuk binary Linux.

## Release GitHub

Release Windows otomatis dibuat oleh GitHub Actions saat tag versi baru dipush, misalnya:

```bash
git tag v1.0.1
git push origin v1.0.1
```
