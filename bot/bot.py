from typing import Dict
import yaml
from discord.ext import commands
from discord import TextChannel


class ZeusBot(commands.Bot):
    def __init__(self, *args, config: Dict, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.channels: Dict[str, TextChannel] = {}
        # self.add_listener(self.on_ready)

    @classmethod
    def create(cls) -> "ZeusBot":
        with open("config.yaml", "r") as f:
            config = yaml.load(f, yaml.SafeLoader)
        try:
            with open("config_local.yaml", "r") as f:
                local_config = yaml.load(f, yaml.SafeLoader)
            for key, value in local_config.items():
                if isinstance(value, dict):
                    for key_, value_ in value.items():
                        config[key][key_] = value_
                else:
                    config[key] = value
        except FileNotFoundError:
            # Local config doesn't exist, continue
            pass
        if 'token' not in config['bot']:
            raise ValueError(
                "Token has to be defined in config.yaml or config_local.yaml")
        return cls(
            command_prefix=config['bot']['prefix'],
            config=config,
        )

    def run(self, *args, **kwargs) -> None:
        super().run(self.config['bot']['token'], *args, **kwargs)

    async def on_ready(self):
        print("waiting until ready")
        await self.wait_until_ready()
        await self._get_channels()
        print("bot channels", self.channels)
        print("ready")
        await self.load_extensions()

    async def _get_channels(self):
        channels = self.config['guild']['channels']
        for channel_name, channel_id in channels.items():
            channel = await self.fetch_channel(channel_id)
            self.channels[channel_name] = channel

    async def load_extensions(self) -> None:
        for extension in self.config['bot']['extensions']:
            self.load_extension(extension)
        for cog in self.cogs.values():
            if "init" in dir(cog):
                await cog.init()
