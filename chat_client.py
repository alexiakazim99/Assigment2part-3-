import os
import requests
from dotenv import load_dotenv

load_dotenv()

HUB_URL = os.getenv("HUB_URL")
HUB_PASSWORD = os.getenv("HUB_PASSWORD")
AGENT_NAME = "alexia-developer"

def send_message(content):
    resp = requests.post(
        f"{HUB_URL}/api/message",
        json={
            "agent_name": AGENT_NAME,
            "content": content,
            "password": HUB_PASSWORD,
        },
    )
    return resp.status_code == 200

def get_messages(since=0):
    resp = requests.get(
        f"{HUB_URL}/api/messages",
        params={"since": since, "password": HUB_PASSWORD},
    )
    return resp.json().get("messages", [])