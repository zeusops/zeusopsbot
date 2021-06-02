import traceback

from bot import ZeusBot
from bot.cog import Cog
from discord.ext import commands
from discord.ext.commands import Context, ExtensionNotLoaded
from discord.ext.commands.errors import CheckFailure, CommandError


class Reload(Cog):
    def __init__(self, bot: ZeusBot):
        super().__init__(bot)
        self.extensions = self.bot.config['bot']['extensions']
        self.checks = {
            'reload': self._is_staff,
        }

    @commands.command()
    async def reload(self, ctx: Context):
        print("Reloading extensions")
        self.bot.reload_config()

        unloaded = []
        for extension in self.extensions:
            if await self._unload_extension(ctx, extension):
                unloaded.append(extension)

        loaded = []
        for extension in self.extensions:
            if await self._load_extension(ctx, extension):
                loaded.append(extension)

        if len(loaded) > 0:
            await ctx.send(
                "Reloaded following extensions: {}".format(loaded))
            not_loaded = [item for item in unloaded if item not in loaded]
            if len(not_loaded) > 0:
                await ctx.send("Failed to reload following extensions: {}"
                               .format(not_loaded))
        for cog in self.bot.cogs.values():
            if "init" in dir(cog):
                await cog.init()

    def _is_staff(self, ctx: Context):
        if not self.bot.is_staff(ctx.author):
            raise CheckFailure("Not staff")
        return True

    async def _unload_extension(self, ctx, extension):
        try:
            self.bot.unload_extension(extension)
            print("unloaded", extension)
        except ExtensionNotLoaded:
            await ctx.send("Skipping unload for not loaded extension {}"
                           .format(extension))
            return False
        else:
            return True

    async def _load_extension(self, ctx, extension):
        try:
            self.bot.load_extension(extension)
            print("loaded", extension)
        except Exception:
            await ctx.send("An error occured while reloading: ```{}```"
                           .format(traceback.format_exc()))
            print(traceback.format_exc())
            return False
        else:
            return True

    @reload.error
    async def _command_error(self, ctx: Context, error: CommandError):
        await ctx.send("An error occured: {}".format(error))


def setup(bot):
    bot.add_cog(Reload(bot))
