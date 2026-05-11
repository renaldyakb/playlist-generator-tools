# Playlist Generator

Aplikasi GUI ringan untuk memilih file dari folder atau drag & drop, membuat kumpulan file secara random/manual/urut nama file, lalu meng-copy file ke folder tujuan dengan prefix nomor urut seperti `01.nama-file.mp3`.

## Fitur

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
pyinstaller --onefile --windowed --name PlaylistGenerator --collect-all tkinterdnd2 playlist_generator.py
```

Hasil build akan ada di folder `dist`.

Catatan: executable harus dibuild di OS target masing-masing. Build di Windows untuk `.exe`, build di macOS untuk aplikasi macOS, dan build di Linux untuk binary Linux.
