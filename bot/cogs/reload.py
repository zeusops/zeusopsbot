import traceback

from discord.ext.commands import Bot, Cog, Context, ExtensionNotLoaded, command


class Reload(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot
        self.extensions = self.bot.config['bot']['extensions']

    @command()
    async def reload(self, ctx: Context):
        print("Reloading extensions")

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
            return False
        else:
            return True


def setup(bot):
    bot.add_cog(Reload(bot))