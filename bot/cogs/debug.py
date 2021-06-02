import yaml
from bot import ZeusBot
from bot.cog import Cog
from discord.ext import commands
from discord.ext.commands import Context
from discord.ext.commands.errors import CheckFailure, CommandError


class Debug(Cog):
    def __init__(self, bot: ZeusBot):
        super().__init__(bot)
        self.checks = {
            'configdump': self._is_staff,
            'configreload': self._is_staff,
        }

    async def _dump_config(self, ctx: Context):
        # Replace backticks with \` in order to prevent discord code blocks
        # from breaking
        config = yaml.dump(self.bot.config).replace('`', '\\`')
        config = config.replace(self.bot.config['bot']['token'], "REDACTED")
        await ctx.send("```yaml\n{}```".format(config))

    @commands.command(aliases=['cfgd'])
    async def configdump(self, ctx: Context):
        print("Dumping config")
        await self._dump_config(ctx)

    @commands.command(aliases=['cfgr'])
    async def configreload(self, ctx: Context):
        print("Reloading config")
        self.bot.reload_config()
        await self._dump_config(ctx)

    def _is_staff(self, ctx: Context):
        if not self.bot.is_staff(ctx.author):
            raise CheckFailure("Not staff")
        return True

    @configdump.error
    @configreload.error
    async def _command_error(self, ctx: Context, error: CommandError):
        await ctx.send("An error occured: {}".format(error))


def setup(bot):
    bot.add_cog(Debug(bot))
