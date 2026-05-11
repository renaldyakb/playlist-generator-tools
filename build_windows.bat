@echo off
setlocal

title Build Playlist Generator

where py >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=py"
    goto check_python
)

where python >nul 2>nul
if %errorlevel%==0 (
    set "PYTHON_CMD=python"
    goto check_python
)

echo.
echo Python belum tersedia di komputer ini.
echo.
echo Untuk build aplikasi, install Python 3.10 atau yang lebih baru.
echo Download resmi: https://www.python.org/downloads/windows/
echo.
echo Saat install, centang opsi "Add python.exe to PATH".
echo.
pause
exit /b 1

:check_python
%PYTHON_CMD% --version >nul 2>nul
if not %errorlevel%==0 (
    echo.
    echo Python belum bisa dijalankan dari terminal ini.
    echo.
    echo Kemungkinan yang terdeteksi hanya alias Microsoft Store.
    echo Install Python resmi dari:
    echo https://www.python.org/downloads/windows/
    echo.
    echo Setelah install, buka terminal baru lalu jalankan build_windows.bat lagi.
    echo.
    pause
    exit /b 1
)

%PYTHON_CMD% -m pip --version >nul 2>nul
if not %errorlevel%==0 (
    echo.
    echo Python ditemukan, tetapi pip belum tersedia.
    echo Install ulang Python dari link resmi dan pastikan pip ikut dipasang:
    echo https://www.python.org/downloads/windows/
    echo.
    pause
    exit /b 1
)

echo.
echo Menyiapkan dependency aplikasi...
%PYTHON_CMD% -m pip install --upgrade pip
%PYTHON_CMD% -m pip install --user -r "%~dp0requirements.txt"
if not %errorlevel%==0 (
    echo.
    echo Gagal memasang dependency aplikasi.
    pause
    exit /b 1
)

echo.
echo Menyiapkan PyInstaller...
%PYTHON_CMD% -m pip install --user pyinstaller
if not %errorlevel%==0 (
    echo.
    echo Gagal memasang PyInstaller.
    pause
    exit /b 1
)

echo.
echo Membersihkan hasil build lama...
if exist "%~dp0build" rmdir /s /q "%~dp0build"
if exist "%~dp0dist" rmdir /s /q "%~dp0dist"
if exist "%~dp0PlaylistGenerator.spec" del /q "%~dp0PlaylistGenerator.spec"

echo.
echo Membuild Playlist Generator...
%PYTHON_CMD% -m PyInstaller ^
    --onefile ^
    --windowed ^
    --name PlaylistGenerator ^
    --collect-all tkinterdnd2 ^
    "%~dp0playlist_generator.py"

if not %errorlevel%==0 (
    echo.
    echo Build gagal. Cek pesan error di atas.
    pause
    exit /b 1
)

echo.
echo Build selesai.
echo File aplikasi ada di:
echo %~dp0dist\PlaylistGenerator.exe
echo.
pause
endlocal
