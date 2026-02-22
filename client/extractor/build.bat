@echo off
REM Apollo 凭证提取器打包脚本 (Windows) — PyArmor 加密
echo === ApolloExtractor Build ===

cd /d "%~dp0"

pip install pyinstaller -q 2>nul

if exist dist rmdir /s /q dist
if exist obfuscated rmdir /s /q obfuscated
if exist build_tmp rmdir /s /q build_tmp

REM PyArmor 加密
set USE_OBF=0
where pyarmor >nul 2>nul
if %ERRORLEVEL%==0 (
    echo PyArmor 加密源码...
    mkdir obfuscated 2>nul
    pyarmor gen --output obfuscated apollo_extractor.py
    if exist obfuscated\apollo_extractor.py (
        REM 查找 pyarmor_runtime 目录
        for /d %%D in (obfuscated\pyarmor_runtime_*) do (
            set RUNTIME_PKG=%%~nxD
            set USE_OBF=1
            echo   PyArmor runtime: %%~nxD
        )
    )
)

REM 选择图标
set ICON_ARG=
if exist icon.ico set ICON_ARG=--icon=icon.ico

if "%USE_OBF%"=="1" (
    echo 使用加密版本打包...
    pyinstaller --onefile --windowed --name ApolloExtractor %ICON_ARG% --hidden-import=%RUNTIME_PKG% --add-data "obfuscated\%RUNTIME_PKG%;%RUNTIME_PKG%" --distpath dist --workpath build_tmp --clean -y obfuscated\apollo_extractor.py
) else (
    echo 使用明文版本打包...
    pyinstaller --onefile --windowed --name ApolloExtractor %ICON_ARG% --distpath dist --workpath build_tmp --clean -y apollo_extractor.py
)

if exist dist\ApolloExtractor.exe (
    echo.
    echo √ 构建完成: dist\ApolloExtractor.exe
    for %%A in (dist\ApolloExtractor.exe) do echo   大小: %%~zA bytes
) else (
    echo × 构建失败
    exit /b 1
)
pause
