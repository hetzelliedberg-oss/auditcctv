"""
1-Click Deployer to Hugging Face Cloud (Free 24/7 CCTV AI Engine)
Creates Space: https://<username>-auditcctv.hf.space
Uploads all code, Xiaomi credentials, and AI models.
"""
import os
import sys
import glob
from huggingface_hub import HfApi, create_repo

def deploy(token: str):
    print("🚀 Initializing Hugging Face Cloud Deployment...")
    api = HfApi(token=token)
    user = api.whoami()
    username = user.get("name")
    print(f"👤 Logged in as: {username}")

    repo_id = f"{username}/auditcctv"
    print(f"📦 Target Space: {repo_id}")

    # 1. Create Space (Docker, Blank)
    try:
        url = create_repo(
            repo_id=repo_id,
            repo_type="space",
            space_sdk="docker",
            private=False, # Accessible from smartphone anywhere
            token=token,
            exist_ok=True
        )
        print(f"✅ Space created/verified: {repo_id}")
    except Exception as e:
        print(f"Space creation note: {e}")

    # 2. Files to upload
    files_to_upload = [
        "Dockerfile",
        "requirements.txt",
        "yolov8n.pt",
        "live_stream_daemon.py",
        "app_dashboard.py",
        "session_manager.py",
        "video_recorder.py",
        "camera_auto_stream.py",
        "device_sync.py",
        "query_devices_encrypted.py",
        "telegram_alert.py",
        "hf_cloud_sync.py",
        "data/authenticated_credentials.json",
        "data/all_real_devices.json",
    ]

    print(f"\n📤 Uploading {len(files_to_upload)} files to Cloud Space...")
    for f in files_to_upload:
        if os.path.exists(f):
            print(f"  ⬆️ Uploading {f}...")
            api.upload_file(
                path_or_fileobj=f,
                path_in_repo=f,
                repo_id=repo_id,
                repo_type="space"
            )

    # 3. Set HF_TOKEN secret so space can auto-sync database
    try:
        api.add_space_secret(repo_id=repo_id, key="HF_TOKEN", value=token)
        print("🔑 Configured HF_TOKEN secret for database auto-sync!")
    except Exception as e:
        print(f"Secret config note: {e}")

    live_url = f"https://{username.lower()}-auditcctv.hf.space"
    print("\n" + "="*60)
    print("🎉 DEPLOYMENT LAUNCHED TO CLOUD SUCCESSFULLY!")
    print(f"🌐 Permanent Live URL: {live_url}")
    print("📱 You can now bookmark this link on your smartphone!")
    print("💻 You can completely SHUT DOWN / TURN OFF this computer now!")
    print("="*60)
    return live_url

if __name__ == "__main__":
    if len(sys.argv) > 1:
        token = sys.argv[1].strip()
    else:
        token = os.environ.get("HF_TOKEN")
        if not token:
            token = input("Enter your Hugging Face Access Token (hf_...): ").strip()
    if token:
        deploy(token)
    else:
        print("❌ No token provided.")
