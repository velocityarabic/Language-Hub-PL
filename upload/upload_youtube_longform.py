"""
YouTube Long-Form Video Upload Script
Uploads video with title, description, tags, and thumbnail
"""

import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# YouTube API credentials
YT_CLIENT_ID = os.getenv("YT_CLIENT_ID")
YT_CLIENT_SECRET = os.getenv("YT_CLIENT_SECRET")
YT_REFRESH_TOKEN = os.getenv("YT_REFRESH_TOKEN")

def get_latest_video():
    """Find the most recently generated long-form video"""
    base_dir = Path(__file__).parent.parent
    longform_dir = base_dir / "output" / "longform_videos"

    if not longform_dir.exists():
        print("❌ No longform_videos directory found")
        return None

    # Get latest directory
    dirs = sorted([d for d in longform_dir.iterdir() if d.is_dir()], key=lambda x: x.stat().st_mtime, reverse=True)

    if not dirs:
        print("❌ No video directories found")
        return None

    latest_dir = dirs[0]
    print(f"📁 Found latest video: {latest_dir.name}")

    # Check for required files
    video_file = latest_dir / "final_video.mp4"
    info_file = latest_dir / "youtube_upload_info.txt"
    metadata_file = latest_dir / "video_metadata.json"

    if not video_file.exists():
        print(f"❌ Video file not found: {video_file}")
        return None

    # Use custom generated thumbnail (AI scenic background with text overlay)
    thumbnail_file = None
    if (latest_dir / "thumbnail.jpg").exists():
        thumbnail_file = latest_dir / "thumbnail.jpg"
        print(f"🖼️  Using custom thumbnail: thumbnail.jpg")
    else:
        phrase_images = sorted(latest_dir.glob("phrase_*.jpg"))
        if phrase_images:
            thumbnail_file = phrase_images[0]
            print(f"🖼️  Using phrase image as thumbnail: {thumbnail_file.name}")

    return {
        "dir": latest_dir,
        "video": video_file,
        "thumbnail": thumbnail_file,
        "info": info_file if info_file.exists() else None,
        "metadata": metadata_file if metadata_file.exists() else None
    }


