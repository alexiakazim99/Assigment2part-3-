import os
import time
import re
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI
from chat_client import send_message, get_messages, AGENT_NAME
from rate_limiter import RateLimiter

load_dotenv()
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1000000"))

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
    line = f"[{timestamp}] [{event}] {content}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def _one_line(value, max_len=300):
    text = str(value).replace("\n", "\\n").strip()
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text

def log_tool_call(tool_name, tool_input):
    log("tool", f"{tool_name} — {_one_line(tool_input)}")

rate_limiter = RateLimiter(max_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "10")))
last_seen = 0
total_tokens = 0
REPLY_MAX_TOKENS = int(os.getenv("REPLY_MAX_TOKENS", "1200"))
AGENT_ALIASES = [
    AGENT_NAME.lower(),
    AGENT_NAME.replace("-", "").lower(),
    "alexia",
    "kazim",
]
SOFTWARE_KEYWORDS = {
    "bug", "error", "fix", "debug", "issue", "stacktrace", "traceback", "exception",
    "test", "pytest", "unit test", "integration", "failing", "ci", "pipeline",
    "deploy", "docker", "compose", "build", "run", "command", "terminal",
    "api", "endpoint", "backend", "frontend", "database", "schema", "migration",
    "refactor", "review", "pr", "commit", "branch", "merge", "performance",
    "latency", "timeout", "auth", "token", "docs", "readme", "implementation",
    "code", "function", "class", "file", "python", "javascript", "typescript",
}

def normalize_text(text):
    return re.sub(r"\s+", " ", (text or "").strip().lower())

def is_directly_addressed(text):
    t = normalize_text(text)
    return any(f"@{alias}" in t or alias in t for alias in AGENT_ALIASES)

def has_software_context(text):
    t = normalize_text(text)
    return any(keyword in t for keyword in SOFTWARE_KEYWORDS)

def split_message(content, max_chars=4096):
    if not content:
        return [""]
    return [content[i:i + max_chars] for i in range(0, len(content), max_chars)]

print(f"Agent {AGENT_NAME} starting...")
log("start", f"Agent {AGENT_NAME} started")
log_tool_call("send_message", "online announcement")
send_message("alexia-kazim-agent is online and ready to help with software engineering tasks!")

while MAX_TOKENS <= 0 or total_tokens < MAX_TOKENS:
    load_dotenv(override=True)
    MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1000000"))
    rate_limiter.set_limit(int(os.getenv("RATE_LIMIT_PER_MINUTE", "10")))

    messages = get_messages(since=last_seen)

    if not messages:
        time.sleep(4)
        continue

    last_seen = messages[-1]["seq"]
    log("received", f"{len(messages)} nya meddelanden")

    others_messages = [m for m in messages if m["agent_name"] != AGENT_NAME]
    if not others_messages:
        time.sleep(4)
        continue

    latest_other = others_messages[-1]
    latest_text = latest_other.get("content", "")
    recent_other_text = " ".join(m.get("content", "") for m in others_messages[-8:])
    direct_assignment = is_directly_addressed(latest_text)
    likely_question = "?" in latest_text
    software_context = has_software_context(recent_other_text)
    should_respond = direct_assignment or likely_question or software_context

    conversation = [{"role": "system", "content": system_prompt}]
    for msg in messages[-20:]:
        role = "assistant" if msg["agent_name"] == AGENT_NAME else "user"
        conversation.append({
            "role": role,
            "content": f"[{msg['agent_name']}]: {msg['content']}",
        })

    conversation.append({
        "role": "user",
        "content": f"""You are {AGENT_NAME}. Decide whether to post in the group chat.

Be proactive and collaborative in software engineering discussions.
Reply with exactly PASS only when staying silent is clearly better.

Always respond if directly mentioned by name or alias, even without an @ tag.
A direct assignment includes instructions like "alexia write this code", "alexia fix this",
"kazim review this", or any message that tells you to do something.
Respond if you can meaningfully help with coding, documentation, reasoning, or discussion.
PASS if another agent already answered well or the task is done.
PASS if you have nothing concrete to add.

Signals:
- direct_assignment={direct_assignment}
- likely_question={likely_question}
- software_context={software_context}
- should_respond={should_respond}

If you respond, be concrete and helpful. You may include longer code examples when needed.
If your response is long, that's okay — it will be split into multiple chat messages automatically.""",
    })

    rate_limiter.wait_if_needed()

    log_tool_call(
        "chat.completions.create",
        {
            "model": os.getenv("MODEL"),
            "max_tokens": REPLY_MAX_TOKENS,
            "messages_count": len(conversation),
        },
    )
    response = client.chat.completions.create(
        model=os.getenv("MODEL"),
        messages=conversation,
        max_tokens=REPLY_MAX_TOKENS,
    )

    total_tokens += response.usage.total_tokens
    reply = response.choices[0].message.content.strip()

    log("tokens", f"{total_tokens}/{MAX_TOKENS}")

    if reply.upper() == "PASS":
        if direct_assignment:
            follow_up = conversation + [
                {"role": "assistant", "content": "PASS"},
                {
                    "role": "user",
                    "content": (
                        "The latest message directly assigned work to you by name. "
                        "You must answer with a concrete helpful response. Do not output PASS."
                    ),
                },
            ]
            rate_limiter.wait_if_needed()
            log_tool_call(
                "chat.completions.create",
                {
                    "model": os.getenv("MODEL"),
                    "max_tokens": REPLY_MAX_TOKENS,
                    "messages_count": len(follow_up),
                },
            )
            second_response = client.chat.completions.create(
                model=os.getenv("MODEL"),
                messages=follow_up,
                max_tokens=REPLY_MAX_TOKENS,
            )
            total_tokens += second_response.usage.total_tokens
            reply = second_response.choices[0].message.content.strip()

            if reply.upper() != "PASS":
                log("tokens", f"{total_tokens}/{MAX_TOKENS}")
            else:
                reply = "Yes, I can help with that. Please share any requirements or constraints, and I will provide a concrete solution."
        else:
            log("pass", f"PASS på senaste meddelandet från {latest_other.get('agent_name', 'okänd avsändare')}")
            time.sleep(4)
            continue

    parts = split_message(reply, max_chars=4096)
    total_parts = len(parts)
    for idx, part in enumerate(parts, start=1):
        outbound = f"[{idx}/{total_parts}] {part}" if total_parts > 1 else part
        log_tool_call("send_message", outbound)
        if send_message(outbound):
            log("sent", f"Skickade meddelande ({len(outbound)} tecken)")
        if idx < total_parts:
            time.sleep(1)

    time.sleep(4)

log_tool_call("send_message", "offline announcement")
send_message("alexia-kazim-agent is going offline. Goodbye!")
log("done", f"Agent finished — used {total_tokens} tokens")
print(f"Agent done — used {total_tokens} tokens.")