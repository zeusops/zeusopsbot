from typing import List, Dict

from bot import ZeusBot
from bot.cog import Cog
from discord import Embed, Message
from discord.channel import TextChannel
from discord.errors import Forbidden
from discord.ext import commands


class Suggestions(Cog):
    def __init__(self, bot: ZeusBot) -> None:
        super().__init__(bot)
        self.keyword: str = self.config['keyword']
        self.image_keyword: str = self.config['image_keyword']
        self.channels: List[Dict[str, TextChannel]] = []

    async def init(self):
        await super().init()
        await self._get_channels()
        self._check_channels()

    async def _get_channels(self):
        for channels in self.config['channels']:
            channel_dict = {}
            for name in ['suggestions', 'discussion']:
                if channels.get(name, None):
                    try:
                        channel = await self.bot.fetch_channel(channels[name])
                    except Forbidden as e:
                        raise ValueError(f"Cannot access {name} channel") \
                                from e
                    channel_dict[name] = channel
            self.channels.append(channel_dict)

    def _get_channel(self, channels, name):
        """Check that specified channel exists and is messageable

        Raises ValueError if either doesn't match"""
        channel = channels.get(name, None)
        if not channel:
            raise ValueError(f"Missing {name} channel")
        member = channel.guild.get_member(self.bot.user.id)
        if not channel.permissions_for(member).send_messages:
            raise ValueError(f"Cannot send messages to {name} channel")

    def _check_channels(self):
        for guild_ch in self.channels:
            self._get_channel(guild_ch, 'suggestions')

            if self.config['discussion_channel']:
                self._get_channel(guild_ch, 'discussion')

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
                if self.config['use_threads']:
                    text = f"{text}\n{self.config['thread_message']}"
                await message.author.send(text)
                await message.delete()

    async def _handle_suggestion(self, message: Message):
        if self.config['discussion_channel']:
            channels = [ch for ch in self.channels
                        if message.channel == ch['suggestions']][0]

            title = message.content.split('\n')[0].replace('**', '')
            embed = Embed(title=title, description="[Link to suggestion]({})"
                                                   .format(message.jump_url))
            embed.set_author(name=message.author.display_name)
            discussion_message = await channels['discussions'] \
                .send(embed=embed)

            embed = Embed(description="[Link to discussion]({})"
                                      .format(discussion_message.jump_url))
            suggestion_message = await channels['suggestions'] \
                .send(embed=embed)

            reaction_target = suggestion_message
        else:
            reaction_target = message

        for reaction in self.config['reactions']:
            await reaction_target.add_reaction(reaction)


def setup(bot: ZeusBot):
    bot.add_cog(Suggestions(bot))
