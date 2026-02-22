@echo off
chcp 65001 >nul 2>&1
echo ============================================
echo   Cursor 完全清理脚本 (Windows)
echo   适配所有安装方式，删除全部残留
echo ============================================
echo.

:: 强制关闭 Cursor 进程
echo [1/4] 关闭 Cursor 进程...
taskkill /F /IM Cursor.exe >nul 2>&1
taskkill /F /IM "Cursor Helper.exe" >nul 2>&1
taskkill /F /IM "Cursor Helper (GPU).exe" >nul 2>&1
taskkill /F /IM "Cursor Helper (Renderer).exe" >nul 2>&1
taskkill /F /IM "Cursor Helper (Plugin).exe" >nul 2>&1
timeout /t 2 /nobreak >nul

:: 卸载（静默，如果有卸载程序的话）
echo [2/4] 尝试卸载 Cursor...
if exist "%LOCALAPPDATA%\Programs\cursor\Uninstall Cursor.exe" (
    "%LOCALAPPDATA%\Programs\cursor\Uninstall Cursor.exe" /S >nul 2>&1
    timeout /t 3 /nobreak >nul
)
if exist "%LOCALAPPDATA%\Programs\Cursor\Uninstall Cursor.exe" (
    "%LOCALAPPDATA%\Programs\Cursor\Uninstall Cursor.exe" /S >nul 2>&1
    timeout /t 3 /nobreak >nul
)

:: 删除所有 Cursor 目录
echo [3/4] 删除 Cursor 数据和缓存...

:: 用户数据（Roaming）
if exist "%APPDATA%\Cursor" (
    rmdir /s /q "%APPDATA%\Cursor"
    echo   已删除 %APPDATA%\Cursor
)

:: 本地数据（Local）
if exist "%LOCALAPPDATA%\Cursor" (
    rmdir /s /q "%LOCALAPPDATA%\Cursor"
    echo   已删除 %LOCALAPPDATA%\Cursor
)

:: 安装目录（Local\Programs）
if exist "%LOCALAPPDATA%\Programs\cursor" (
    rmdir /s /q "%LOCALAPPDATA%\Programs\cursor"
    echo   已删除 %LOCALAPPDATA%\Programs\cursor
)
if exist "%LOCALAPPDATA%\Programs\Cursor" (
    rmdir /s /q "%LOCALAPPDATA%\Programs\Cursor"
    echo   已删除 %LOCALAPPDATA%\Programs\Cursor
)

:: 用户主目录下的 .cursor
if exist "%USERPROFILE%\.cursor" (
    rmdir /s /q "%USERPROFILE%\.cursor"
    echo   已删除 %USERPROFILE%\.cursor
)

:: Cursor 更新缓存
if exist "%LOCALAPPDATA%\cursor-updater" (
    rmdir /s /q "%LOCALAPPDATA%\cursor-updater"
    echo   已删除 %LOCALAPPDATA%\cursor-updater
)
if exist "%LOCALAPPDATA%\Cursor-updater" (
    rmdir /s /q "%LOCALAPPDATA%\Cursor-updater"
    echo   已删除 %LOCALAPPDATA%\Cursor-updater
)

:: Temp 中的 Cursor 残留
for /d %%i in ("%TEMP%\cursor*") do (
    rmdir /s /q "%%i" >nul 2>&1
)
for /d %%i in ("%TEMP%\Cursor*") do (
    rmdir /s /q "%%i" >nul 2>&1
)

:: Program Files（少见但可能存在）
if exist "%PROGRAMFILES%\Cursor" (
    rmdir /s /q "%PROGRAMFILES%\Cursor"
    echo   已删除 %PROGRAMFILES%\Cursor
)
if exist "%PROGRAMFILES(x86)%\Cursor" (
    rmdir /s /q "%PROGRAMFILES(x86)%\Cursor"
    echo   已删除 %PROGRAMFILES(x86)%\Cursor
)

:: 清理注册表
echo [4/4] 清理注册表...
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\cursor" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\Cursor" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Uninstall\{cursor}" /f >nul 2>&1
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\cursor" /f >nul 2>&1
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\Uninstall\Cursor" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\App Paths\Cursor.exe" /f >nul 2>&1
reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\App Paths\cursor.exe" /f >nul 2>&1
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\App Paths\Cursor.exe" /f >nul 2>&1
reg delete "HKLM\Software\Microsoft\Windows\CurrentVersion\App Paths\cursor.exe" /f >nul 2>&1
echo   注册表已清理

echo.
echo ============================================
echo   清理完成！可以重新安装 Cursor 了
echo ============================================
pause
