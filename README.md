# 🎬 Private YouTube Video Downloader

A fast, lightweight, and modern web application to analyze and download YouTube videos in highest available quality (up to 4K / 2160p, 1080p, 720p, MP4, and WEBM).

![App Interface](https://img.shields.io/badge/Status-Active-brightgreen) ![Python](https://img.shields.io/badge/Python-3.8+-blue) ![Framework](https://img.shields.io/badge/Framework-Flask-black)

---

## ✨ Features

- ⚡ **High Speed Extraction**: Retrieves title, thumbnail, duration, and all resolution options instantly.
- 📺 **Full HD & 4K Support**: Download videos in 2160p (4K), 1440p (2K), 1080p, 720p, 480p, and 360p.
- 🎨 **Modern Dark UI**: Sleek glassmorphism interface with real-time progress indicators.
- 📦 **Estimated File Sizes**: Displays approximate download size for each resolution option.
- 🔒 **Privacy Focused**: Runs locally on your machine without third-party tracking.

---

## 🚀 Quick Start Guide

Follow these simple steps to run the application on your computer:

### 1. Prerequisites

Make sure you have [Python 3.8 or higher](https://www.python.org/downloads/) installed on your system.

### 2. Download / Clone Repository

Open your terminal or command prompt and run:

```bash
git clone https://github.com/Rohithsrr/youtube-downloader.git
cd youtube-downloader
```

### 3. Set Up Virtual Environment

#### On Windows (PowerShell / Command Prompt):
```powershell
python -m venv venv
.\venv\Scripts\activate
```

#### On Mac / Linux:
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the Application

```bash
python app.py
```

### 6. Open in Browser

Open your browser and navigate to:
👉 **[http://127.0.0.1:5000](http://127.0.0.1:5000)**

---

## 🛠️ Optional Enhancement (FFmpeg for 1080p & 4K Merging)

For resolutions above 720p (such as 1080p, 1440p, and 4K), YouTube provides separate video and audio streams. Installing **FFmpeg** allows the app to automatically merge high-definition video and audio streams into a single `.mp4` file.

- **Windows**: Download FFmpeg from [ffmpeg.org](https://ffmpeg.org/download.html) or run `winget install FFmpeg` in PowerShell.
- **Mac**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

---

## 📝 License

This project is open-source and free to use for personal education and utility.
