from typing import Callable, Dict, List, Union

from discord.ext import commands

from bot import ZeusBot


class Cog(commands.Cog):
    def __init__(self, bot: ZeusBot) -> None:
        print("Loading cog {}".format(self.qualified_name))
        self.bot = bot
        name = self.__class__.__name__.lower()
        self.config: Dict = self.bot.config.get('cogs', {}).get(name, {})
        self.checks: Dict[str, Union[Callable, List[Callable]]] = {}

    def _add_checks(self):
        print("Adding checks for {}".format(self.qualified_name))
        for command in self.walk_commands():
            if command.name in self.checks:
                command_checks = self.checks[command.name]
                if not isinstance(command_checks, list):
                    command_checks = [command_checks]
                for check in command_checks:
                    command.add_check(check)
                    print("{}: Adding check {} for command {}"
                          .format(self.qualified_name, check.__name__,
                                  command.qualified_name))

    async def init(self):
        """This method gets called at the end of the bot's `on_ready` block,
        if implemented."""
        print("Cog {} init".format(self.qualified_name))
        self._add_checks()
