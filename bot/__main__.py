from bot.bot import LogBot

instance = LogBot.create()
print(instance.config)
instance.run()
