from curl_cffi import requests
from bs4 import BeautifulSoup
import json

def fetch_reposts_data(username):
    url = f"https://viewtikstories.com/profile/{username}?tab=reposts"
    try:
        response = requests.get(url, impersonate="chrome116", timeout=15)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, "html.parser")
        script_tag = soup.find("script", {"data-post-slides": True})
        
        if script_tag and script_tag.string:
            return json.loads(script_tag.string)
        return []
    except Exception as e:
        return []