import os
from dotenv import load_dotenv
from supabase import create_client, Client

# Şifre kasasını (.env) yüklüyoruz
load_dotenv()

# Anahtarları gizli dosyadan çekiyoruz
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def add_subscription(user_id: int, days: int, platforms: list):
    data = {
        "user_id": user_id,
        "days_active": days,
        "platforms": platforms,
        "status": "active"
    }
    response = supabase.table("users").upsert(data, on_conflict="user_id").execute()
    return response
    
def add_target(user_id: int, target_username: str, platform: str):
    data = {
        "user_id": user_id,
        "target_username": target_username,
        "platform": platform
    }
    response = supabase.table("targets").upsert(data, on_conflict="user_id, target_username, platform").execute()
    return response