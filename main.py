#!/usr/bin/env python3
"""
MusicDL Win - 音乐下载工具 (Windows 单文件版)
支持: YouTube / 网易云 / QQ音乐 / Bilibili
首次运行自动下载 ffmpeg
"""

import subprocess
import sys
import os
import re
import json
import threading
import shutil
import zipfile
import struct

# ── GUI ──────────────────────────────────────────────────────────────────────
try:
    import PySimpleGUI as sg
except ImportError:
    sg = None

# ── 常量 ────────────────────────────────────────────────────────────────────
APP_NAME = "MusicDL"
VERSION = "1.0"


# ── ffmpeg 自动下载 ─────────────────────────────────────────────────────────
def get_ffmpeg_dir():
    """获取 ffmpeg 目录（内置优先）"""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))

    # 优先同目录 ffmpeg/bin
    local = os.path.join(base, 'ffmpeg', 'bin')
    if os.path.exists(os.path.join(local, 'ffmpeg.exe')):
        return local

    # 尝试用户数据目录
    user_dir = os.path.join(os.path.expanduser('~'), '.MusicDL', 'ffmpeg', 'bin')
    if os.path.exists(os.path.join(user_dir, 'ffmpeg.exe')):
        return user_dir

    return None


def ensure_ffmpeg(progress_callback=None):
    """确保 ffmpeg 存在，不存在则下载"""
    ffmpeg_dir = get_ffmpeg_dir()
    if ffmpeg_dir and os.path.exists(os.path.join(ffmpeg_dir, 'ffmpeg.exe')):
        return True

    # 下载 ffmpeg
    if progress_callback:
        progress_callback('正在下载 ffmpeg...')

    user_dir = os.path.join(os.path.expanduser('~'), '.MusicDL', 'ffmpeg')
    os.makedirs(user_dir, exist_ok=True)

    # 使用 essentials 版本（小体积）
    url = 'https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip'
    zip_path = os.path.join(user_dir, 'ffmpeg.zip')

    try:
        import urllib.request
        urllib.request.urlretrieve(url, zip_path)
    except Exception:
        # 备用源
        url = 'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'
        import urllib.request
        urllib.request.urlretrieve(url, zip_path)

    # 解压
    with zipfile.ZipFile(zip_path, 'r') as z:
        names = z.namelist()
        # 找 bin 目录
        bin_prefix = None
        for n in names:
            if re.match(r'.*/bin/ffmpeg\.exe$', n):
                bin_prefix = re.match(r'(.*/bin)/', n).group(1) + '/'
                break

        if not bin_prefix:
            raise Exception('无法从 zip 中找到 ffmpeg')

        bin_dir = os.path.join(user_dir, 'bin')
        os.makedirs(bin_dir, exist_ok=True)

        for n in names:
            if n.startswith(bin_prefix):
                rel = n[len(bin_prefix):]
                if n.endswith('/'):
                    os.makedirs(os.path.join(bin_dir, rel), exist_ok=True)
                else:
                    dest = os.path.join(bin_dir, rel)
                    data = z.read(n)
                    with open(dest, 'wb') as f:
                        f.write(data)

    os.remove(zip_path)

    if progress_callback:
        progress_callback('ffmpeg 下载完成')

    return True


# ── 下载核心 ────────────────────────────────────────────────────────────────
def download_one(url_or_search, music_dir, audio_format, proxy, progress_callback):
    """下载单首歌，返回 (success, message)"""
    ffmpeg_dir = get_ffmpeg_dir()

    # 判断来源
    if url_or_search.startswith('http://') or url_or_search.startswith('https://'):
        source = url_or_search
    else:
        source = f"ytsearch1:{url_or_search}"

    # 格式参数
    if audio_format == 'flac':
        ext_args = ['-x', '--audio-format', 'flac', '--audio-quality', '0']
    elif audio_format == '320k':
        ext_args = ['-x', '--audio-format', 'mp3', '--audio-quality', '0']
    else:
        ext_args = ['-x', '--audio-format', 'mp3', '--audio-quality', '2']

    # 构建输出路径
    safe = re.sub(r'[<>:"/\\|?*]', '_', url_or_search.strip())[:80]
    out = os.path.join(music_dir, f'{safe}.%(ext)s')

    cmd = [
        sys.executable, '-m', 'yt_dlp',
        '--no-playlist',
        *ext_args,
        '-o', out,
    ]

    if proxy:
        cmd += ['--proxy', proxy]

    if ffmpeg_dir:
        cmd += ['--ffmpeg-location', ffmpeg_dir]

    cmd.append(source)

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        )

        for line in proc.stdout:
            line = line.strip()
            if progress_callback and '[download]' in line and '%' in line:
                m = re.search(r'(\d+\.\d+)%', line)
                if m:
                    progress_callback(float(m.group(1)))
            elif progress_callback and 'has already been downloaded' in line.lower():
                progress_callback(100)
                return True, '已存在，跳过'

        proc.wait()
        progress_callback(100)
        return (proc.returncode == 0), ('下载完成' if proc.returncode == 0 else f'失败 (code {proc.returncode})')
    except Exception as e:
        return False, str(e)


