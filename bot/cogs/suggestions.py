from typing import List, Dict

from bot import ZeusBot
from bot.cog import Cog
from discord import Embed, Message
from discord.channel import TextChannel
from discord.ext import commands


class Suggestions(Cog):
    def __init__(self, bot: ZeusBot) -> None:
        super().__init__(bot)
        self.keyword: str = self.config['keyword']
        self.channels: List[Dict[str, TextChannel]] = []

    async def init(self):
        for channels in self.config['channels']:
            suggestions = await self.bot.fetch_channel(channels['suggestions'])
            discussion = await self.bot.fetch_channel(channels['discussion'])
            self.channels.append({
                'suggestions': suggestions,
                'discussions': discussion
            })

    def _correct_channel(self, channel: TextChannel):
        for channels in self.channels:
            if channel == channels['suggestions']:
                return True
        return False

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        if message.author.bot or \
                message.content.startswith(self.bot.command_prefix) or \
                not self._correct_channel(message.channel):
            # We only care about messages that are sent to the suggestion
            # channels, not sent by bots and are not commands
            return

        if message.content.startswith(self.keyword):
            await self._handle_suggestion(message)
        else:
            # User posted a random message, not in format
            if not message.attachments:
                # Messages with attachments are allowed because you can't
                # add multiple attachments in a single message, other messages
                # will be deleted with a notification to the author
                await message.author.send(self.config['message']
                                          .format(message.channel.name,
                                                  message.content))
                await message.delete()

    async def _handle_suggestion(self, message: Message):
        channels = [ch for ch in self.channels
                    if message.channel == ch['suggestions']][0]

        title = message.content.split('\n')[0].replace('**', '')
        embed = Embed(title=title, description="[Link to suggestion]({})"
                                               .format(message.jump_url))
        embed.set_author(name=message.author.display_name)
        discussion_message = await channels['discussions'].send(embed=embed)

        embed = Embed(description="[Link to discussion]({})"
                                  .format(discussion_message.jump_url))
        suggestion_message = await channels['suggestions'].send(embed=embed)

        for reaction in self.config['reactions']:
            await suggestion_message.add_reaction(reaction)


def setup(bot: ZeusBot):
    bot.add_cog(Suggestions(bot))
