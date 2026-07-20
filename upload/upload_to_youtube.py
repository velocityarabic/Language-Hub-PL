"""
YouTube Upload Script - Updated for 2025

Uses refresh token from GitHub Secrets to upload videos.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import datetime

# Load environment variables
load_dotenv()

def get_authenticated_service():
    """Authenticate using refresh token from environment."""
    
    # Get credentials from GitHub Secrets
    client_id = (os.getenv('YOUTUBE_CLIENT_ID') or os.getenv('YT_CLIENT_ID', '')).strip()
    client_secret = (os.getenv('YOUTUBE_CLIENT_SECRET') or os.getenv('YT_CLIENT_SECRET', '')).strip()
    refresh_token = (os.getenv('YOUTUBE_REFRESH_TOKEN') or os.getenv('YT_REFRESH_TOKEN', '')).strip()
    
    # Debug info (masked)
    def mask(s): return f"{s[:4]}...{s[-4:]}" if s and len(s) > 8 else "MISSING"
    print(f"[youtube] Client ID: {mask(client_id)}")
    print(f"[youtube] Client Secret: {mask(client_secret)}")
    print(f"[youtube] Refresh Token: {mask(refresh_token)}")

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError(
            "Missing credentials! Set these environment variables:\n"
            "  - YOUTUBE_CLIENT_ID\n"
            "  - YOUTUBE_CLIENT_SECRET\n"
            "  - YOUTUBE_REFRESH_TOKEN"
        )
    
    # Create credentials from refresh token
    # IMPORTANT: Don't pass scopes - they're already bound to the refresh token
    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret
    )
    
    try:
        # Refresh to get access token
        creds.refresh(Request())
    except Exception as e:
        if "invalid_grant" in str(e).lower():
            print("\n❌ [youtube] AUTH ERROR: Refresh token has EXPIRED or been REVOKED.")
            print("💡 SOLUTION: You must generate a NEW refresh token.")
            print("   1. Go to Google Cloud Console.")
            print("   2. Ensure your 'OAuth Consent Screen' is in 'Production' or add yourself as a test user.")
            print("   3. Run a local script to get a new refresh token.")
        raise
    
    return build('youtube', 'v3', credentials=creds)

def generate_video_metadata(category: str, num_phrases: int, phrases: list = None):
    """Generate Spanish title, description, and tags for the video"""

    title = f"Spanish Learning: {num_phrases} Essential {category} Phrases 🇪🇸"

    # Build description with phrases if provided
    description_lines = [
        f"🇪🇸 Learn Spanish with Velocity Spanish! 🇪🇸",
        f"",
        f"📚 Category: {category}",
        f"",
        f"🎯 Master Spanish one phrase at a time! Today's {category} lesson:",
        f""
    ]

    # Add all phrases with emojis (same format as Facebook/Instagram)
    if phrases:
        emojis = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]
        for i, phrase in enumerate(phrases[:5], 0):
            emoji = emojis[i] if i < len(emojis) else f"{i+1}."
            description_lines.append(f"{emoji} {phrase['english']}")
            description_lines.append(f"   📍 {phrase['spanish']}")
            # Spanish uses 'pronunciation'
            pronunciation = phrase.get('pronunciation', '')
            description_lines.append(f"   🔊 [{pronunciation}]")
            description_lines.append("")

    # Call to action and hashtags
    description_lines.extend([
        f"💡 Tip: Repeat each phrase out loud 3 times!",
        f"👍 Like this video if you learned something new!",
        f"💬 Comment your favorite phrase below!",
        f"🔔 Subscribe for daily Spanish lessons!",
        f"",
        f"📖 Pronunciation Guide:",
        f"   The pronunciation spelling in brackets helps you say it correctly!",
        f"",
        f"#LearnSpanish #SpanishLessons #SpanishForBeginners #LanguageLearning",
        f"#Spanish #Education #Tutorial #DailySpanish #{category.replace(' ', '')}",
        f"#VelocitySpanish #SpanishPhrases #SpeakSpanish #Espanol"
    ])

    description = "\n".join(description_lines)

    tags = [
        "learn spanish",
        "spanish lessons",
        "spanish for beginners",
        "spanish phrases",
        "language learning",
        "spanish tutorial",
        "speak spanish",
        "espanol",
        category.lower(),
        "education",
        "daily spanish",
        "velocity spanish",
        "spanish learning"
    ]

    return title, description, tags

def upload_to_youtube(video_path, title, description, tags=None, category_id='22'):
    """Upload video to YouTube and return result."""
    if tags is None:
        tags = ['slapstick', 'animation', 'funny']
    youtube = get_authenticated_service()
    
    body = {
        'snippet': {
            'title': title,
            'description': description,
            'tags': tags,
            'categoryId': category_id
        },
        'status': {
            'privacyStatus': 'public',
            'selfDeclaredMadeForKids': False,
        }
    }
    
    if '#Shorts' not in body['snippet']['description']:
        body['snippet']['description'] += '\n\n#Shorts'
    
    media = MediaFileUpload(
        str(video_path),
        chunksize=-1,
        resumable=True,
        mimetype='video/mp4'
    )
    
    print(f"[youtube] Uploading: {title}")
    request = youtube.videos().insert(
        part=','.join(body.keys()),
        body=body,
        media_body=media
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"[youtube] Progress: {int(status.progress() * 100)}%")
    
    print(f"[youtube] ✅ Uploaded! Video ID: {response['id']}")
    print(f"[youtube] URL: https://youtube.com/shorts/{response['id']}")
    
    return response

def main():
    """Upload the generated video to YouTube."""
    video_file = Path('final_video.mp4')
    
    if not video_file.exists():
        print("[youtube] ❌ No video found at final_video.mp4")
        return
    
    # Simple test metadata
    title = "Slapstick Loops Daily"
    description = "#shorts #slapstick #cartoon #funny"
    tags = ['slapstick', 'cartoon', 'funny']
    
    # Upload
    try:
        upload_to_youtube(
            video_path=video_file,
            title=title,
            description=description,
            tags=tags,
            category_id='22'
        )
    except Exception as e:
        print(f"[youtube] ❌ Upload failed: {e}")
        raise

if __name__ == '__main__':
    main()
