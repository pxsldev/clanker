import discord
import datetime
from discord.ext import commands, tasks

THEMES = {
    "halloween": {
        "success": discord.Color.orange(),
        "fail": discord.Color.purple(),
        "avatar": "assets/halloween/avatar.png",
        "banner": "assets/halloween/banner.png",
        "name": "Spooky Clanker 🎃",
    },

    "fools": {
        "success": discord.Color.yellow(),
        "fail": discord.Color.magenta(),
        "avatar": "assets/fools/avatar.png",
        "banner": "assets/fools/banner.png",
        "name": "clanker uwu :3",
    },

    "christmas": {
        "success": discord.Color.green(),
        "fail": discord.Color.red(),
        "avatar": "assets/christmas/avatar.png",
        "banner": "assets/christmas/banner.png",
        "name": "Merry Clanker🎄",
    },

    "easter": {
        "success": discord.Color.green(),
        "fail": discord.Color.pink(),
        "avatar": "assets/easter/avatar.png",
        "banner": "assets/easter/banner.png",
        "name": "Clanker Bunny 🐰",
    },

    "default": {
        "success": discord.Color.blurple(),
        "fail": discord.Color.red(),
        "avatar": "assets/default/avatar.png",
        "banner": "assets/default/banner.png",
        "name": "Clanker",
    },
}

def get_theme():
    now = datetime.datetime.now(datetime.timezone.utc)

    if now.month == 4 and now.day == 1:
        return "fools"
    elif now.month == 10:
        return "halloween"
    elif now.month == 12:
        return "christmas"
    elif now.month == 3:
        return "easter"

    return "default"

def get_success_colour():
    return THEMES[get_theme()]["success"]

def get_fail_colour():
    return THEMES[get_theme()]["fail"]

def get_avatar():
    return THEMES[get_theme()]["avatar"]

def get_banner():
    return THEMES[get_theme()]["banner"]

def get_name():
    return THEMES[get_theme()]["name"]

class Theming(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_date = None
        self.applied_theme = None
        self.update_theme.start()

    def cog_unload(self):
        self.update_theme.cancel()

    async def apply_theme(self):
        now = datetime.datetime.now(datetime.timezone.utc)
        date = now.date()
        theme = get_theme()

        theme_changed = self.applied_theme != theme

        if self.current_date == date and not theme_changed:
            return

        self.current_date = date

        name = THEMES[theme]["name"]
        avatar_file = THEMES[theme]["avatar"]
        banner_file = THEMES[theme]["banner"]

        if self.bot.user.name != name:
            try:
                await self.bot.user.edit(username=name)
                print(f"[THEMING] Updated name to {name}")
            except discord.HTTPException as e:
                print(f"[THEMING] Failed to update name: {e}")

        if theme_changed:
            try:
                with open(avatar_file, "rb") as f:
                    avatar = f.read()

                await self.bot.user.edit(avatar=avatar)
                print(f"[THEMING] Updated avatar for {theme}")

            except discord.HTTPException as e:
                print(f"[THEMING] Failed to update avatar: {e}")

            try:
                with open(banner_file, "rb") as f:
                    banner = f.read()

                await self.bot.user.edit(banner=banner)
                print(f"[THEMING] Updated banner for {theme}")

            except discord.HTTPException as e:
                print(f"[THEMING] Failed to update banner: {e}")

        self.applied_theme = theme

    @tasks.loop(
        time=datetime.time(
            hour=0,
            minute=0,
            second=0,
            tzinfo=datetime.timezone.utc
        )
    )
    async def update_theme(self):
        await self.apply_theme()

    @update_theme.before_loop
    async def before_update_theme(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    cog = Theming(bot)
    await bot.add_cog(cog)
    await cog.apply_theme()