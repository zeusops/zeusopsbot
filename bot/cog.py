import logging
from typing import Callable, Union, TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from bot import ZeusBot


class Cog(commands.Cog):
    def __init__(self, bot: 'ZeusBot') -> None:
        self.bot = bot
        name = self.__class__.__name__.lower()
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.logger.info("Loading cog %s", self.qualified_name)
        self.config: dict = self.bot.config.get('cogs', {}).get(name, {})
        self.checks: dict[str, Union[Callable, list[Callable]]] = {}

    def _add_checks(self):
        self.logger.info("Adding checks for %s", self.qualified_name)
        for command in self.walk_commands():
            if command.name in self.checks:
                command_checks = self.checks[command.name]
                if not isinstance(command_checks, list):
                    command_checks = [command_checks]
                for check in command_checks:
                    command.add_check(check)
                    self.logger.info(
                        "%s: Adding check %s for command %s",
                        self.qualified_name,
                        check.__name__,
                        command.qualified_name
                    )

    async def init(self):
        """This method gets called at the end of the bot's `on_ready` block"""
        self.logger.info("Cog %s init", self.qualified_name)
        self._add_checks()
