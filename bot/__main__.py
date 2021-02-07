import bot
from bot.bot import LogBot

instance = LogBot.create()
# instance.load_extensions()
print(instance.config)
instance.run()
