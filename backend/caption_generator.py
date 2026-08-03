import re
from typing import Dict, List, Any

def clean_tag(word: str) -> str:
    """Removes invalid characters for a hashtag."""
    cleaned = re.sub(r'[^\w\u0e00-\u0e7f]', '', word)
    return cleaned

def generate_hashtags(title: str = "", description: str = "", tags: List[str] = None, extractor: str = "") -> List[str]:
    """Generates a rich list of relevant Thai & English hashtags from video metadata."""
    hashtags = []
    seen = set()

    def add_tag(tag_str: str):
        if not tag_str.startswith("#"):
            tag_str = f"#{tag_str}"
        if tag_str not in seen and len(tag_str) > 2:
            seen.add(tag_str)
            hashtags.append(tag_str)

    # 1. Thai base trending hashtags
    thai_base = ["#คลิปฮิต", "#คลิปเด็ด", "#คลิปดัง", "#ฟีด", "#ขึ้นฟีดเหอะ", "#สาระน่ารู้", "#เทรนด์วันนี้", "#ตัดต่อวิดีโอ"]
    for tb in thai_base:
        add_tag(tb)

    # 2. English base hashtags
    eng_base = ["#VideoEditing", "#ContentCreator", "#Shorts", "#Reels", "#Viral", "#TikTok"]
    for eb in eng_base:
        add_tag(eb)

    # 3. Platform tag
    if extractor:
        add_tag(f"#{clean_tag(extractor.capitalize())}")

    # 4. Explicit video tags
    if tags:
        for t in tags[:10]:
            cleaned = clean_tag(t)
            if len(cleaned) >= 2:
                add_tag(f"#{cleaned}")

    # 5. Extract keywords from title
    if title:
        words = title.split()
        for w in words:
            cleaned = clean_tag(w)
            if len(cleaned) >= 2 and not cleaned.isdigit():
                add_tag(f"#{cleaned}")

    return hashtags[:20]

def create_caption_presets(info: Dict[str, Any], filepath: str = "") -> Dict[str, Any]:
    """Generates ready-to-use Thai & English captions and hashtags for social media and video editing."""
    title = info.get("title", "คลิปวิดีโอเด็ด")
    description = info.get("description", "") or ""
    uploader = info.get("uploader", "ผู้สร้างวิดีโอ")
    extractor = info.get("extractor", "Web")
    duration = info.get("duration_string") or "N/A"
    raw_tags = info.get("tags") or []

    hashtags_list = generate_hashtags(title, description, raw_tags, extractor)
    hashtags_text = " ".join(hashtags_list)

    # Short summary from description
    desc_summary = description.strip().split("\n")[0] if description else ""
    if len(desc_summary) > 180:
        desc_summary = desc_summary[:177] + "..."

    caption_short = f"🎬 {title}\n\n{hashtags_text}"

    caption_full = f"📌 {title}\n\n📝 รายละเอียด:\n{desc_summary or title}\n\n👤 ช่อง/ผู้สร้าง: {uploader}\n🌐 แหล่งที่มา: {extractor.capitalize()}\n\n{hashtags_text}"

    caption_editor = f"🎬 ชื่อคลิป: {title}\n⏱️ ความยาว: {duration}\n👤 ช่อง/ผู้สร้าง: {uploader}\n📁 ตำแหน่งไฟล์ในเครื่อง: {filepath or 'downloads/'}\n\n🏷️ แท็กภาษาไทย & อังกฤษสำหรับตัดต่อ:\n{hashtags_text}"

    # ----------------------------------------
    # New: Raw Metadata Archive for .caption.txt
    # ----------------------------------------
    webpage_url = info.get("webpage_url", info.get("original_url", "N/A"))
    upload_date = info.get("upload_date", "N/A")
    if len(upload_date) == 8 and upload_date.isdigit():
        upload_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}" # Format YYYY-MM-DD
    view_count = info.get("view_count", "N/A")
    like_count = info.get("like_count", "N/A")
    
    metadata_archive = (
        f"🔗 ลิงก์ต้นฉบับ (Original URL): {webpage_url}\n"
        f"👤 ช่อง/ผู้สร้าง (Uploader): {uploader}\n"
        f"📅 วันที่อัปโหลด (Upload Date): {upload_date}\n"
        f"👁️ ยอดวิว (Views): {view_count} | 👍 ยอดไลก์ (Likes): {like_count}\n"
        f"📝 ข้อความต้นฉบับ (Original Description):\n"
        f"----------------------------------------\n"
        f"{description}\n"
        f"----------------------------------------"
    )

    return {
        "title": title,
        "hashtags": hashtags_list,
        "hashtags_text": hashtags_text,
        "caption_short": caption_short,
        "caption_full": caption_full,
        "caption_editor": caption_editor,
        "metadata_archive": metadata_archive
    }
