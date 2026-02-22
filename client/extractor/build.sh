#!/bin/bash
# Apollo 凭证提取器打包脚本 (macOS) — PyArmor 加密
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DIST_DIR="$SCRIPT_DIR/dist"
ICON_ICNS="$SCRIPT_DIR/icon.icns"
ICON_ICO="$SCRIPT_DIR/icon.ico"
OBF_DIR="$SCRIPT_DIR/obfuscated"

echo "=== ApolloExtractor Build (加密) ==="

pip3 install pyinstaller -q 2>/dev/null

rm -rf "$DIST_DIR" "$SCRIPT_DIR/build_tmp" "$OBF_DIR"
mkdir -p "$OBF_DIR"

# PyArmor 加密
USE_OBF=false
if command -v pyarmor &> /dev/null; then
    echo "PyArmor 加密源码..."
    pyarmor gen --output "$OBF_DIR" "$SCRIPT_DIR/apollo_extractor.py"
    RUNTIME_PKG=$(ls -d "$OBF_DIR"/pyarmor_runtime_* 2>/dev/null | head -1 | xargs basename 2>/dev/null || echo "")
    if [ -n "$RUNTIME_PKG" ] && [ -d "$OBF_DIR/$RUNTIME_PKG" ]; then
        echo "  PyArmor runtime: $RUNTIME_PKG"
        USE_OBF=true
    else
        echo "  [WARN] PyArmor runtime 未找到，回退到明文"
    fi
else
    echo "  [WARN] PyArmor 未安装，回退到明文"
fi

# 选择图标
ICON_ARG=""
if [ "$(uname -s)" = "Darwin" ] && [ -f "$ICON_ICNS" ]; then
    ICON_ARG="--icon=$ICON_ICNS"
elif [ -f "$ICON_ICO" ]; then
    ICON_ARG="--icon=$ICON_ICO"
fi

# PyArmor 加密后 PyInstaller 无法自动分析 import，需要显式声明
STD_IMPORTS="--hidden-import=json --hidden-import=os --hidden-import=platform --hidden-import=sqlite3 --hidden-import=hashlib --hidden-import=urllib.request --hidden-import=urllib.error --hidden-import=tkinter --hidden-import=tkinter.ttk --hidden-import=tkinter.messagebox --hidden-import=tkinter.scrolledtext --hidden-import=pathlib --hidden-import=secrets"

if [ "$USE_OBF" = true ]; then
    echo "使用加密版本打包..."
    HIDDEN="--hidden-import=$RUNTIME_PKG $STD_IMPORTS"
    EXTRA_DATA="--add-data=$OBF_DIR/$RUNTIME_PKG:$RUNTIME_PKG"
    SRC="$OBF_DIR/apollo_extractor.py"
else
    echo "使用明文版本打包..."
    HIDDEN=""
    EXTRA_DATA=""
    SRC="$SCRIPT_DIR/apollo_extractor.py"
fi

pyinstaller \
    --onedir \
    --windowed \
    --name "ApolloExtractor" \
    $ICON_ARG \
    $HIDDEN \
    $EXTRA_DATA \
    --distpath "$DIST_DIR" \
    --workpath "$SCRIPT_DIR/build_tmp" \
    --clean -y \
    "$SRC"

if [ -d "$DIST_DIR/ApolloExtractor.app" ]; then
    echo ""
    echo "✓ 构建完成: $DIST_DIR/ApolloExtractor.app"
    du -sh "$DIST_DIR/ApolloExtractor.app"
else
    echo "✗ 构建失败"
    exit 1
fi
