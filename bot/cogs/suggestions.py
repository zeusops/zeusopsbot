from typing import Optional

from bot import ZeusBot
from bot.cog import Cog
from discord import Embed, Message
from discord.channel import TextChannel
from discord.ext import commands


class Suggestions(Cog):
    def __init__(self, bot: ZeusBot) -> None:
        super().__init__(bot)
        self.keyword: str = self.config['keyword']
        self.suggestion_ch: Optional[TextChannel] = None
        self.discussion_ch: Optional[TextChannel] = None

    async def init(self):
        self.suggestion_ch = await self.bot.fetch_channel(
            self.config['channels']['suggestions'])
        self.discussion_ch = await self.bot.fetch_channel(
            self.config['channels']['discussion'])

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.channel != self.suggestion_ch or \
                message.author == self.bot.user or \
                message.content[0] == self.bot.command_prefix:
            # We only care about messages that are sent to the suggestion
            # channel, sent by other people and are not commands
            return
        if message.content.startswith(self.keyword):
            await self._handle_suggestion(message)
        else:
            # User posted a random message, not in format
            content = message.content
            await message.delete()
            await message.author.send(
                self.config['message']
                .format(self.suggestion_ch.name, content))

    async def _handle_suggestion(self, message: Message):
        title = message.content.split('\n')[0].replace('*', '')
        embed = Embed(title=title, description="[Link to suggestion]({})"
                                               .format(message.jump_url))
        embed.set_author(name=message.author.display_name)
        discussion_message = await self.discussion_ch.send(embed=embed)
        embed = Embed(description="[Link to discussion]({})"
                                  .format(discussion_message.jump_url))
        await self.suggestion_ch.send(embed=embed)

        for reaction in self.config['reactions'].values():
            await message.add_reaction(reaction)


def setup(bot: ZeusBot):
    bot.add_cog(Suggestions(bot))
