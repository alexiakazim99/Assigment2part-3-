import os
import time
from datetime import datetime
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

os.makedirs("logs", exist_ok=True)
LOG_FILE = "logs/agent.log"

def log(event, content):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a") as f:
        f.write(f"[{timestamp}] {event.upper()}: {content}\n")

rate_limiter = RateLimiter(max_per_minute=10)
last_seen = 0
total_tokens = 0
MAX_TOKENS = 50000

print(f"Agent {AGENT_NAME} starting...")
log("start", f"Agent {AGENT_NAME} started")
send_message("alexia-kazim-agent is online and ready to help with software engineering tasks!")

while total_tokens < MAX_TOKENS:
    messages = get_messages(since=last_seen)

    if not messages:
        time.sleep(4)
        continue

    last_seen = messages[-1]["seq"]
    log("received", f"{len(messages)} new messages")

    conversation = [{"role": "system", "content": system_prompt}]
    for msg in messages[-20:]:
        role = "assistant" if msg["agent_name"] == AGENT_NAME else "user"
        conversation.append({
            "role": role,
            "content": f"[{msg['agent_name']}]: {msg['content']}",
        })

    conversation.append({
        "role": "user",
        "content": "Based on the conversation above, write a helpful response. Only reply with exactly 'PASS' if the message is completely irrelevant to software engineering or already fully answered.",
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
        log("pass", "Agent decided not to respond")
        time.sleep(4)
        continue

    if send_message(reply):
        log("sent", reply)
        print(f"[{AGENT_NAME}]: {reply[:80]}")

    time.sleep(4)

send_message("alexia-kazim-agent is going offline. Goodbye!")
log("done", f"Agent finished — used {total_tokens} tokens")
print(f"Agent done — used {total_tokens} tokens.")