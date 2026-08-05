# MusicDL - 音乐下载工具

基于 yt-dlp 的 Windows 音乐下载工具，单文件，双击即用。

## 功能

- **单曲下载**：输入 YouTube/网易云/QQ音乐/Bilibili URL 或搜索关键词
- **批量下载**：粘贴歌手-歌名列表，批量下载
- **格式选择**：FLAC 无损 / MP3 320k / MP3 128k
- **代理支持**：支持 HTTP 代理（出国听歌必备）
- **自动 ffmpeg**：首次运行自动下载，无需手动配置

## 下载

直接下载 `dist/MusicDL.exe`，双击运行即可。

**下载地址**：[群文件 / NAS 共享 / ...]

## 使用方法

### 单曲下载
1. 在上方输入框粘贴 YouTube 视频链接或搜索关键词（如：`周杰伦 七里香`）
2. 选择格式（默认 FLAC）
3. 点击"下载"

### 批量下载
1. 格式参考：
   ```
   周杰伦 - 七里香
   Taylor Swift - Blank Space
   https://www.youtube.com/watch?v=xxxxx
   ```
2. 粘贴到下方文本框
3. 点击"开始批量下载"

### 代理设置
如果网络无法直接访问 YouTube，在代理框填写代理地址，例如：
- `http://127.0.0.1:7890`（Clash 默认）
- `http://127.0.0.1:1080`（V2Ray 默认）

## 构建（开发/自定义）

### 环境要求
- Python 3.9+
- Windows 10/11

### 构建步骤

```batch
# 1. 克隆/下载本项目，解压到任意目录

# 2. 进入目录，双击运行 build.bat
#    或在命令提示符中执行：
cd 音乐下载工具目录
build.bat
```

构建完成后，`dist/MusicDL.exe` 即为最终文件。

## 技术栈

- **yt-dlp** - 音视频下载核心
- **PySimpleGUI** - 图形界面
- **PyInstaller** - 打包成单文件 .exe

## 支持平台

| 平台 | 支持 |
|------|------|
| YouTube | ✅ FLAC/MP3 |
| 网易云音乐 | ✅ MP3（需代理） |
| QQ 音乐 | ✅ MP3（需代理） |
| Bilibili | ✅ 音频提取 |
| Spotify | ❌（ DRM 保护） |

## 常见问题

**Q: 下载失败，提示网络错误？**
A: 请确认代理设置正确，或确认本机网络可以访问目标网站。

**Q: 提示缺少 ffmpeg？**
A: 首次运行会自动下载，如果下载失败，请手动从 https://ffmpeg.org 下载并将 ffmpeg.exe 放到程序同目录的 ffmpeg/bin/ 下。

**Q: FLAC 格式无法播放？**
A: 部分老式车载播放器不支持 FLAC，请改用 MP3 320k 格式。
