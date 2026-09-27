# im a baisc file

# im going to tickle my cat's foot... tickle tickle! - dashcrikeydash

import aiohttp
from discord import app_commands, Interaction
from discord.ext import commands
from datetime import datetime, timezone
import random
import discord
import json
from cogs.theming import get_fail_colour, get_success_colour

class WelcomeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

        self.add_item(
            discord.ui.Button(
                label="Join the Community",
                emoji="💬",
                url="https://discord.gg/YtQdrkxfg7"
            )
        )

        self.add_item(
            discord.ui.Button(
                label="Legal & Privacy",
                emoji="📄",
                url="https://clanker.pxsl.dev/legal"
            )
        )

@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
class Basic(commands.GroupCog, group_name="basic"):
    def __init__(self, bot):
        self.bot = bot
        self.bot_start_time = datetime.now(timezone.utc)

    group_1 = app_commands.Group(
        name="1",
        description="Basic - page 1",
        allowed_contexts=app_commands.AppCommandContext(guild=True, dm=True, private_channel=True),
        allowed_installs=app_commands.AppInstallationType(guild=True, user=True)
    )

    @group_1.command(
        name="welcome",
        description="show the Clanker welcome message"
    )
    async def welcome(
        self,
        interaction: discord.Interaction
    ):
        embed = discord.Embed(
            title="👋 Thanks for adding Clanker!",
            description=(
                "Thanks for inviting **Clanker** to your server! ❤️\n\n"
                "## 💬 Join the Clanker Community\n"
                "Clanker isn't just a bot - it's a community too!\n\n"
                "Join our Discord to **meet other Clanker users, chat, share memes, "
                "suggest new features, report bugs, get updates, and take part in "
                "community events.**\n\n"
                "We've got **60,000+ users and 100+ servers**, and we'd love to have "
                "you be part of it. ❤️\n\n"
                "## 🔒 Privacy & Legal\n"
                "Want to know what information Clanker stores and how it's used? "
                "You can find our legal and privacy information using the button below.\n\n"
                "**Thanks for choosing Clanker! 🔧**"
            ),
            colour=get_success_colour()
        )

        embed.set_footer(
            text="Made with ❤️ by the Clanker team"
        )

        await interaction.response.send_message(
            embed=embed,
            view=WelcomeView()
        )

    @group_1.command(
        name="hello",
        description="say hello to the bot"
    )
    async def hello(
        self,
        interaction: Interaction
    ):
        hello_responses = [
            f"Hello, {interaction.user.name}!",
            f"Hey there, {interaction.user.name}!",
            f"Hi, {interaction.user.name}! How are you?",
            f"Greetings, {interaction.user.name}!",
            f"What's up, {interaction.user.name}?",
            f"Howdy, {interaction.user.name}!",
            f"Yo, {interaction.user.name}!",
            f"Hiya, {interaction.user.name}!",
            f"Salutations, {interaction.user.name}!",
            f"fuck off! {interaction.user.name}! Thank You :D"
        ]

        embed = discord.Embed(
            title="Hello! 👋",
            description=random.choice(hello_responses),
            color=get_success_colour()
        )

        await interaction.response.send_message(embed=embed)

    @group_1.command(
        name="ping",
        description="get bot's latency"
    )
    async def ping(
        self,
        interaction: Interaction
    ):
        embed = discord.Embed(
            title="Pong! 🏓",
            description=f"Ping: {round(self.bot.latency * 1000)} ms",
            color=get_success_colour()
        )

        await interaction.response.send_message(embed=embed)

    @group_1.command(
        name="uptime",
        description="how long bot been online"
    )
    async def uptime(
        self,
        interaction: Interaction
    ):
        now = datetime.now(timezone.utc)

        uptime_seconds = (
            now - self.bot_start_time
        ).total_seconds()

        days, remainder = divmod(
            uptime_seconds,
            86400
        )

        hours, remainder = divmod(
            remainder,
            3600
        )

        minutes, seconds = divmod(
            remainder,
            60
        )

        uptime_str = (
            f"{int(days)}d "
            f"{int(hours)}h "
            f"{int(minutes)}m "
            f"{int(seconds)}s"
        )

        embed = discord.Embed(
            title="Uptime ⏱️",
            description=(
                f"The bot has been online for: {uptime_str}"
            ),
            color=get_success_colour()
        )

        await interaction.response.send_message(embed=embed)

    @group_1.command(
        name="usercount",
        description="how many users does Clanker serve"
    )
    async def usercount(
        self,
        interaction: Interaction
    ):
        servers = len(self.bot.guilds)

        users = sum(
            g.member_count or 0
            for g in self.bot.guilds
        )

        embed = discord.Embed(
            title="User Count 👤",
            description=(
                f"Clanker serves **{users:,}** users "
                f"across **{servers:,}** servers!"
            ),
            color=get_success_colour()
        )

        await interaction.response.send_message(embed=embed)

    @group_1.command(
        name="cmdcount",
        description="how many commands Clanker has"
    )
    async def cmdcount(
        self,
        interaction: Interaction
    ):
        total = 0
        category_counts = {}

        for cmd in self.bot.tree.walk_commands():
            if isinstance(cmd, app_commands.Group):
                continue

            total += 1

            cog_name = (
                cmd.binding.__class__.__name__
                if getattr(cmd, "binding", None)
                else "No Category"
            )

            if cog_name not in category_counts:
                category_counts[cog_name] = 0

            category_counts[cog_name] += 1

        desc = f"**Total Commands:** {total}\n\n"

        for category, count in category_counts.items():
            desc += f"- **{category}**: {count}\n"

        embed = discord.Embed(
            title="Command Count 🤖",
            description=desc,
            color=get_success_colour()
        )

        await interaction.response.send_message(embed=embed)

    @group_1.command(
        name="version",
        description="see the bot's version"
    )
    async def version(
        self,
        interaction: discord.Interaction
    ):
        with open("data.json", "r") as f:
            data = json.load(f)

        v = data.get("version")

        if not v:
            raise ValueError(
                "Version not found in data.json!"
            )

        embed = discord.Embed(
            title="Version 🏷️",
            description=(
                f"Clanker is currently running v{v}!"
            ),
            color=get_success_colour()
        )

        await interaction.response.send_message(embed=embed)

    @group_1.command(
        name="info",
        description="view information about Clanker"
    )
    async def info(
        self,
        interaction: Interaction
    ):
        with open("data.json", "r") as f:
            data = json.load(f)

        version = data.get(
            "version",
            "Unknown"
        )

        ping = round(
            self.bot.latency * 1000
        )

        users = sum(
            g.member_count or 0
            for g in self.bot.guilds
        )

        servers = len(self.bot.guilds)

        commands = sum(
            1
            for cmd in self.bot.tree.walk_commands()
            if not isinstance(cmd, app_commands.Group)
        )

        embed = discord.Embed(
            title="Info 🤖",
            color=get_success_colour()
        )

        embed.add_field(
            name="🏷️ Version",
            value=f"v{version}",
            inline=True
        )

        embed.add_field(
            name="📡 Ping",
            value=f"{ping} ms",
            inline=True
        )

        embed.add_field(
            name="🤖 Commands",
            value=str(commands),
            inline=True
        )

        embed.add_field(
            name="👤 Users",
            value=f"{users:,}",
            inline=True
        )

        embed.add_field(
            name="🖥️ Servers",
            value=f"{servers:,}",
            inline=True
        )

        await interaction.response.send_message(embed=embed)

    @group_1.command(
        name="vote",
        description="vote for the bot on top.gg"
    )
    async def vote(
        self,
        interaction: discord.Interaction
    ):
        embed = discord.Embed(
            title="Vote for Clanker! 🗳️",
            description=(
                "Help us grow by voting for the bot on top.gg!"
            ),
            color=get_success_colour()
        )

        embed.add_field(
            name="Vote Link",
            value=(
                "[Click here to vote]"
                "(https://top.gg/bot/1482397035909873865/vote)"
            ),
            inline=False
        )

        await interaction.response.send_message(embed=embed)

    @group_1.command(
        name="invite",
        description="get bot invite link"
    )
    async def invite(
        self,
        interaction: discord.Interaction
    ):
        embed = discord.Embed(
            title="Invite Me 🤖",
            description=(
                "[Click here to invite the bot]"
                "(https://clanker.pxsl.dev/invite/)"
            ),
            color=get_success_colour()
        )

        await interaction.response.send_message(embed=embed)

    def get_all_commands(self):
        cmds = []

        for cmd in self.bot.tree.walk_commands():
            if isinstance(cmd, app_commands.Group):
                continue

            cmds.append(cmd)

        return cmds

    @group_1.command(
        name="help",
        description="get help with the bot"
    )
    async def help(
        self,
        interaction: discord.Interaction
    ):
        def is_admin(user_id):
            return (
                user_id in self.bot.data.get("admins", [])
                or
                user_id in self.bot.data.get("owners", [])
            )

        categories = {}
        admin_commands = []

        for cmd in self.get_all_commands():
            cog_name = (
                cmd.binding.__class__.__name__
                if getattr(cmd, "binding", None)
                else "Other"
            )

            if cog_name == "Admin":
                if is_admin(interaction.user.id):
                    admin_commands.append(cmd)

                continue

            categories.setdefault(
                cog_name,
                []
            ).append(cmd)

        if is_admin(interaction.user.id) and admin_commands:
            categories["Admin"] = admin_commands

        pages = []

        for category, cmds in categories.items():
            cmds = sorted(
                cmds,
                key=lambda c: c.name
            )

            chunk_size = 5

            for i in range(
                0,
                len(cmds),
                chunk_size
            ):
                chunk = cmds[
                    i:i + chunk_size
                ]

                description = "\n".join(
                    f"{getattr(cmd, 'mention', f'/{cmd.name}')} "
                    f"- {cmd.description}"
                    for cmd in chunk
                )

                page_num = (
                    i // chunk_size
                ) + 1

                total_pages = (
                    len(cmds) + chunk_size - 1
                ) // chunk_size

                embed = discord.Embed(
                    title=(
                        f"Help - {category} "
                        f"({page_num}/{total_pages})"
                    ),
                    description=description,
                    color=get_success_colour()
                )

                pages.append(embed)

        if not pages:
            pages.append(
                discord.Embed(
                    title="Help",
                    description="No commands found.",
                    color=get_fail_colour()
                )
            )

        class HelpView(discord.ui.View):
            def __init__(self):
                super().__init__(timeout=120)
                self.current = 0

            @discord.ui.button(
                label="◀️",
                style=discord.ButtonStyle.gray
            )
            async def previous(
                self,
                interaction: discord.Interaction,
                button: discord.ui.Button
            ):
                self.current = (
                    self.current - 1
                ) % len(pages)

                await interaction.response.edit_message(
                    embed=pages[self.current],
                    view=self
                )

            @discord.ui.button(
                label="▶️",
                style=discord.ButtonStyle.gray
            )
            async def next(
                self,
                interaction: discord.Interaction,
                button: discord.ui.Button
            ):
                self.current = (
                    self.current + 1
                ) % len(pages)

                await interaction.response.edit_message(
                    embed=pages[self.current],
                    view=self
                )

        view = HelpView()

        await interaction.response.send_message(
            embed=pages[0],
            view=view,
            ephemeral=True
        )

    @group_1.command(
        name="credits",
        description="see the people who somehow made Clanker possible"
    )
    async def credits(
        self,
        interaction: discord.Interaction
    ):
        embed = discord.Embed(
            title="🛠️ the people behind Clanker",
            description=(
                "Clanker didn't magically appear out of nowhere.\n\n"
                "A bunch of absolutely wonderful people have helped build, "
                "test, support, and tolerate this stupid little bot.\n\n"
                "[**view the full credits →**]"
                "(https://clanker.pxsl.dev/credits/)"
            ),
            color=get_success_colour()
        )

        embed.set_footer(
            text="thank you to everyone who helped make Clanker what it is 💜"
        )

        await interaction.response.send_message(embed=embed)

    @group_1.command(
        name="thanks",
        description="support the bot and its developer :)"
    )
    async def thanks(
        self,
        interaction: discord.Interaction
    ):
        embed = discord.Embed(
            title="Thank you so much for wanting to support me 💜",
            description=(
                "Check out the links below:\n"
                "[💬 Join the Discord](https://discord.gg/YtQdrkxfg7)\n"
                "[🌐 Visit the Website](https://clanker.pxsl.dev/)\n"
                "[💜 Support Us](https://pxsl.dev/thanks/)"
            ),
            color=get_success_colour()
        )

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Basic(bot))