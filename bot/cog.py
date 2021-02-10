from typing import Dict
from discord.ext import commands

from bot import ZeusBot


class Cog(commands.Cog):
    def __init__(self, bot: ZeusBot) -> None:
        self.bot = bot
        name = self.__class__.__name__.lower()
        self.config: Dict = self.bot.config.get('cogs', {}).get(name, {})

    async def init(self):
        """This method gets called at the end of the bot's `on_ready` block,
        if implemented."""
        pass
