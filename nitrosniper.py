import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
import json
from datetime import datetime
import re
from fastapi import FastAPI
import uvicorn
import threading

# Initialize FastAPI
app = FastAPI()

# Health check endpoint for UptimeRobot
@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# Configuration
GITHUB_TOKEN = "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"
MAIN_TOKEN = "MTIxMDQwMjYwODA3MDc5MTIzMA.GEtAXD.nLsEWxm9IKsmFyiJY3Nlso-zO7F84oZNsRrCxQ"
BOT_TOKEN = "MTMzNzQzMjcyMzk0MTM2MzgwNg.G5xdmo.9b5AIimcJBzl0hnzUpi7ZGCCV2JzDhZ4gXssbw"
WEBHOOK_URL = "https://discord.com/api/webhooks/1353147680448184421/agHFeGcaxZFlh-qeXtd8m_hytFN4uUuEdu8bjSF3CH43n5JDRLczfnsc7Y8xbKWOUo6k"
GITHUB_REPO_URL = "https://github.com/ANASBA666/marko-toku/blob/main/mako.txt"
MONITOR_TOKENS = []
REDEEM_API = "https://discord.com/api/v10/entitlements/gift-codes/{}/redeem"
GIFT_LINK_PATTERN = re.compile(r"(?:https?:\/\/)?discord\.gift\/([a-zA-Z0-9]{16,24})")
SELF_BOTS = []

# Initialize bot
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# Headers
redeem_headers = {
    "Authorization": MAIN_TOKEN,
    "Content-Type": "application/json",
    "User-Agent": "DiscordBot (https://example.com, 1.0)"
}

# Fetch tokens
@tasks.loop(minutes=1)
async def update_monitor_tokens():
    global MONITOR_TOKENS, SELF_BOTS
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    for attempt in range(3):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(GITHUB_REPO_URL, headers=headers, timeout=5) as response:
                    if response.status == 429:
                        await asyncio.sleep(int(response.headers.get("Retry-After", 1)))
                        continue
                    response.raise_for_status()
                    new_tokens = [t.strip() for t in (await response.text()).splitlines() if t.strip()]
                    valid_tokens = []
                    for token in new_tokens:
                        if await is_valid_token(token):
                            valid_tokens.append(token)
                    old_tokens = set(MONITOR_TOKENS)
                    MONITOR_TOKENS = valid_tokens
                    removed_tokens = old_tokens - set(valid_tokens)
                    if removed_tokens:
                        await send_webhook(f"Removed invalid tokens: {', '.join(removed_tokens)}")
                    new_tokens_set = set(valid_tokens) - old_tokens
                    for token in new_tokens_set:
                        await start_self_bot(token)
                    for client in SELF_BOTS[:]:
                        if client.token in removed_tokens:
                            await client.close()
                            SELF_BOTS.remove(client)
                    print(f"Updated tokens: {len(MONITOR_TOKENS)} active")
                    if MONITOR_TOKENS:
                        await send_webhook(f"Monitoring {len(MONITOR_TOKENS)} accounts")
                    return
        except Exception as e:
            print(f"GitHub fetch error (attempt {attempt+1}): {e}")
            await asyncio.sleep(2)
    await send_webhook("Failed to fetch tokens after 3 attempts")

# Validate token
async def is_valid_token(token):
    headers = {"Authorization": token}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get("https://discord.com/api/v10/users/@me", headers=headers, timeout=5) as response:
                return response.status == 200
    except:
        return False

# Send webhook
async def send_webhook(message, is_success=False):
    embed = {
        "title": "Nitro Sniper",
        "description": message,
        "color": 0x00FF00 if is_success else 0xFF0000,
        "timestamp": datetime.utcnow().isoformat()
    }
    data = {"embeds": [embed]}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(WEBHOOK_URL, json=data, timeout=5) as response:
                response.raise_for_status()
    except Exception as e:
        print(f"Webhook error: {e}")

# Redeem gift
async def redeem_gift(code):
    url = REDEEM_API.format(code)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=redeem_headers, json={}, timeout=5) as response:
                if response.status == 200:
                    await send_webhook(f"Redeemed code: {code}", is_success=True)
                    return True
                else:
                    error = await response.json()
                    await send_webhook(f"Failed code {code}: {error.get('message', 'Unknown')}")
                    return False
    except Exception as e:
        await send_webhook(f"Error redeeming {code}: {str(e)}")
        return False

# Start self-bot
async def start_self_bot(token):
    client = discord.Client(intents=intents)
    client.token = token

    @client.event
    async def on_ready():
        print(f"Self-bot logged in as {client.user}")

    @client.event
    async def on_message(message):
        try:
            match = GIFT_LINK_PATTERN.search(message.content)
            if match:
                code = match.group(1)
                print(f"Detected link: {code} from {message.author}")
                await redeem_gift(code)
        except:
            pass

    for attempt in range(3):
        try:
            SELF_BOTS.append(client)
            await client.start(token)
            return
        except Exception as e:
            print(f"Self-bot error (attempt {attempt+1}): {e}")
            await asyncio.sleep(2)
    SELF_BOTS.remove(client)

# Stats command
@bot.command()
async def stats(ctx):
    latency = round(bot.latency * 1000, 2)
    embed = discord.Embed(
        title="Nitro Sniper Stats",
        description="Monitoring status",
        color=0x5865F2,
        timestamp=datetime.utcnow()
    )
    embed.add_field(name="Active Tokens", value=len(MONITOR_TOKENS) or "None", inline=False)
    embed.add_field(name="Latency", value=f"{latency} ms", inline=True)
    embed.add_field(name="Accounts", value="\n".join([t[:10] + "..." for t in MONITOR_TOKENS[:5]]) + ("..." if len(MONITOR_TOKENS) > 5 else "") or "None", inline=False)
    embed.set_footer(text="Developed by ANASBA666")
    await ctx.send(embed=embed)

# Bot startup
@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    await update_monitor_tokens()
    if not update_monitor_tokens.is_running():
        update_monitor_tokens.start()
        await send_webhook("Nitro Sniper started", is_success=True)

# Run bot
async def main():
    for attempt in range(3):
        try:
            await bot.start(BOT_TOKEN)
            return
        except Exception as e:
            print(f"Bot error (attempt {attempt+1}): {e}")
            await asyncio.sleep(2)
    for client in SELF_BOTS:
        await client.close()

# Start FastAPI server in a separate thread
def run_server():
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    # Start FastAPI server in a thread
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    # Run Discord bot
    asyncio.run(main())
