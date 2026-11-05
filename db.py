import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"].strip()

print("KEY CHECK:", SUPABASE_KEY[:3], len(SUPABASE_KEY))

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def add_subscription(user_id: int, days: int, platforms: list):
    data = {
        "user_id": user_id,
        "days_active": days,
        "platforms": platforms,
        "status": "active"
    }
    return supabase.table("users").upsert(data, on_conflict="user_id").execute()

def add_target(user_id: int, target_username: str, platform: str):
    data = {
        "user_id": user_id,
        "target_username": target_username,
        "platform": platform
    }
    return supabase.table("targets").upsert(data, on_conflict="user_id, target_username, platform").execute()
