from typing import Dict, Union

import yaml
from discord import Member, TextChannel
from discord.abc import User
from discord.ext import commands


def _merge(a, b, path=None, update=True):
    """merges b into a
    http://stackoverflow.com/questions/7204805/python-dictionaries-of-dictionaries-merge
    https://stackoverflow.com/a/25270947/3005969"""
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                _merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            elif isinstance(a[key], list) and isinstance(b[key], list):
                for idx, _ in enumerate(b[key]):
                    a[key][idx] = _merge(a[key][idx], b[key][idx],
                                         path + [str(key), str(idx)],
                                         update=update)
            elif update:
                a[key] = b[key]
            else:
                raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
        else:
            a[key] = b[key]
    return a


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
            config = _merge(config, local_config)
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
        print(f"Logged in as {self.user.name}#{self.user.discriminator}")
        print("Connected")
        await self.load_extensions()
        print("Extensions loaded")

    async def load_extensions(self) -> None:
        for extension in self.config['bot']['extensions']:
            self.load_extension(extension)
        for cog in self.cogs.values():
            if "init" in dir(cog):
                await cog.init()
