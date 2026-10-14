# Private Video Downloader

A **desktop video downloader** with a clean, modern GUI. Drag in a link (or
paste it), pick quality, and download — powered by `yt-dlp` under the hood.

## Features
- Modern desktop UI (CustomTkinter)
- **Drag-and-drop** link support (`tkinterdnd2`)
- `yt-dlp` backend for site-aware, high-quality downloads
- Clean separation of `core/` (download logic) and `ui/` (interface)

## Stack
Python · CustomTkinter · yt-dlp

## Getting started
```bash
pip install -r requirements.txt
python main.py
```

## Notes
- Only download content you have the right to download.
