import os
import subprocess
import json
import re
import traceback
from enum import IntEnum
from typing import Any, Callable, List, Optional

from discord import Message, NotFound
from discord.channel import TextChannel
from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands.converter import MessageConverter
from discord.ext.commands.errors import CommandError
from discord.guild import Guild
from discord.user import User

from bot import ZeusBot
from bot.cog import Cog

STEAM_URL_PATTERN = '(https://steamcommunity.com/' \
                    '.*/filedetails/\\?id=\\d+)'
CATEGORY_OPTIONS = "1, c, co\n2, b, both\n3, s, staff\n4, e, edit"

START = """CO & Staff meeting 2023-mm
===

###### tags: `zeusops` `meeting`

###### date : 2023-mm-dd

[Previous notes](https://www.zeusops.com/meetings)

## Present
### COs
-
### Staff
- Capry
- Gehock
- Matt
- Miller

## Preface

### Notes

### TODO

- Assignee
    - [ ] Todo item 1

"""

CATEGORY = "## Suggestions - {}\n\n"
TITLE = '### {}. {} ({})\n'
VOTES = """
#### Neutral
- name
#### Yes
- name
#### No
- name

#### Notes
- A note

---

"""

FOOTER = """## Community votes

### Votes

![CO](https://cdn.discordapp.com/attachments/582590015054544896/620340512905363466/a.png)
![Mod votes](https://cdn.discordapp.com/attachments/582590015054544896/620340540604547092/a.png)

### Mods

**Terrains** in the default collection:
```diff
+ added
kept
- removed
```

Mod changes to the **default collection**:
```diff
+ added
kept
- removed
```

Mod changes to the **optional collection**:
```diff
+ added
kept
- removed
```

### COs

**COs** this month:
```
MAJ 
CPT 
CPT 
1LT 
1LT 
```
"""  # NOQA


class InvalidReply(Exception):
    pass


class PromptCancelled(Exception):
    pass


class NoChanges(Exception):
    pass


class Type(IntEnum):
    CO = 1
    BOTH = 2
    STAFF = 3
    UNKNOWN = 4


class Suggestion:
    def __init__(self, author: str, title: str, url: str, category: Type,
                 steam_url: Optional[str] = None):
        self.author: str = author
        self.title: str = title
        self.url: str = url
        self.steam_url: Optional[str] = steam_url
        self.category: Type = category
        self.number: Optional[int] = None

    def dump(self):
        return vars(self)

    def __repr__(self):
        return (f"<Suggestion author='{self.author}' title='{self.title}' "
                f"category={self.category}>")

# Suggestion = namedtuple('Suggestion', ['author', 'title', 'url', 'steam_url',
#                                        'category'])


def parse_code_block(text: str):
    if text.startswith('```') and text.endswith('```'):
        rest = text.split('\n')[1:]
        return '\n'.join(rest)[:-3]
    return text


