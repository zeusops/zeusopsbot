import pprint
from typing import Dict, List

from bot import ZeusBot
from bot.cog import Cog
from discord import (AuditLogAction, AuditLogEntry, Guild, Message,
                     RawMessageDeleteEvent)
from discord.ext import commands, tasks


class Log(Cog):
    def __init__(self, bot: ZeusBot) -> None:
        self.bot = bot
        print("log init")
        self.log_entries: Dict[int, AuditLogEntry] = {}
        # self.messages: Dict = {}
        self.deleted: List[Message] = []
        self.check_audit_log.start()
        # self.show_message_cache.start()

    async def init(self):
        for name, id in self.config['channels'].values():
            channel = await self.bot.fetch_channel(id)
            self.channels[name] = channel

    # @commands.Cog.listener()
    # async def on_ready(self):
    #     await self.bot.wait_until_ready()
    #     print("cog ready")
    #     time.sleep(5)

    @commands.Cog.listener()
    async def on_message_delete(self, message: Message):
        print("on_message_delete", message, message.content)
        self.deleted.append(message)

    # @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: RawMessageDeleteEvent):
        print("on_raw_message_delete", payload)
        # channel = await self.bot.fetch_channel(payload.channel_id)
        # message = await channel.fetch_message(payload.message_id)
        # print(message)
        # self.deleted.append(payload.message_id)

    # @commands.Cog.listener()
    # async def on_message(self, message: Message):
    #     print("on_message", message, message.content)
    #     self.messages[message.id] = message.content

    # @commands.Cog.listener()
    # async def on_audi
    @tasks.loop(seconds=5.0)
    async def check_audit_log(self):
        print("task")
        # print("log channels", self.channels)
        guild: Guild = self.channels['delete_log'].guild
        entry: AuditLogEntry
        async for entry in guild.audit_logs(
                action=AuditLogAction.message_delete):
            if entry.id not in self.log_entries or \
                    entry.extra.count != self.log_entries[entry.id]['count']:
                # a completely new entry has been added
                if entry.id not in self.log_entries:
                    print("entry not in list")
                    self.log_entries[entry.id] = {'count': 0}
                else:
                    print("counter increased")
                print(entry, entry.extra.count)
                channel = entry.extra.channel
                entry_count = entry.extra.count - \
                    self.log_entries[entry.id]['count']
                if self.deleted:
                    for i in range(entry_count):
                        remove = []
                        for message in reversed(self.deleted):
                            if message.channel == channel and \
                                    message.author == entry.target:
                                print("message by {} deleted in {} by {}: {}"
                                      .format(message.author, message.channel,
                                              entry.user, message.content))
                                remove.append(message)
                            else:
                                print("no match", message)
                        self.deleted = [m for m in self.deleted
                                        if m not in remove]
                self.log_entries[entry.id] = {'entry': entry,
                                              'count': entry.extra.count}
        self.deleted = []

    @tasks.loop(seconds=3.0)
    async def show_message_cache(self):
        print("cache")
        for message in self.bot.cached_messages:
            pprint.pprint({attr: getattr(message, attr, None)
                           for attr in message.__slots__})


def setup(bot: ZeusBot):
    bot.add_cog(Log(bot))
