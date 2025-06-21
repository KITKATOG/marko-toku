import discord
import aiohttp
import asyncio
import re
import logging
from datetime import datetime
from discord.ext import commands, tasks
from typing import List, Set, Optional

# =============================================
# REPLACE THESE VALUES WITH YOUR ACTUAL CREDENTIALS
# =============================================
GITHUB_TOKEN = "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"  # GitHub personal access token
MAIN_TOKEN = "MTIxMDQwMjYwODA3MDc5MTIzMA.GEtAXD.nLsEWxm9IKsmFyiJY3Nlso-zO7F84oZNsRrCxQ"  # For redeeming Nitro
BOT_TOKEN = "MTMzNzQzMjcyMzk0MTM2MzgwNg.G5xdmo.9b5AIimcJBzl0hnzUpi7ZGCCV2JzDhZ4gXssbw"  # Discord bot token
WEBHOOK_URL = "https://discord.com/api/webhooks/1353147680448184421/agHFeGcaxZFlh-qeXtd8m_hytFN4uUuEdu8bjSF3CH43n5JDRLczfnsc7Y8xbKWOUo6k"  # For notifications
GITHUB_REPO_URL = "https://raw.githubusercontent.com/ANASBA666/marko-toku/refs/heads/main/mako.txt?token=GHSAT0AAAAAADFOPWB2HRJDFWTKG2PP7UPG2CW5RSA"  # Raw link to tokens file
# =============================================

# Constants
GIFT_LINK_PATTERNS = [
    re.compile(r"(?:https?:\/\/)?discord\.gift\/([a-zA-Z0-9]{16,24})"),
    re.compile(r"(?:https?:\/\/)?discord\.com\/gifts\/([a-zA-Z0-9]{16,24})"),
    re.compile(r"(?:https?:\/\/)?discordapp\.com\/gifts\/([a-zA-Z0-9]{16,24})")
]
REDEEM_API = "https://discord.com/api/v10/entitlements/gift-codes/{}/redeem"
TOKEN_REFRESH_INTERVAL = 300  # 5 minutes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('nitro_sniper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class NitroSniperBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.monitor_tokens: List[str] = []
        self.used_codes: Set[str] = set()
        self.session: Optional[aiohttp.ClientSession] = None
        self.successful_claims = 0
        self.failed_attempts = 0
        self.start_time = datetime.utcnow()
        self.rate_limiter = asyncio.Semaphore(5)  # 5 concurrent requests max

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        self.update_tokens.start()

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
        await super().close()

    async def redeem_gift(self, code: str) -> bool:
        """Attempt to redeem a Nitro gift code"""
        if code in self.used_codes:
            logger.info(f"Code {code} already attempted, skipping")
            return False

        self.used_codes.add(code)
        
        headers = {
            "Authorization": MAIN_TOKEN,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }

        async with self.rate_limiter:
            try:
                async with self.session.post(
                    REDEEM_API.format(code),
                    headers=headers,
                    json={}
                ) as response:
                    data = await response.json()
                    
                    if response.status == 200:
                        logger.info(f"Successfully claimed Nitro: {code}")
                        self.successful_claims += 1
                        await self.send_webhook(
                            f"✅ Successfully claimed Nitro: `{code}`",
                            color=0x00FF00
                        )
                        return True
                    else:
                        error_msg = data.get('message', 'Unknown error')
                        logger.warning(f"Failed to redeem {code}: {error_msg}")
                        self.failed_attempts += 1
                        await self.send_webhook(
                            f"❌ Failed to redeem `{code}`: {error_msg}",
                            color=0xFF0000
                        )
            except Exception as e:
                logger.error(f"Error redeeming {code}: {str(e)}")
                await self.send_webhook(
                    f"⚠️ Error redeeming `{code}`: {str(e)}",
                    color=0xFFA500
                )
        
        return False

    async def send_webhook(self, message: str, color: int = 0x00FF00):
        """Send message to webhook"""
        embed = {
            "title": "Nitro Sniper Alert",
            "description": message,
            "color": color,
            "timestamp": datetime.utcnow().isoformat(),
            "footer": {
                "text": f"Claims: {self.successful_claims} | Fails: {self.failed_attempts}"
            }
        }

        try:
            async with self.session.post(
                WEBHOOK_URL,
                json={"embeds": [embed]}
            ) as response:
                if response.status == 429:
                    retry_after = float(response.headers.get('Retry-After', 1))
                    await asyncio.sleep(retry_after)
        except Exception as e:
            logger.error(f"Webhook error: {str(e)}")

    async def update_monitor_tokens(self):
        """Update the list of tokens to monitor"""
        headers = {"Authorization": f"token {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}

        try:
            async with self.session.get(GITHUB_REPO_URL, headers=headers) as response:
                if response.status == 200:
                    content = await response.text()
                    new_tokens = [
                        t.strip() for t in content.splitlines() 
                        if t.strip() and len(t.strip()) > 50
                    ]
                    self.monitor_tokens = list(set(new_tokens))
                    logger.info(f"Updated tokens. Now monitoring {len(self.monitor_tokens)} accounts")
                    await self.send_webhook(
                        f"🔄 Monitoring {len(self.monitor_tokens)} accounts",
                        color=0x7289DA
                    )
        except Exception as e:
            logger.error(f"Failed to update tokens: {str(e)}")
            await self.send_webhook(
                f"⚠️ Failed to update tokens: {str(e)}",
                color=0xFF0000
            )

    @tasks.loop(minutes=5)
    async def update_tokens(self):
        """Periodically update the token list"""
        await self.update_monitor_tokens()

    @update_tokens.before_loop
    async def before_update_tokens(self):
        """Wait until bot is ready"""
        await self.wait_until_ready()

    async def on_ready(self):
        """Called when the bot is ready"""
        logger.info(f"Logged in as {self.user} (ID: {self.user.id})")
        await self.send_webhook("🚀 Nitro Sniper bot started", color=0x00FF00)

    async def on_message(self, message: discord.Message):
        """Handle incoming messages"""
        if message.author.bot or message.author == self.user:
            return

        # Check for nitro codes in message
        for pattern in GIFT_LINK_PATTERNS:
            if match := pattern.search(message.content):
                code = match.group(1)
                if len(code) in (16, 24) and code.isalnum():
                    logger.info(f"Detected Nitro code: {code} from {message.author}")
                    await self.send_webhook(
                        f"🔍 Detected Nitro code: `{code}` from {message.author} in {message.guild or 'DM'}",
                        color=0x7289DA
                    )
                    await self.redeem_gift(code)
        
        await self.process_commands(message)

    @commands.command()
    @commands.is_owner()
    async def stats(self, ctx: commands.Context):
        """Show bot statistics"""
        embed = discord.Embed(
            title="Nitro Sniper Stats",
            color=0x00FF00,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Monitored Accounts", value=len(self.monitor_tokens))
        embed.add_field(name="Successful Claims", value=self.successful_claims)
        embed.add_field(name="Failed Attempts", value=self.failed_attempts)
        embed.add_field(name="Latency", value=f"{round(self.latency * 1000, 2)}ms")
        embed.add_field(name="Uptime", value=str(datetime.utcnow() - self.start_time))
        embed.set_footer(text="Advanced Nitro Sniper v2.0")
        
        await ctx.send(embed=embed)

# Initialize and run the bot
intents = discord.Intents.default()
intents.message_content = True

bot = NitroSniperBot(
    command_prefix="!",
    intents=intents,
    help_command=None
)

async def main():
    async with bot:
        await bot.start(BOT_TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
