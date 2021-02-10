from typing import Dict, Optional

from bot import ZeusBot
from discord.channel import TextChannel
from discord import Message
from discord.ext import commands


class Pin(commands.Cog):
    def __init__(self, bot: ZeusBot) -> None:
        self.bot = bot
        self.config: Dict = self.bot.config['cogs']['pin']
        self.keyword: str = self.config['keyword']
        self.channel: Optional[TextChannel] = None

    async def init(self):
        self.channel = await self.bot.fetch_channel(self.config['channel'])

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.channel != self.channel:
            # we only care about messages in the suggestion channel
            return
        if self.keyword in message.content:
            await message.pin(reason="Automatic suggestion pin")


def setup(bot: ZeusBot):
    bot.add_cog(Pin(bot))
