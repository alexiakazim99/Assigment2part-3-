import os
import time
from dotenv import load_dotenv
from openai import OpenAI
from chat_client import send_message, get_messages, AGENT_NAME
from rate_limiter import RateLimiter

load_dotenv()

client = OpenAI(
    base_url=os.getenv("BASE_URL"),
    api_key=os.getenv("API_KEY"),
)

with open("config/system_prompt.md", "r") as f:
    system_prompt = f.read()

rate_limiter = RateLimiter(max_per_minute=10)
last_seen = 0
messages_sent = 0
MAX_MESSAGES = 10
total_tokens = 0
MAX_TOKENS = 50000

print(f"Agent {AGENT_NAME} starting...")

while messages_sent < MAX_MESSAGES and total_tokens < MAX_TOKENS:
    messages = get_messages(since=last_seen)
    
    if not messages:
        time.sleep(4)
        continue
    
    last_seen = messages[-1]["seq"]
    
    conversation = [{"role": "system", "content": system_prompt}]
    for msg in messages[-20:]:
        role = "assistant" if msg["agent_name"] == AGENT_NAME else "user"
        conversation.append({
            "role": role,
            "content": f"[{msg['agent_name']}]: {msg['content']}",
        })
    
    conversation.append({
        "role": "user",
        "content": "Based on the conversation above, write a short response "
                   "OR reply with exactly 'PASS' if you have nothing to add.",
    })
    
    rate_limiter.wait_if_needed()
    
    response = client.chat.completions.create(
        model=os.getenv("MODEL"),
        messages=conversation,
        max_tokens=300,
    )
    
    total_tokens += response.usage.total_tokens
    reply = response.choices[0].message.content.strip()
    
    print(f"Tokens used: {total_tokens}/{MAX_TOKENS}")
    
    if reply.upper() == "PASS":
        time.sleep(4)
        continue
    
    if send_message(reply):
        messages_sent += 1
        print(f"[{AGENT_NAME}] ({messages_sent}/{MAX_MESSAGES}): {reply[:80]}")
    
    time.sleep(4)

print(f"Agent done — sent {messages_sent} messages, used {total_tokens} tokens.")