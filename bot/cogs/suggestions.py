from typing import Optional

from discord import Embed, Message
from discord.channel import TextChannel
from discord.errors import Forbidden
from discord.ext import commands

from bot import ZeusBot
from bot.cog import Cog


class Suggestions(Cog):
    def __init__(self, bot: ZeusBot) -> None:
        super().__init__(bot)
        self.channels: list[dict[str, TextChannel]] = []
        self.reactions: list[str] = self.config['reactions']
        self.keyword: str = self.config['keyword']
        self.image_keyword: str = self.config['image_keyword']
        self.message: str = self.config['message']
        self.thread_message: str = self.config['thread_message']
        self.discussion_channel: bool = self.config['discussion_channel']
        self.use_threads: bool = self.config['use_threads']

    async def init(self):
        await super().init()
        await self._get_channels()
        self._check_channels()

    async def _get_channels(self):
        """Fetch all configured channels"""
        channels: dict[str, Optional[int]]
        for channels in self.config['channels']:
            channel_dict: dict[str, TextChannel] = {}
            for name in ['suggestions', 'discussion']:
                channel_id = channels.get(name, None)
                if channel_id:
                    try:
                        channel = await self.bot.fetch_channel(channel_id)
                        if not isinstance(channel, TextChannel):
                            raise TypeError(f"Channel {name} is not a "
                                            "text channel")
                    except Forbidden as e:
                        raise ValueError(f"Cannot access {name} channel") \
                                from e
                    channel_dict[name] = channel
            self.channels.append(channel_dict)

    def _check_channel(self, channels: dict[str, TextChannel], name: str):
        """Check that specified channel exists and is messageable

        Raises ValueError if either doesn't match"""
        channel = channels.get(name, None)
        if not channel:
            raise ValueError(f"Missing {name} channel")
        member = channel.guild.get_member(self.bot.user.id)
        if not member:
            raise ValueError("Bot's member not found on guild "
                             f"{channel.guild}")
        if not channel.permissions_for(member).send_messages:
            raise ValueError(f"Cannot send messages to {name} channel")

    def _check_channels(self):
        """Check that suggestion (and optional discussion) channels exist and
        are messageable"""
        if not self.channels:
            raise ValueError("No channels configured")
        for guild_ch in self.channels:
            self._check_channel(guild_ch, 'suggestions')

            if self.discussion_channel:
                self._check_channel(guild_ch, 'discussion')

    def _is_correct_channel(self, channel: TextChannel):
        """Check that channel is in the list of channels to listen to"""
        for channels in self.channels:
            if channel == channels['suggestions']:
                return True
        return False

    @commands.Cog.listener()
    async def on_message(self, message: Message):
        # We only care about messages that are sent to the suggestion
        # channels, not sent by bots and are not commands
        if message.author.bot:
            return
        if not isinstance(message.channel, TextChannel):
            return
        command_prefix = tuple(await self.bot.get_prefix(message))
        if (message.content.startswith(command_prefix)
                or not self._is_correct_channel(message.channel)):
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
            if message.type == 18:
                # Message is a new thread. The current library version (v1.7.3)
                # can't handle this properly yet, so using a workaround. It
                # seems that creating a thread to a cached message doesn't
                # trigger this event handler, only threads created to older
                # messages will.
                return
            # Other messages will be deleted after sending a notification
            # to the author
            text = self.message.format(
                message.channel.name, message.content, self.image_keyword)
            if self.use_threads:
                text = f"{text}\n{self.thread_message}"
            await message.author.send(text)
            await message.delete()

    async def _handle_suggestion(self, message: Message):
        if self.discussion_channel:
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

        for reaction in self.reactions:
            await reaction_target.add_reaction(reaction)


def setup(bot: ZeusBot):
    bot.add_cog(Suggestions(bot))