def parse_upload_info(info_file):
    """Parse youtube_upload_info.txt to extract title and description"""
    if not info_file or not info_file.exists():
        return None, None
    
    with open(info_file, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Extract selected title
    title = None
    description = None
    
    try:
        # Find selected title section
        if "📝 SELECTED TITLE" in content:
            title_section = content.split("📝 SELECTED TITLE")[1]
            if "--------------------------------------------------------------------------------" in title_section:
                title = title_section.split("--------------------------------------------------------------------------------")[1].strip()
                title = title.split("\n")[0].strip()
        
        # Find description section
        if "📄 VIDEO DESCRIPTION:" in content:
            desc_section = content.split("📄 VIDEO DESCRIPTION:")[1]
            if "--------------------------------------------------------------------------------" in desc_section:
                description = desc_section.split("--------------------------------------------------------------------------------")[1].strip()
    except Exception as e:
        print(f"⚠️  Error parsing upload info: {e}")
    
    return title, description


def upload_to_youtube(video_info):
    """Upload video to YouTube using Google API"""
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        from googleapiclient.errors import HttpError
        import pickle
    except ImportError:
        print("❌ YouTube API libraries not installed.")
        print("   Install with: pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client")
        return False
    
    # Use BOTH scopes (must match what was used when generating the refresh token)
    SCOPES = [
        "https://www.googleapis.com/auth/youtube.upload",
        "https://www.googleapis.com/auth/youtube"
    ]
    API_SERVICE_NAME = "youtube"
    API_VERSION = "v3"

    # Try to use refresh token first
    if YT_REFRESH_TOKEN:
        print("🔑 Using refresh token for authentication...")
        try:
            # IMPORTANT: Don't pass scopes when using refresh token
            # Scopes are already bound to the token from initial authorization
            credentials = Credentials(
                None,
                refresh_token=YT_REFRESH_TOKEN,
                client_id=YT_CLIENT_ID,
                client_secret=YT_CLIENT_SECRET,
                token_uri="https://oauth2.googleapis.com/token"
            )
            credentials.refresh(Request())
            print("✅ Authentication successful!")
        except Exception as e:
            print(f"⚠️  Refresh token failed: {e}")
            credentials = None
    else:
        credentials = None
    
    if not credentials:
        print("❌ No valid YouTube credentials found.")
        print("   Please set YT_REFRESH_TOKEN in your .env or secrets")
        return False
    
    # Build YouTube API client
    youtube = build(API_SERVICE_NAME, API_VERSION, credentials=credentials)
    
    # Get title and description
    title = "Learn Polish with Velocity Polish"
    description = ""
    
    if video_info.get("metadata") and video_info["metadata"].exists():
        with open(video_info["metadata"], "r", encoding="utf-8") as f:
            metadata = json.load(f)
            title = metadata.get("selected_title", title)
            description = metadata.get("description", description)
    elif video_info.get("info"):
        parsed_title, parsed_desc = parse_upload_info(video_info["info"])
        if parsed_title:
            title = parsed_title
        if parsed_desc:
            description = parsed_desc
    
    # Truncate description if too long (YouTube limit: 5000 characters)
    if len(description) > 4800:
        description = description[:4800] + "\n\n... (truncated)"
    
    print(f"\n📹 Uploading video to YouTube...")
    print(f"   Title: {title[:80]}...")
    print(f"   Duration: ~{len(description.split('Phrases')[-1]) if 'Phrases' in description else 5} minutes")
    
    # Prepare video metadata
    video_metadata = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": [
                "Learn Polish",
                "Polish Phrases",
                "Polish Language",
                "Velocity Polish",
                "Polish for Beginners",
                "Language Learning"
            ],
            "categoryId": "27"  # Education
        },
        "status": {
            "privacyStatus": "public",  # Upload as public immediately
            "selfDeclaredMadeForKids": False
        }
    }
    
    # Upload video
    try:
        media = MediaFileUpload(str(video_info["video"]), chunksize=1024*1024*10, resumable=True)
        
        request = youtube.videos().insert(
            part=",".join(video_metadata.keys()),
            body=video_metadata,
            media_body=media
        )
        
        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                print(f"   Upload progress: {progress}%")
        
        video_id = response["id"]
        print(f"\n✅ Video uploaded successfully!")
        print(f"   Video ID: {video_id}")
        print(f"   URL: https://www.youtube.com/watch?v={video_id}")
        print(f"   Status: Public (visible to everyone)")
        
        # Upload thumbnail
        if video_info.get("thumbnail") and video_info["thumbnail"].exists():
            print(f"\n🖼️  Uploading custom thumbnail...")
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(str(video_info["thumbnail"]))
                ).execute()
                print(f"   ✅ Thumbnail uploaded successfully!")
            except HttpError as e:
                print(f"   ⚠️  Thumbnail upload failed: {e}")
                print(f"   You can manually upload thumbnail.jpg from the video directory")
        
        # Save upload result
        result_file = video_info["dir"] / "youtube_upload_result.json"
        with open(result_file, "w", encoding="utf-8") as f:
            json.dump({
                "video_id": video_id,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "status": "public",
                "uploaded_at": str(Path(video_info["dir"]).stat().st_mtime)
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n📄 Upload result saved to: {result_file}")
        
        return True
        
    except HttpError as e:
        print(f"\n❌ YouTube upload failed: {e}")
        if "quotaExceeded" in str(e):
            print("   ⚠️  Daily upload quota exceeded. Try again tomorrow.")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return False


def main():
    print("\n" + "="*80)
    print("🇵🇱 VELOCITY POLISH - YOUTUBE LONG-FORM UPLOADER 🇵🇱")
    print("="*80)
    
    # Find latest video
    video_info = get_latest_video()
    if not video_info:
        print("\n❌ No video found to upload")
        print("   Run youtube_longform_automation.py first to generate a video")
        return False
    
    print(f"\n📁 Video Directory: {video_info['dir']}")
    print(f"   🎬 Video: {video_info['video'].name}")
    print(f"   🖼️  Thumbnail: {video_info['thumbnail'].name if video_info.get('thumbnail') else 'Not found'}")
    
    # Confirm upload
    print(f"\n✅ Videos will be uploaded as PUBLIC")
    print(f"   They will be visible to everyone immediately")
    
    # Check if running in GitHub Actions (non-interactive)
    if os.getenv("GITHUB_ACTIONS") == "true":
        print(f"\n🤖 Running in GitHub Actions - auto-confirming upload")
        confirm = True
    else:
        response = input(f"\nProceed with upload? (yes/no): ").strip().lower()
        confirm = response in ["yes", "y"]
    
    if not confirm:
        print("❌ Upload cancelled")
        return False
    
    # Upload to YouTube
    success = upload_to_youtube(video_info)
    
    print("\n" + "="*80)
    if success:
        print("✅ UPLOAD COMPLETE!")
        print("   Check your YouTube Studio for the uploaded video")
        print("   Remember to change visibility from Private to Public")
    else:
        print("❌ UPLOAD FAILED")
        print("   Check the error messages above")
        print("   You can manually upload the video files from:")
        print(f"   {video_info['dir']}")
    print("="*80 + "\n")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
