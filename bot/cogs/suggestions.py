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
        self.image_keyword: str = self.config['image_keyword']
        self.channels: List[Dict[str, TextChannel]] = []

    async def init(self):
        await super().init()
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

        is_suggestion = False
        is_image = False

        if message.content.startswith(self.keyword):
            is_suggestion = True
        if message.attachments:
            is_image = True
        if len(message.content.split('\n')) > 1:
            # It's quite unlikely that an image has a multiline caption
            is_image = False
        if 'http' in message.content:
            # If the message contains a link, it's not an image. No reason to
            # have links in image captions by default
            is_image = False
        if message.content.startswith(self.image_keyword):
            # Message explicitly marked as image caption
            is_suggestion = False
            is_image = True

        if is_suggestion:
            await self._handle_suggestion(message)
        else:
            # User posted a random message, not in format
            if is_image:
                # Messages with attachments and captions are allowed because
                # the desktop client can't add multiple attachments in a single
                # message
                return
            else:
                # Other messages will be deleted after sending a notification
                # to the author
                text = self.config['message'].format(
                    message.channel.name, message.content, self.image_keyword)
                await message.author.send(text)
                await message.delete()

    async def _handle_suggestion(self, message: Message):
        if self.config['post_links']:
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

            reaction_target = suggestion_message
        else:
            reaction_target = message

        for reaction in self.config['reactions']:
            await reaction_target.add_reaction(reaction)


def setup(bot: ZeusBot):
    bot.add_cog(Suggestions(bot))
