# 🚀 yt-dlp Web Studio (Local Web Downloader & Editing Suite)

ระบบเว็บแอปพลิเคชันสำหรับ **ดาวน์โหลดวิดีโอ สื่อ เสียง คำบรรยาย และ Metadata** จากอินเทอร์เน็ตมากกว่า 1,700+ เว็บทั่วโลก (YouTube, TikTok, X, Facebook, Instagram, Reddit, Twitch, Bilibili, Douyin, Kuaishou, Weibo) พร้อมระบบเร่งความเร็วด้วย GPU, AI ถอดเสียง Whisper และเครื่องมือสร้างแฮชแท็กภาษาไทย/อังกฤษสำหรับตัดต่อวิดีโอ

---

## ⚡ คุณสมบัติเด่น (Features)

1. **⚡ Hardware GPU Acceleration:**  
   - ตรวจจับระบบฮาร์ดแวร์ GPU (NVIDIA NVENC, Intel QSV, AMD AMF) ให้อัตโนมัติ เพื่อเร่งความเร็วการแปลงไฟล์ (Transcoding), การตัดคลิป และการฝังซับเข้าเนื้อวิดีโอ (Burn-in)

2. **🎬 แพลตฟอร์มที่รองรับ 1,700+ เว็บทั่วโลก:**  
   - รองรับ YouTube, TikTok, X (Twitter), Facebook, Instagram, Reddit, Twitch, Vimeo, Dailymotion, Bilibili, Douyin, Kuaishou, Weibo และอื่นๆ

3. **🎯 ความละเอียดและฟอร์แมตไฟล์:**  
   - **วิดีโอ:** เลือกความละเอียด 4K (2160p), 2K (1440p), 1080p, 720p, 480p, Best Available
   - **เสียง:** แยกเสียงเฉพาะเป็น MP3 (320k), M4A, WAV (Uncompressed), FLAC (Lossless), AAC, Opus

4. **💬 ซับไตเติล & Metadata & Local Whisper AI:**  
   - โหลดซับคนทำ และซับสร้างอัตโนมัติ (Auto-caps) แปลงเป็น `.srt` หรือ `.vtt` หรือฝังลงวิดีโอ (`--embed-subs`)
   - **🤖 Local Whisper AI:** ถอดเสียงคำพูดสร้างซับภาษาไทย/อังกฤษให้อัตโนมัติ หากวิดีโอไม่มีซับต้นทาง
   - ฝังปก (Thumbnail), ชื่อคลิป, ผู้สร้าง, วันอัปโหลด และ Tags ลงใน Metadata ของไฟล์
   - **Dynamic Folder Routing:** จัดเก็บไฟล์แยกโฟลเดอร์ตามชื่อผู้สร้าง/แพลตฟอร์มอัตโนมัติ (`downloads/YouTube/Channel_Name/...`)

5. **🔍 ตรวจสอบคลิปซ้ำ (Duplicate Check) & เปิดโฟลเดอร์ตรง:**  
   - ระบบสแกนหาไฟล์ซ้ำก่อนดาวน์โหลด แจ้งเตือนเมื่อพบคลิปที่เคยดาวน์โหลดไว้แล้ว
   - ปุ่ม **`📂 เปิดโฟลเดอร์คลิปนี้`** ประจำอยู่ที่การ์ดคลิปและคลังไฟล์ กดแล้วเปิด Windows File Explorer ไปยังโฟลเดอร์เฉพาะคลิปนั้นทันที

6. **🇹🇭 Hashtags & Captions Studio (สำหรับตัดต่อ & ลงโซเชียล):**  
   - สร้างแฮชแท็กภาษาไทย/อังกฤษติดเทรนด์ (`#คลิปฮิต #คลิปเด็ด #ฟีด #ขึ้นฟีดเหอะ #ตัดต่อวิดีโอ #VideoEditing #Shorts #Reels #TikTok`)
   - แคปชันสั้น/แคปชันเต็ม/โน้ตสำหรับตัดต่อ พร้อมปุ่ม 1-Click Copy

---

## 🛠️ วิธีการเปิดใช้งาน (How to Run)

### วิธีที่ 1: ดับเบิลคลิกไฟล์ (Windows)
ดับเบิลคลิกที่ไฟล์:
```
D:\Project\yt-dlp-project\yt-dlp-web-downloader\run.bat
```

### วิธีที่ 2: รันผ่าน Command Line / PowerShell
```powershell
cd D:\Project\yt-dlp-project\yt-dlp-web-downloader
python run.py
```

### Regression Tests
```powershell
cd D:\Project\yt-dlp-project\yt-dlp-web-downloader
python run_regressions.py
```

This runs the backend completion regression and the headless browser folder-open regression in one command.

### ??????????????????
```powershell
git clone https://github.com/thanonhari/ytdlpatrrudownload.git
cd ytdlpatrrudownload
python -m venv .venv
.venv\Scripts\activate
pip install -r backend/requirements.txt
python run.py
```

??? repo ????????????? ?????? `git pull origin main` ??? `git clone`.

?????????? push ????????????????????? GitHub:
```powershell
git status
git add .
git commit -m "your message"
git push
```



จากนั้นเปิดเว็บเบราว์เซอร์ไปที่: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 📁 โครงสร้างโปรเจกต์ (Project Structure)
```
yt-dlp-web-downloader/
├── backend/
│   ├── app.py                 # FastAPI Main Server & WebSockets (Thread-safe event loop)
│   ├── downloader.py          # yt-dlp Core Engine & Event Hook
│   ├── gpu_checker.py         # Hardware GPU Acceleration Detector (NVENC/QSV/AMF)
│   ├── caption_generator.py   # Thai & English Hashtags & Caption Studio
│   ├── whisper_service.py     # Local Whisper AI Speech-to-Text
│   ├── cookie_manager.py      # Browser Cookies & cookies.txt Manager
│   ├── file_manager.py        # File Explorer API, Duplicate Check & Media Streamer
│   └── preset_manager.py      # Download Presets
├── frontend/
│   ├── index.html             # Glassmorphic Web UI
│   ├── css/style.css          # Design Tokens, Toast & Caption Studio Styles
│   └── js/
│       ├── app.js             # UI Logic, Rest API Fallbacks & Task Management
│       └── websocket.js       # Real-time Progress WebSockets
├── downloads/                 # โฟลเดอร์ปลายทางจัดเก็บไฟล์สื่อ
├── run.py                     # Launcher Script
├── run.bat                    # Batch Launcher
└── progress.md                # บันทึกสถานะการพัฒนาและการทดสอบ Close-The-Loop
```
