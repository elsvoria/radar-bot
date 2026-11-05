import os
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()

# Yedekli tanımlama: Önce .env'e bakar, bulamazsa doğrudan yazar
SUPABASE_URL = os.getenv("SUPABASE_URL") or "https://llbxzbyejbavcsfcpkvs.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY") or "sb_publishable_4vAqXoxhJxpdnrGIpQGFuA_xMCy68PJ"

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
