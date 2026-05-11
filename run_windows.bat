@echo off
setlocal

title Playlist Generator

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py"
    goto check_pip
)

where python >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=python"
    goto check_pip
)

echo.
echo Python belum tersedia di komputer ini.
echo.
echo Untuk menjalankan Playlist Generator, install Python 3.10 atau yang lebih baru.
echo Download resmi: https://www.python.org/downloads/windows/
echo.
echo Saat install, centang opsi "Add python.exe to PATH" agar script ini bisa berjalan.
echo.
pause
exit /b 1

:check_pip
%PYTHON_CMD% -m pip --version >nul 2>nul
if not %errorlevel%==0 (
    echo.
    echo Python ditemukan, tetapi pip belum tersedia.
    echo.
    echo Coba install ulang Python dari link resmi berikut dan pastikan opsi pip ikut dipasang:
    echo https://www.python.org/downloads/windows/
    echo.
    pause
    exit /b 1
)

%PYTHON_CMD% -c "import tkinterdnd2" >nul 2>nul
if not %errorlevel%==0 (
    echo.
    echo Menyiapkan fitur drag ^& drop...
    %PYTHON_CMD% -m pip install --user -r "%~dp0requirements.txt"
    if not %errorlevel%==0 (
        echo.
        echo Dependency drag ^& drop belum berhasil dipasang.
        echo Aplikasi tetap bisa dibuka, tetapi gunakan tombol Pilih Folder atau Pilih File.
        echo.
        pause
    )
)

echo.
echo Membuka Playlist Generator...
echo.
%PYTHON_CMD% "%~dp0playlist_generator.py"

if not %errorlevel%==0 (
    echo.
    echo Aplikasi berhenti dengan error. Cek pesan di atas untuk detailnya.
    echo.
    pause
    exit /b 1
)

endlocal