def parse_playlist(text):
    """解析粘贴的列表"""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    songs = []
    for line in lines:
        if ' - ' in line:
            parts = line.split(' - ', 1)
            artist, track = parts[0].strip(), parts[1].strip()
        else:
            artist, track = '', line.strip()

        if track.startswith('http'):
            songs.append(('', track, 'url'))
        elif artist.startswith('http'):
            songs.append(('', artist, 'url'))
        else:
            songs.append((artist, track, 'search'))

    return songs


# ── GUI 模式 ────────────────────────────────────────────────────────────────
def run_gui():
    sg.theme('DarkBlue13')

    layout = [
        [sg.Text(f'{APP_NAME} v{VERSION}', font=('微软雅黑', 14, 'bold'), text_color='#00BFFF')],
        [sg.Text('─' * 65, text_color='#444444')],

        # 代理
        [sg.Text('代理:', font=('微软雅黑', 9)),
         sg.Input(key='proxy', size=(42, 1), default_text='http://127.0.0.1:7890'),
         sg.Text('HTTP 代理，留空直连', font=('微软雅黑', 8), text_color='#666666')],

        # 保存目录
        [sg.Text('保存:', font=('微软雅黑', 9)),
         sg.Input(key='outdir', size=(42, 1),
                  default_text=os.path.join(os.path.expanduser('~'), 'Music')),
         sg.FolderBrowse('浏览', target='outdir', font=('微软雅黑', 9))],

        # 格式
        [sg.Text('格式:', font=('微软雅黑', 9)),
         sg.Radio('FLAC', 'fmt', key='fmt_flac', default=True, font=('微软雅黑', 9)),
         sg.Radio('MP3 320k', 'fmt', key='fmt_320', font=('微软雅黑', 9)),
         sg.Radio('MP3 128k', 'fmt', key='fmt_128', font=('微软雅黑', 9))],

        [sg.Text('─' * 65, text_color='#444444')],

        # 单曲
        [sg.Text('单曲下载（URL 或搜索关键词）:', font=('微软雅黑', 10))],
        [sg.Input(key='single', size=(62, 1),
                  default_text='https://www.youtube.com/watch?v=...'),
         sg.Button('下载', key='dl_single', bind_return_key=True, font=('微软雅黑', 9))],

        [sg.Text('─' * 65, text_color='#444444')],

        # 批量
        [sg.Text('批量下载（每行: 歌手 - 歌名，或直接粘 URL）:', font=('微软雅黑', 10))],
        [sg.Multiline(key='batch', size=(65, 8), font=('Consolas', 9),
                      autoscroll=True, scrollbar=True)],
        [sg.Button('开始批量下载', key='dl_batch', font=('微软雅黑', 9)),
         sg.Button('停止', key='dl_stop', font=('微软雅黑', 9), disabled=True)],

        [sg.Text('─' * 65, text_color='#444444')],

        # 日志
        [sg.Text('日志:', font=('微软雅黑', 9)),
         sg.Text('', key='status', font=('微软雅黑', 9), text_color='#00FF00')],
        [sg.Multiline(key='log', size=(72, 8), font=('Consolas', 8),
                      autoscroll=True, readonly=True, text_color='#AAAAAA', rstrip=True)],
    ]

    window = sg.Window(
        f'{APP_NAME} - 音乐下载',
        layout,
        font=('微软雅黑', 10),
        finalize=True,
    )

    stop_flag = threading.Event()

    def log(msg):
        window['log'].print(msg)

    def fmt_from_values(values):
        return 'flac' if values['fmt_flac'] else ('320k' if values['fmt_320'] else '128k')

    # 启动时检查 ffmpeg
    window.perform_long_operation(lambda: ensure_ffmpeg(), '-FFMPEG_OK-')
    log('[提示] 首次运行会自动下载 ffmpeg，请稍候...')

    while True:
        event, values = window.read()

        if event in (sg.WIN_CLOSED, None):
            stop_flag.set()
            break

        if event == '-FFMPEG_OK-':
            log('[OK] ffmpeg 已就绪')
            window['dl_single'].update(disabled=False)

        elif event == 'dl_single':
            url = values['single'].strip()
            if not url:
                continue
            outdir = values['outdir'].strip() or os.path.expanduser('~/Music')
            os.makedirs(outdir, exist_ok=True)
            fmt = fmt_from_values(values)
            proxy = values['proxy'].strip() or None

            log(f'[单曲] {url}')
            window['dl_single'].update(disabled=True)
            window['dl_batch'].update(disabled=True)

            def do():
                ok, msg = download_one(url, outdir, fmt, proxy, None)
                window.write_event_value('-SINGLE_DONE-', (ok, msg))

            threading.Thread(target=do, daemon=True).start()

        elif event == '-SINGLE_DONE-':
            ok, msg = values['-SINGLE_DONE-']
            log(f'[结果] {msg}')
            window['dl_single'].update(disabled=False)
            window['dl_batch'].update(disabled=False)

        elif event == 'dl_batch':
            text = values['batch'].strip()
            if not text:
                continue
            songs = parse_playlist(text)
            if not songs:
                continue

            outdir = values['outdir'].strip() or os.path.expanduser('~/Music')
            os.makedirs(outdir, exist_ok=True)
            fmt = fmt_from_values(values)
            proxy = values['proxy'].strip() or None

            log(f'[批量] {len(songs)} 首 | {fmt} | 代理:{proxy or "直连"}')
            stop_flag.clear()
            window['dl_batch'].update(disabled=True)
            window['dl_stop'].update(disabled=False)
            window['dl_single'].update(disabled=True)

            def do_batch():
                ok = skip = fail = 0
                for i, (artist, track, stype) in enumerate(songs):
                    if stop_flag.is_set():
                        log(f'\n[停止] 已处理 {i} 首')
                        break

                    src = track if stype == 'url' else (f'{artist} {track}' if artist else track)
                    log(f'\n[{i+1}/{len(songs)}] {src}')

                    # 查是否已存在
                    exists = any(
                        os.path.exists(os.path.join(outdir, f'{src}.{ext}'))
                        for ext in ['flac', 'mp3', 'm4a', 'wav']
                    )
                    if exists:
                        log('  → 已存在，跳过')
                        skip += 1
                        continue

                    ok2, msg = download_one(src, outdir, fmt, proxy, None)
                    log(f'  → {msg}')
                    if ok2:
                        ok += 1
                    else:
                        fail += 1

                log(f'\n[完成] 成功:{ok} 跳过:{skip} 失败:{fail}')
                window.write_event_value('-BATCH_DONE-', None)

            threading.Thread(target=do_batch, daemon=True).start()

        elif event == '-BATCH_DONE-':
            window['dl_batch'].update(disabled=False)
            window['dl_stop'].update(disabled=True)
            window['dl_single'].update(disabled=False)

        elif event == 'dl_stop':
            stop_flag.set()
            log('[停止中...]')
            window['dl_stop'].update(disabled=True)

    window.close()


# ── 命令行模式 ──────────────────────────────────────────────────────────────
def run_cli():
    print(f'{APP_NAME} v{VERSION}')
    if len(sys.argv) > 1:
        url = sys.argv[1]
        outdir = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.expanduser('~'), 'Music')
        fmt = sys.argv[3] if len(sys.argv) > 3 else 'flac'
        proxy = sys.argv[4] if len(sys.argv) > 4 else None
        os.makedirs(outdir, exist_ok=True)
        ok, msg = download_one(url, outdir, fmt, proxy, None)
        print(msg)
    else:
        run_gui()


if __name__ == '__main__':
    if sg is None:
        print('[警告] PySimpleGUI 未安装，命令行模式')
        run_cli()
    elif len(sys.argv) > 1:
        run_cli()
    else:
        run_gui()
