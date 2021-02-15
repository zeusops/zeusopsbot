from typing import Dict, Union

import yaml
from discord import Member, TextChannel
from discord.abc import User
from discord.ext import commands


class ZeusBot(commands.Bot):
    def __init__(self, *args, config: Dict, **kwargs):
        super().__init__(*args, **kwargs)
        self.config = config
        self.channels: Dict[str, TextChannel] = {}
        self.staff_role = self.config['guild']['roles']['staff']

    def is_admin(self, user: Union[User, Member]):
        return user.id in self.config['bot']['admins']

    def is_staff(self, user: Union[User, Member]) -> bool:
        """Returns true if the member has a staff role defined in the config

        Currently this only checks a single role, doesn't take multiple guilds
        into account."""

        if self.is_admin(user):
            # Admin is considered staff across all guilds
            return True
        try:
            for role in user.roles:
                if role.id == self.staff_role or role.name == self.staff_role:
                    return True
        except AttributeError:
            # Most likely got passed a User from a DM -> never staff
            pass
        return False

    @classmethod
    def _load_config(cls) -> Dict:
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
        return config

    @classmethod
    def create(cls) -> "ZeusBot":
        config = cls._load_config()
        return cls(
            command_prefix=config['bot']['prefix'],
            config=config,
        )

    def run(self, *args, **kwargs) -> None:
        super().run(self.config['bot']['token'], *args, **kwargs)

    def reload_config(self):
        self.config = self._load_config()

    async def on_ready(self):
        print("Waiting until ready")
        await self.wait_until_ready()
        print("Connected")
        await self.load_extensions()
        print("Extensions loaded")

    async def load_extensions(self) -> None:
        for extension in self.config['bot']['extensions']:
            self.load_extension(extension)
        for cog in self.cogs.values():
            if "init" in dir(cog):
                await cog.init()
