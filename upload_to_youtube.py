"""
YouTube Upload Script for Velocity Polish
"""

import os, sys, json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

YT_CLIENT_ID = os.getenv("YT_CLIENT_ID")
YT_CLIENT_SECRET = os.getenv("YT_CLIENT_SECRET")
YT_REFRESH_TOKEN = os.getenv("YT_REFRESH_TOKEN")


def get_latest_video():
    base_dir = Path(__file__).parent
    longform_dir = base_dir / "output" / "longform_videos"
    if not longform_dir.exists():
        print("No longform_videos directory found")
        return None
    dirs = sorted([d for d in longform_dir.iterdir() if d.is_dir()], key=lambda x: x.stat().st_mtime, reverse=True)
    if not dirs:
        print("No video directories found")
        return None
    latest_dir = dirs[0]
    video_file = latest_dir / "final_video.mp4"
    metadata_file = latest_dir / "video_metadata.json"
    thumbnail_file = latest_dir / "thumbnail.jpg"
    if not thumbnail_file.exists():
        phrase_images = sorted(latest_dir.glob("phrase_*.jpg"))
        if phrase_images:
            thumbnail_file = phrase_images[0]
    return {"dir": latest_dir, "video": video_file, "thumbnail": thumbnail_file, "metadata": metadata_file if metadata_file.exists() else None}


def upload_to_youtube(video_info):
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from googleapiclient.errors import HttpError
    except ImportError:
        print("YouTube API libraries not installed.")
        return False

    if not YT_REFRESH_TOKEN:
        print("No refresh token found.")
        return False

    credentials = Credentials(None, refresh_token=YT_REFRESH_TOKEN, client_id=YT_CLIENT_ID, client_secret=YT_CLIENT_SECRET, token_uri="https://oauth2.googleapis.com/token")
    try:
        credentials.refresh(Request())
    except Exception as e:
        print(f"Auth failed: {e}")
        return False

    youtube = build("youtube", "v3", credentials=credentials)

    title = "Learn Polish with Velocity Polish"
    description = ""
    if video_info.get("metadata"):
        with open(video_info["metadata"], "r", encoding="utf-8") as f:
            meta = json.load(f)
            title = meta.get("selected_title", title)
            description = meta.get("description", "")

    video_metadata = {
        "snippet": {"title": title, "description": description[:4800],
                     "tags": ["Learn Polish", "Polish Phrases", "Polish Language", "Velocity Polish", "Polish for Beginners"],
                     "categoryId": "27"},
        "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False}
    }

    media = MediaFileUpload(str(video_info["video"]), chunksize=1024*1024*10, resumable=True)
    request = youtube.videos().insert(part=",".join(video_metadata.keys()), body=video_metadata, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload progress: {int(status.progress() * 100)}%")

    video_id = response["id"]
    print(f"Uploaded! Video ID: {video_id}")
    print(f"URL: https://www.youtube.com/watch?v={video_id}")

    if video_info.get("thumbnail") and video_info["thumbnail"].exists():
        try:
            youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(video_info["thumbnail"]))).execute()
            print("Thumbnail uploaded!")
        except HttpError as e:
            print(f"Thumbnail upload failed: {e}")

    result_file = video_info["dir"] / "youtube_upload_result.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump({"video_id": video_id, "title": title, "url": f"https://www.youtube.com/watch?v={video_id}"}, f)
    return True


def main():
    print("VELOCITY POLISH - YOUTUBE UPLOADER")
    video_info = get_latest_video()
    if not video_info:
        print("No video found to upload")
        return False
    print(f"Video: {video_info['video']}")
    print(f"Thumbnail: {video_info['thumbnail']}")
    return upload_to_youtube(video_info)


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
