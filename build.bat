@echo off
REM MusicDL Win 构建脚本
REM 用法: build.bat

echo ========================================
echo  MusicDL Win 构建脚本
echo ========================================

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.9+
    pause
    exit /b 1
)

REM 创建虚拟环境
echo [1/4] 创建虚拟环境...
if not exist venv (
    python -m venv venv
)

REM 激活虚拟环境
echo [2/4] 安装依赖...
call venv\Scripts\activate.bat

REM 升级 pip
python -m pip install --upgrade pip -q

REM 安装依赖
pip install -r requirements.txt -q

REM 下载 ffmpeg
echo [3/4] 下载 ffmpeg...
if not exist ffmpeg (
    python -c "import yt_dlp; print(yt_dlp.version.__version__)"
    REM 尝试用 yt-dlp 自带的 ffmpeg 下载器
    echo 注意: ffmpeg 会自动按需下载
)

REM PyInstaller 打包
echo [4/4] PyInstaller 打包...
pyinstaller ^
    --name "MusicDL" ^
    --onefile ^
    --windowed ^
    --icon=NONE ^
    --add-data "ffmpeg;ffmpeg" ^
    --hidden-import "yt_dlp" ^
    --hidden-import "yt_dlp.extractor" ^
    --hidden-import "yt_dlp.postprocessor" ^
    --hidden-import "yt_dlp.utils" ^
    --collect-all "yt_dlp" ^
    --noconfirm ^
    main.py

if errorlevel 1 (
    echo [错误] 打包失败
    pause
    exit /b 1
)

echo.
echo ========================================
echo  打包完成！
echo  输出目录: dist\MusicDL.exe
echo ========================================
pause