class MeetingNotes(Cog):
    CATEGORY_NAMES = ["CO", "Staff & CO", "Staff", "Unknown"]

    def __init__(self, bot: ZeusBot) -> None:
        super().__init__(bot)
        self.keyword: str = self.config['keyword']
        self.channel: TextChannel = None
        self.suggestions: List[Suggestion] = []
        self.officers: List[Suggestion] = []
        self.both: List[Suggestion] = []
        self.staff: List[Suggestion] = []
        self.unknown: List[Suggestion] = []
        self.categories: List[List[Suggestion]] = []
        self.awaiting_reply = False

    async def init(self):
        await super().init()
        self.channel = await self.bot.fetch_channel(
            self.config['channels']['suggestions'])

    # @bot.check
    # async def await_reply(ctx: Context):
    #     if self.bot.awaiting_reply:
    #         await ctx.send("Please answer the previous prompt first.")
    #         return False
    #     return True

    @commands.command()
    async def create(self, ctx: Context,
                     start_message: MessageConverter = None):
        if start_message is None:
            channel = await self.bot.fetch_channel(360434525798531084)
            print("ch", channel)
            start_message = await channel.fetch_message(817514329326616616)
            print("msg", start_message)
        await ctx.send("Creating")
        count = await self._create(start_message)
        if count > 0:
            await ctx.send("Categories")
            await self._categorize(ctx)
        else:
            await ctx.send("No unknowns")
        await ctx.send("Sorting")
        await self._sort(ctx)
        await ctx.send("Saving")
        await self._save()
        await ctx.send("Done")
        env = os.environ.copy()
        env["GH_TOKEN"] = self.config['gh_token']
        await ctx.send(subprocess.check_output(
            ["gh", "gist", "create", "notes.md"], env=env).decode())

    @commands.command(aliases=['c'])
    async def categorize(self, ctx: Context):
        await self._categorize(ctx)
        await ctx.send("Categories done")

    @commands.command()
    async def sort(self, ctx: Context):
        await self._sort(ctx)
        await ctx.send("Sort done")

    @commands.command(aliases=['s'])
    async def save(self, ctx: Context):
        await self._save()
        await ctx.send("Save done")

    async def _create(self, start_message: Message, limit=100):
        guild: Guild = start_message.guild
        print("guild", guild)
        print("creating")
        message: Message
        async for message in self.channel.history(after=start_message,
                                                  limit=limit):
            text: str = message.clean_content
            if text.startswith(self.keyword):
                author: User = message.author
                if isinstance(author, User):
                    try:
                        author = await guild.fetch_member(author.id)
                    except NotFound:
                        # User is not a member of the guild anymore, default
                        # to the discord username instead of custom nickname
                        pass
                title = text.split('\n')[0].strip('*')
                url = message.jump_url
                if 'https://steamcommunity.com/' in text:
                    match = re.search(STEAM_URL_PATTERN, text)
                    if match:
                        steam_url: Optional[str] = match.group(0)
                    else:
                        print(text)
                        # raise ValueError(f"Didn't match steam URL: {url}")
                else:
                    steam_url = None
                category = Type.CO if steam_url else Type.UNKNOWN
                self.suggestions.append(Suggestion(
                    author.display_name,
                    title,
                    url,
                    category,
                    steam_url,
                ))
        print("suggestions")
        count = sum(1 for s in self.suggestions
                    if s.category == Type.UNKNOWN)
        return count

    async def _categorize(self, ctx: Context):
        if not self.suggestions:
            await ctx.send(f"Suggestions not collected yet. "
                           f"Run `{self.bot.command_prefix}create` first")
            return
        unknowns = [s for s in self.suggestions
                    if s.category == Type.UNKNOWN]
        if unknowns:
            await ctx.send(f"Replies:\n{CATEGORY_OPTIONS}")
            for unknown in unknowns:
                categories = "|".join(CATEGORY_OPTIONS .split('\n'))
                await ctx.send(f"{unknown.author}: {unknown.title}\n"
                               f"{categories}")
                if await self._prompt(ctx, self._parse_category, unknown) \
                        == "edit":
                    await ctx.send("Post correction")
                    await self._prompt(ctx, self._parse_correction, unknown)

        self.officers = [s for s in self.suggestions if s.category == Type.CO]
        self.both = [s for s in self.suggestions if s.category == Type.BOTH]
        self.staff = [s for s in self.suggestions if s.category == Type.STAFF]
        self.unknown = [s for s in self.suggestions
                        if s.category == Type.UNKNOWN]
        self.categories = [self.officers, self.both, self.staff, self.unknown]

        print("after categorize")
        print(self.suggestions)
        await ctx.send("Unknowns done")

    async def _sort(self, ctx: Context):
        while True:
            msg = "Current ordering:\n```\n"
            number = 1
            for collection, name in zip(self.categories, self.CATEGORY_NAMES):
                if collection:
                    msg += CATEGORY.format(name)
                    for entry in collection:
                        msg += TITLE.format(number, entry.title, entry.author)
                        entry.number = number
                        number += 1
                    msg += '\n'
            msg += "```\nReply either with `ok` or send corrected order."
            await ctx.send(msg)
            try:
                await self._prompt(ctx, self._parse_sorting)
            except NoChanges:
                break

    async def _prompt(self, ctx: Context, parser: Callable,
                      data: Any = None, awaitable=False):
        self.awaiting_reply = True

        def pred(m: Message):
            return m.author == ctx.message.author and m.channel == ctx.channel

        # try:
        while True:
            response: Message = await self.bot.wait_for('message',
                                                        check=pred)
            reply = response.clean_content
            try:
                if awaitable:
                    data = await parser(reply, data)
                else:
                    data = parser(reply, data)
            except InvalidReply as e:
                if reply == "cancel":
                    await ctx.send("Cancelled")
                    self.awaiting_reply = False
                    raise PromptCancelled
                await ctx.send(str(e))
            except Exception:
                # Parser returned something unexpected, exiting
                self.awaiting_reply = False
                raise
            else:
                # Parser exited successfully, we're done
                return data
        # except Exception:
        #     await ctx.send(f'```py\n{traceback.format_exc()}\n```')
        #     traceback.print_exc()
        #     self.awaiting_reply = False

        return data

    def _parse_sorting(self, reply: str, _):
        collections = {
            "CO": self.officers,
            "Staff & CO": self.both,
            "Staff": self.staff,
            "Unknown": self.unknown,
        }
        if reply.lower() == "ok" or reply.lower() == "`ok`":
            raise NoChanges
        reply = parse_code_block(reply)
        categories = reply.split('## Suggestions - ')
        if categories[0]:
            raise InvalidReply("Invalid data at the beginning")
        categories = categories[1:]
        for category in categories:
            name, *suggestions = list(
                filter(len, category.strip().split('\n')))
            collection = collections[name]
            tmp = []
            for suggestion in suggestions:
                match = re.match('### (\\d+)\\. (.+) \\((.+)\\)', suggestion)
                if match:
                    number = int(match.group(1))
                    entry = [x for x in collection if x.number == number][0]
                    entry.title = match.group(2)
                    entry.author = match.group(3)
                    tmp.append(entry)
                else:
                    raise InvalidReply("Did not match the format:\n"
                                       f"```\n{suggestion}\n```")
            collection[:] = tmp

    def _parse_category(self, reply: str, suggestion: Suggestion):
        reply = reply.lower()
        if reply in ['1', 'c', 'co']:
            suggestion.category = Type.CO
        elif reply in ['2', 'b', 'both']:
            suggestion.category = Type.BOTH
        elif reply in ['3', 's', 'staff']:
            suggestion.category = Type.STAFF
        elif reply in ['4', 'e', 'edit']:
            return "edit"
        else:
            raise InvalidReply("Invalid reply.")
        return suggestion

    def _parse_correction(self, reply: str, suggestion: Suggestion):
        if ':' not in reply:
            raise InvalidReply("Invalid reply, missing ':'.")
        author, title = reply.split(':', maxsplit=1)
        suggestion.author = author
        suggestion.title = title

    async def _save(self):
        data = {}
        with open('notes.md', 'w') as f:
            f.write(START)
            for collection, name in zip(self.categories, self.CATEGORY_NAMES):
                if collection:
                    data_ = []
                    f.write(CATEGORY.format(name))
                    for entry in collection:
                        f.write(TITLE.format(entry.number, entry.title,
                                             entry.author))
                        f.write(f'- {entry.url}\n')
                        if entry.steam_url:
                            f.write(f'- {entry.steam_url}\n')
                        f.write(VOTES)
                        data_.append(entry.dump())
                    data[name] = data_
            f.write(FOOTER)
        with open('notes.json', 'w') as f:
            json.dump(data, f, indent=4)

    @commands.Cog.listener()
    async def on_command_error(self, ctx: Context, error: CommandError):
        await ctx.send(f"An error occured: {error}")
        # print(''.join(traceback.format_exception(type(error),
        #       error, error.__traceback__)))
        # print(vars(error))
        traceback.print_tb(error.original)
        print(error)


def setup(bot: ZeusBot):
    bot.add_cog(MeetingNotes(bot))
