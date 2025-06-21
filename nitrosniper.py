import discord
from discord.ext import commands, tasks
import aiohttp
import asyncio
from datetime import datetime
import re
from fastapi import FastAPI
import uvicorn
import threading

# Initialize FastAPI
app = FastAPI()

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

# Config
GITHUB_TOKEN = "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"
MAIN_TOKEN = "MTIxMDQwMjYwODA3MDc5MTIzMA.GEtAXD.nLsEWxm9IKsmFyiJY3Nlso-zO7F84oZNsRrCxQ"  # ONLY THIS will be used to redeem
BOT_TOKEN = "MTMzNzQzMjcyMzk0MTM2MzgwNg.G5xdmo.9b5AIimcJBzl0hnzUpi7ZGCCV2JzDhZ4gXssbw"
WEBHOOK_URL = "https://discord.com/api/webhooks/1353147680448184421/agHFeGcaxZFlh-qeXtd8m_hytFN4uUuEdu8bjSF3CH43n5JDRLczfnsc7Y8xbKWOUo6k"
GITHUB_REPO_URL = "https://raw.githubusercontent.com/ANASBA666/marko-toku/refs/heads/main/mako.txt?token=GHSAT0AAAAAADFOPWB2WD25BWTLG4ALPB742CW47UQ"
REDEEM_API = "https://discord.com/api/v10/entitlements/gift-codes/{}/redeem"
GIFT_LINK_PATTERN = re.compile(r"(?:https?:\\/\\/)?discord\\.gift\\/([a-zA-Z0-9]{16,24})")
MONITOR_TOKENS = []

# Discord Bot Init
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

redeem_headers = {
    "Authorization": MAIN_TOKEN,
    "Content-Type": "application/json",
    "User-Agent": "DiscordBot (https://example.com, 1.0)"
}

# Fetch and validate tokens only
@tasks.loop(minutes=2)
async def update_monitor_tokens():
    global MONITOR_TOKENS
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(GITHUB_REPO_URL, headers=headers) as res:
                tokens = [t.strip() for t in (await res.text()).splitlines() if t.strip()]
        valid = []
        for token in tokens:
            if await is_valid_token(token):
                valid.append(token)
            else:
                await send_webhook(f"❌ Invalid token removed: `{token[:10]}...`")
        MONITOR_TOKENS = valid
        await send_webhook(f"✅ Monitoring {len(valid)} valid accounts")
    except Exception as e:
        await send_webhook(f"⚠️ Error updating monitor tokens: {e}")

# Only validate tokens, don't use them
async def is_valid_token(token):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://discord.com/api/v10/users/@me", headers={"Authorization": token}) as r:
                return r.status == 200
    except:
        return False

# Listen to messages for Nitro links
@bot.event
async def on_message(msg):
    if msg.author.bot:
        return
    match = GIFT_LINK_PATTERN.search(msg.content)
    if match:
        code = match.group(1)
        await send_webhook(f"🎁 Found Nitro code: `{code}` from {msg.author}")
        await redeem_gift(code)

# Redeem using MAIN_TOKEN only
async def redeem_gift(code):
    url = REDEEM_API.format(code)
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=redeem_headers, json={}) as r:
                data = await r.json()
                if r.status == 200:
                    await send_webhook(f"✅ Claimed Nitro: `{code}`")
                else:
                    await send_webhook(f"❌ Failed to redeem `{code}`: {data.get('message', 'Unknown')}")
    except Exception as e:
        await send_webhook(f"⚠️ Error redeeming `{code}`: {str(e)}")

# Webhook notifier
async def send_webhook(msg, color=0xFF0000):
    embed = {
        "title": "Nitro Sniper",
        "description": msg,
        "color": color,
        "timestamp": datetime.utcnow().isoformat()
    }
    try:
        async with aiohttp.ClientSession() as s:
            await s.post(WEBHOOK_URL, json={"embeds": [embed]})
    except:
        pass

@bot.command()
async def stats(ctx):
    latency = round(bot.latency * 1000, 2)
    embed = discord.Embed(title="Nitro Sniper Stats", color=0x00ffcc, timestamp=datetime.utcnow())
    embed.add_field(name="Monitored Accounts", value=len(MONITOR_TOKENS))
    embed.add_field(name="Latency", value=f"{latency}ms")
    embed.set_footer(text="Made by ANAS")
    await ctx.send(embed=embed)

@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    if not update_monitor_tokens.is_running():
        update_monitor_tokens.start()
    await send_webhook("✅ Nitro Sniper bot started.", color=0x00FF00)

# Start bot
async def main():
    try:
        await bot.start(BOT_TOKEN)
    except Exception as e:
        print("Startup error:", e)

# Run FastAPI in thread
threading.Thread(target=lambda: uvicorn.run(app, host="0.0.0.0", port=8000), daemon=True).start()
asyncio.run(main())
