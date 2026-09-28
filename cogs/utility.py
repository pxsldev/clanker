# im a utilitlituy file!

from discord import app_commands, Interaction
from discord.ext import commands
import discord
import aiohttp
import random
import qrcode
import io
import asyncio
import re
import json
import urllib.parse
import socket
import whois
from datetime import datetime, timezone
from mathparse import mathparse
from cogs.theming import get_fail_colour, get_success_colour
from dateutil.easter import easter

class Utility(commands.GroupCog, group_name="utility"):
    def __init__(self, bot):
        self.bot = bot

    def parse_time(self, time_str: str) -> int:
        matches = re.findall(r"(\d+)([smhdw])", time_str.lower())

        if not matches:
            return -1

        multipliers = {
            "s": 1,
            "m": 60,
            "h": 3600,
            "d": 86400,
            "w": 604800
        }

        total_seconds = 0

        for value, unit in matches:
            total_seconds += int(value) * multipliers[unit]

        return total_seconds if total_seconds > 0 else -1

    group_1 = app_commands.Group(
        name="1",
        description="Utility - page 1"
    )

    @group_1.command(
        name="dadjoke",
        description="random dad joke very funny haha"
    )
    async def dadjoke(self, interaction: Interaction):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://icanhazdadjoke.com/",
                headers={"Accept": "application/json"}
            ) as resp:
                data = await resp.json()

        embed = discord.Embed(
            title="Dad Joke 😂",
            description=data["joke"],
            color=get_success_colour()
        )

        await interaction.response.send_message(embed=embed)

    @group_1.command(
        name="dog",
        description="i like dog"
    )
    async def dog(self, interaction: Interaction):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://dog.ceo/api/breeds/image/random"
            ) as resp:
                data = await resp.json()

        embed = discord.Embed(
            title="Random Dog 🐶",
            color=get_success_colour()
        )

        embed.set_image(url=data["message"])

        await interaction.response.send_message(embed=embed)

    @group_1.command(
        name="cat",
        description="i like cat"
    )
    async def cat(self, interaction: Interaction):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.thecatapi.com/v1/images/search"
            ) as resp:
                data = await resp.json()

        embed = discord.Embed(
            title="🐱 Random Cat",
            color=get_success_colour()
        )

        embed.set_image(url=data[0]["url"])

        await interaction.response.send_message(embed=embed)

    @group_1.command(
        name="duck",
        description="i like duck"
    )
    async def duck(self, interaction: Interaction):
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://random-d.uk/api/v2/random"
            ) as resp:
                data = await resp.json()

        embed = discord.Embed(
            title="🦆 Random Duck",
            color=get_success_colour()
        )

        embed.set_image(url=data["url"])

        await interaction.response.send_message(embed=embed)

    @group_1.command(
        name="oliver",
        description="get a random picture of dashcrikeydash's cat"
    )
    async def oliver(self, interaction: Interaction):
        json_url = "https://dashcrikeydash.github.io/images.json"
        base_url = "https://dashcrikeydash.github.io/"

        async with aiohttp.ClientSession() as session:
            async with session.get(json_url) as resp:
                if resp.status != 200:
                    return await interaction.response.send_message(
                        "Failed to fetch cat images ❌",
                        ephemeral=True
                    )

                text = await resp.text()

        lines = text.splitlines()

        valid_lines = [
            line.strip().strip('",')
            for line in lines
            if line.strip() not in ["[", "]"] and line.strip()
        ]

        if not valid_lines:
            return await interaction.response.send_message(
                "No cat images found ❌",
                ephemeral=True
            )

        random_image = random.choice(valid_lines)
        final_url = base_url + random_image

        embed = discord.Embed(
            title="Random Oliver Image 🐱",
            color=get_success_colour()
        )

        embed.set_image(url=final_url)

        await interaction.response.send_message(embed=embed)

    @group_1.command(
        name="password",
        description="get an actually good password"
    )
    @app_commands.describe(
        length="Length of the password (4-100)"
    )
    async def password(
        self,
        interaction: Interaction,
        length: int = 12
    ):
        if length < 4 or length > 100:
            embed = discord.Embed(
                title="Invalid Length ❌",
                description=(
                    "Password length must be between "
                    "4 and 100 characters."
                ),
                color=get_fail_colour()
            )

            return await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

        chars = (
            "abcdefghijklmnopqrstuvwxyz"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "0123456789"
            "!@#$%^&*()-_=+[]{}|;:,.<>?/~`"
        )

        password = "".join(
            random.choice(chars)
            for _ in range(length)
        )

        embed = discord.Embed(
            title="🔐 Generated Password",
            description=f"```\n{password}\n```",
            color=get_success_colour()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

    @group_1.command(
        name="qr",
        description="generate a qr code for a url"
    )
    @app_commands.describe(
        url="url to qr code-ify"
    )
    async def qr(
        self,
        interaction: Interaction,
        url: str
    ):
        qr_img = qrcode.make(url)
        buffer = io.BytesIO()

        qr_img.save(buffer, format="PNG")
        buffer.seek(0)

        embed = discord.Embed(
            title="📱 QR Code",
            description=f"QR code for: `{url}`",
            color=get_success_colour()
        )

        file = discord.File(
            fp=buffer,
            filename="qr.png"
        )

        embed.set_image(
            url="attachment://qr.png"
        )

        await interaction.response.send_message(
            embed=embed,
            file=file
        )

    @group_1.command(
        name="remindme",
        description="set a reminder (10m, 2h, 1d, etc)"
    )
    @app_commands.describe(
        time="time like 10s, 5m, 2h, 1d, 1w",
        message="what should I remind you about"
    )
    async def remindme(
        self,
        interaction: Interaction,
        time: str,
        message: str
    ):
        seconds = self.parse_time(time)

        if seconds <= 0:
            return await interaction.response.send_message(
                "❌ Invalid time format. Use `10s`, `5m`, `2h`, `1d`, `1w`.",
                ephemeral=True
            )

        if seconds > 604800:
            return await interaction.response.send_message(
                "❌ Max reminder time is 1 week.",
                ephemeral=True
            )

        embed = discord.Embed(
            title="⏰ Reminder Set!",
            description=message,
            color=get_success_colour()
        )

        await interaction.response.send_message(
            embed=embed,
            ephemeral=True
        )

        await asyncio.sleep(seconds)

        embed = discord.Embed(
            title="⏰ Reminder",
            description=message,
            color=get_success_colour()
        )

        try:
            await interaction.user.send(embed=embed)
        except:
            if interaction.channel:
                await interaction.channel.send(
                    content=interaction.user.mention,
                    embed=embed
                )

    @group_1.command(
        name="forgetme",
        description="Export your Clanker data and delete everything (GDPR wipe)"
    )
    @app_commands.guild_only()
    async def forgetme(
        self,
        interaction: Interaction
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            guild_id = interaction.guild.id
            user_id = interaction.user.id

            self.cursor.execute(
                """
                SELECT * FROM users
                WHERE guild_id=? AND user_id=?
                """,
                (guild_id, user_id)
            )

            row = self.cursor.fetchone()

            if not row:
                return await interaction.followup.send(
                    embed=discord.Embed(
                        title="Nothing to delete",
                        description="You have no stored Clanker data.",
                        color=get_success_colour()
                    ),
                    ephemeral=True
                )

            user_data = self.user_dict(row)

            json_bytes = io.BytesIO(
                json.dumps(
                    user_data,
                    indent=4
                ).encode("utf-8")
            )

            file = discord.File(
                json_bytes,
                filename="clanker_data_export.json"
            )

            self.cursor.execute(
                """
                DELETE FROM users
                WHERE guild_id=? AND user_id=?
                """,
                (guild_id, user_id)
            )

            self.db.commit()

            embed = discord.Embed(
                title="🧨 Data Wiped",
                description=(
                    "Your Clanker data has been exported and deleted.\n"
                    "You are gone from the system."
                ),
                color=get_fail_colour()
            )

            await interaction.followup.send(
                embed=embed,
                file=file,
                ephemeral=True
            )

        except Exception as e:
            print("FORGETME ERROR:", e)

            await interaction.followup.send(
                embed=discord.Embed(
                    title="❌ Error",
                    description=(
                        "Something went wrong while "
                        "deleting your data."
                    ),
                    color=get_fail_colour()
                ),
                ephemeral=True
            )

    @group_1.command(
        name="steam",
        description="get info on a steam game"
    )
    @app_commands.describe(
        game="steam game name"
    )
    async def steam(
        self,
        interaction: Interaction,
        game: str
    ):
        await interaction.response.defer()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://store.steampowered.com/api/storesearch/",
                    params={
                        "term": game,
                        "cc": "gb",
                        "l": "english"
                    }
                ) as resp:
                    if resp.status != 200:
                        embed = discord.Embed(
                            title="❌ Steam API Error",
                            description=(
                                "Steam failed to return search results.\n\n"
                                "Please try again later."
                            ),
                            color=get_fail_colour()
                        )

                        return await interaction.followup.send(
                            embed=embed,
                            ephemeral=True
                        )

                    search_data = await resp.json()

                items = search_data.get("items", [])

                if not items:
                    embed = discord.Embed(
                        title="❌ Game Not Found",
                        description=(
                            f"I couldn't find a Steam game matching "
                            f"`{game}`."
                        ),
                        color=get_fail_colour()
                    )

                    return await interaction.followup.send(
                        embed=embed,
                        ephemeral=True
                    )

                def normalize(name):
                    name = name.lower()

                    name = re.sub(
                        r"[™®©]",
                        "",
                        name
                    )

                    name = re.sub(
                        r"[^a-z0-9\s]",
                        "",
                        name
                    )

                    name = re.sub(
                        r"\s+",
                        " ",
                        name
                    ).strip()

                    return name

                requested = normalize(game)
                exact_match = None

                for item in items:
                    item_name = item.get("name", "")

                    if normalize(item_name) == requested:
                        exact_match = item
                        break

                if exact_match is None:
                    embed = discord.Embed(
                        title="❌ Game Not Found",
                        description=(
                            f"I couldn't find an exact Steam game "
                            f"called `{game}`."
                        ),
                        color=get_fail_colour()
                    )

                    return await interaction.followup.send(
                        embed=embed,
                        ephemeral=True
                    )

                app_id = exact_match["id"]

                async with session.get(
                    "https://store.steampowered.com/api/appdetails",
                    params={
                        "appids": app_id,
                        "cc": "gb",
                        "l": "english"
                    }
                ) as resp:
                    if resp.status != 200:
                        embed = discord.Embed(
                            title="❌ Steam API Error",
                            description=(
                                "Steam found the game, but I couldn't "
                                "retrieve its information."
                            ),
                            color=get_fail_colour()
                        )

                        return await interaction.followup.send(
                            embed=embed,
                            ephemeral=True
                        )

                    details_response = await resp.json()

                app_data = details_response.get(
                    str(app_id),
                    {}
                )

                if not app_data.get("success"):
                    embed = discord.Embed(
                        title="❌ Game Information Unavailable",
                        description=(
                            "Steam found the game, but its information "
                            "is currently unavailable."
                        ),
                        color=get_fail_colour()
                    )

                    return await interaction.followup.send(
                        embed=embed,
                        ephemeral=True
                    )

                game_data = app_data["data"]

                embed = discord.Embed(
                    title=f"🎮 {game_data.get('name', game)}",
                    description=game_data.get(
                        "short_description",
                        "No description available."
                    ),
                    url=f"https://store.steampowered.com/app/{app_id}",
                    color=get_success_colour()
                )

                if game_data.get("header_image"):
                    embed.set_image(
                        url=game_data["header_image"]
                    )

                price = game_data.get("price_overview")

                if price:
                    embed.add_field(
                        name="💰 Price",
                        value=price.get(
                            "final_formatted",
                            "Unknown"
                        ),
                        inline=True
                    )

                elif game_data.get("is_free"):
                    embed.add_field(
                        name="💰 Price",
                        value="Free",
                        inline=True
                    )

                developers = game_data.get("developers", [])

                if developers:
                    embed.add_field(
                        name="👨‍💻 Developer",
                        value=", ".join(developers),
                        inline=True
                    )

                publishers = game_data.get("publishers", [])

                if publishers:
                    embed.add_field(
                        name="🏢 Publisher",
                        value=", ".join(publishers),
                        inline=True
                    )

                release_date = game_data.get("release_date", {})

                if release_date.get("date"):
                    embed.add_field(
                        name="📅 Release Date",
                        value=release_date["date"],
                        inline=True
                    )

                genres = game_data.get("genres", [])

                if genres:
                    genre_names = [
                        genre["description"]
                        for genre in genres
                        if genre.get("description")
                    ]

                    if genre_names:
                        embed.add_field(
                            name="🎯 Genres",
                            value=", ".join(genre_names),
                            inline=True
                        )

                embed.set_footer(
                    text=f"Steam App ID: {app_id}"
                )

                await interaction.followup.send(
                    embed=embed
                )

        except aiohttp.ClientError:
            embed = discord.Embed(
                title="❌ Connection Error",
                description=(
                    "I couldn't connect to Steam.\n\n"
                    "Please try again later."
                ),
                color=get_fail_colour()
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

        except Exception as e:
            print("STEAM COMMAND ERROR:", e)

            embed = discord.Embed(
                title="❌ Unexpected Error",
                description=(
                    "Something went wrong while getting "
                    "the Steam game information."
                ),
                color=get_fail_colour()
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

    @group_1.command(
        name="github",
        description="View a GitHub profile"
    )
    @app_commands.describe(
        username="The GitHub username to look up"
    )
    async def github(
        self,
        interaction: Interaction,
        username: str
    ):
        await interaction.response.defer()

        url = f"https://api.popcat.xyz/v2/github/{username}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        await interaction.followup.send(
                            "❌ Couldn't find that GitHub profile."
                        )
                        return

                    data = await response.json()

            if data.get("error"):
                await interaction.followup.send(
                    "❌ Couldn't find that GitHub profile."
                )
                return

            profile = data["message"]

            embed = discord.Embed(
                title=f"GitHub - {profile['name']}",
                url=profile["url"],
                description=profile["bio"],
                color=get_success_colour()
            )

            embed.set_thumbnail(url=profile["avatar"])

            embed.add_field(
                name="📦 Repositories",
                value=profile["public_repos"],
                inline=True
            )

            embed.add_field(
                name="👥 Followers",
                value=profile["followers"],
                inline=True
            )

            embed.add_field(
                name="➡️ Following",
                value=profile["following"],
                inline=True
            )

            embed.add_field(
                name="📝 Gists",
                value=profile["public_gists"],
                inline=True
            )

            embed.add_field(
                name="🏢 Company",
                value=profile["company"],
                inline=True
            )

            embed.add_field(
                name="📍 Location",
                value=profile["location"],
                inline=True
            )

            embed.add_field(
                name="🌐 Website",
                value=profile["blog"] if profile["blog"] != "None" else "None",
                inline=False
            )

            embed.set_footer(
                text=f"GitHub account created {profile['created_at'][:10]}"
            )

            await interaction.followup.send(embed=embed)

        except Exception:
            await interaction.followup.send(
                "❌ Something went wrong while fetching that GitHub profile."
            )

    @group_1.command(
        name="imdb",
        description="Look up a movie or TV show on IMDb"
    )
    @app_commands.describe(
        query="The movie or TV show to search for"
    )
    async def imdb(
        self,
        interaction: Interaction,
        query: str
    ):
        await interaction.response.defer()

        url = "https://api.popcat.xyz/v2/imdb"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params={"q": query}
                ) as response:
                    if response.status != 200:
                        await interaction.followup.send(
                            "❌ Couldn't find anything for that search."
                        )
                        return

                    data = await response.json()

            if data.get("error"):
                await interaction.followup.send(
                    "❌ Couldn't find anything for that search."
                )
                return

            movie = data["message"]

            embed = discord.Embed(
                title=f"{movie['title']} ({movie['year']})",
                url=movie["imdburl"],
                description=movie["plot"],
                color=get_success_colour()
            )

            if movie.get("poster") and movie["poster"] != "N/A":
                embed.set_thumbnail(url=movie["poster"])

            embed.add_field(
                name="⭐ IMDb",
                value=f"{movie['rating']}/10 ({movie['votes']} votes)",
                inline=True
            )

            embed.add_field(
                name="🎬 Runtime",
                value=movie["runtime"],
                inline=True
            )

            embed.add_field(
                name="🔞 Rated",
                value=movie["rated"],
                inline=True
            )

            embed.add_field(
                name="🎭 Genres",
                value=movie["genres"],
                inline=False
            )

            embed.add_field(
                name="🎥 Director",
                value=movie["director"],
                inline=True
            )

            embed.add_field(
                name="✍️ Writer",
                value=movie["writer"],
                inline=True
            )

            embed.add_field(
                name="👥 Actors",
                value=movie["actors"],
                inline=False
            )

            embed.add_field(
                name="🌍 Country",
                value=movie["country"],
                inline=True
            )

            embed.add_field(
                name="🗣️ Languages",
                value=movie["languages"],
                inline=True
            )

            embed.add_field(
                name="🏆 Awards",
                value=movie["awards"],
                inline=False
            )

            embed.add_field(
                name="💰 Box Office",
                value=movie["boxoffice"],
                inline=True
            )

            if movie.get("metascore") and movie["metascore"] != "N/A":
                embed.add_field(
                    name="📊 Metascore",
                    value=f"{movie['metascore']}/100",
                    inline=True
                )

            ratings = movie.get("ratings", [])

            if ratings:
                rating_text = "\n".join(
                    f"**{rating['source']}:** {rating['value']}"
                    for rating in ratings
                )

                embed.add_field(
                    name="📈 Ratings",
                    value=rating_text,
                    inline=False
                )

            embed.set_footer(
                text=f"IMDb ID: {movie['imdbid']}"
            )

            await interaction.followup.send(embed=embed)

        except Exception:
            await interaction.followup.send(
                "❌ Something went wrong while looking that up."
            )

    @group_1.command(
        name="itunes",
        description="Search for a song on iTunes"
    )
    @app_commands.describe(
        query="The song to search for"
    )
    async def itunes(
        self,
        interaction: Interaction,
        query: str
    ):
        await interaction.response.defer()

        url = "https://api.popcat.xyz/v2/itunes"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params={"q": query}
                ) as response:
                    if response.status != 200:
                        await interaction.followup.send(
                            "❌ Couldn't find anything for that search."
                        )
                        return

                    data = await response.json()

            if data.get("error"):
                await interaction.followup.send(
                    "❌ Couldn't find anything for that search."
                )
                return

            song = data["message"]

            embed = discord.Embed(
                title=song["name"],
                url=song["url"],
                color=get_success_colour()
            )

            embed.set_author(
                name=song["artist"]
            )

            if song.get("thumbnail"):
                embed.set_thumbnail(url=song["thumbnail"])

            embed.add_field(
                name="🎤 Artist",
                value=song["artist"],
                inline=True
            )

            embed.add_field(
                name="💿 Album",
                value=song["album"],
                inline=True
            )

            embed.add_field(
                name="🎮 Genre",
                value=song["genre"],
                inline=True
            )

            embed.add_field(
                name="📅 Released",
                value=song["release_date"],
                inline=True
            )

            embed.add_field(
                name="⏱️ Length",
                value=song["length"],
                inline=True
            )

            embed.add_field(
                name="💰 Price",
                value=song["price"],
                inline=True
            )

            embed.set_footer(
                text="Apple Music / iTunes"
            )

            await interaction.followup.send(embed=embed)

        except Exception:
            await interaction.followup.send(
                "❌ Something went wrong while searching iTunes."
            )

    @group_1.command(
        name="npm",
        description="Look up an NPM package"
    )
    @app_commands.describe(
        query="The NPM package to look up"
    )
    async def npm(
        self,
        interaction: Interaction,
        query: str
    ):
        await interaction.response.defer()

        url = "https://api.popcat.xyz/v2/npm"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params={"q": query}
                ) as response:
                    if response.status != 200:
                        await interaction.followup.send(
                            "❌ Couldn't find that NPM package."
                        )
                        return

                    data = await response.json()

            if data.get("error"):
                await interaction.followup.send(
                    "❌ Couldn't find that NPM package."
                )
                return

            package = data["message"]

            embed = discord.Embed(
                title=package["name"],
                description=package["description"],
                color=get_fail_colour()
            )

            embed.add_field(
                name="📦 Version",
                value=package["version"],
                inline=True
            )

            embed.add_field(
                name="👤 Author",
                value=package["author"],
                inline=True
            )

            embed.add_field(
                name="📥 Downloads",
                value=f"{package['downloads_this_year']} this year",
                inline=True
            )

            embed.add_field(
                name="📅 Last Published",
                value=package["last_published"],
                inline=True
            )

            embed.add_field(
                name="👥 Maintainers",
                value=package["maintainers"],
                inline=True
            )

            embed.add_field(
                name="🔑 Keywords",
                value=package["keywords"] or "None",
                inline=False
            )

            if package.get("author_email") and package["author_email"] != "None":
                embed.add_field(
                    name="📧 Author Email",
                    value=package["author_email"],
                    inline=False
                )

            if package.get("repository") and package["repository"] != "None":
                embed.add_field(
                    name="🔗 Repository",
                    value=package["repository"],
                    inline=False
                )

            embed.set_footer(
                text="NPM Package"
            )

            await interaction.followup.send(embed=embed)

        except Exception:
            await interaction.followup.send(
                "❌ Something went wrong while looking up that NPM package."
            )

    @group_1.command(
        name="weather",
        description="Check the weather for a place"
    )
    @app_commands.describe(
        place="The place to check"
    )
    async def weather(
        self,
        interaction: Interaction,
        place: str
    ):
        await interaction.response.defer()

        url = "https://api.popcat.xyz/v2/weather"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    params={"q": place}
                ) as response:
                    if response.status != 200:
                        await interaction.followup.send(
                            "❌ Couldn't find that location."
                        )
                        return

                    data = await response.json()

            if data.get("error") or not data.get("message"):
                await interaction.followup.send(
                    "❌ Couldn't find that location."
                )
                return

            result = data["message"][0]
            location = result["location"]
            current = result["current"]
            forecast = result["forecast"]

            embed = discord.Embed(
                title=f"Weather for {location['name']}",
                description=f"**{current['skytext']}**",
                color=get_success_colour()
            )

            if current.get("imageUrl"):
                embed.set_thumbnail(url=current["imageUrl"])

            embed.add_field(
                name="🌡️ Temperature",
                value=f"{current['temperature']}°{location['degreetype']}",
                inline=True
            )

            embed.add_field(
                name="🌡️ Feels Like",
                value=f"{current['feelslike']}°{location['degreetype']}",
                inline=True
            )

            embed.add_field(
                name="💧 Humidity",
                value=f"{current['humidity']}%",
                inline=True
            )

            embed.add_field(
                name="💨 Wind",
                value=current["winddisplay"],
                inline=True
            )

            embed.add_field(
                name="📍 Location",
                value=current["observationpoint"],
                inline=True
            )

            embed.add_field(
                name="🕐 Updated",
                value=current["observationtime"],
                inline=True
            )

            forecast_text = []

            for day in forecast:
                forecast_text.append(
                    f"**{day['shortday']}** — "
                    f"{day['skytextday']} • "
                    f"{day['low']}°/{day['high']}° • "
                    f"🌧️ {day['precip']}%"
                )

            embed.add_field(
                name="📅 5-Day Forecast",
                value="\n".join(forecast_text),
                inline=False
            )

            embed.set_footer(
                text="Weather data provided by MSN Weather"
            )

            await interaction.followup.send(embed=embed)

        except Exception:
            await interaction.followup.send(
                "❌ Something went wrong while getting the weather."
            )

    @group_1.command(
        name="translate",
        description="Translate text to another language"
    )
    @app_commands.describe(
        text="Text to translate",
        target="Target language code (e.g. es, fr, de, ja)",
        source="Source language (auto-detect if omitted)"
    )
    async def translate(
        self,
        interaction: Interaction,
        text: str,
        target: str = "en",
        source: str = "auto"
    ):
        await interaction.response.defer()

        try:
            url = (
                "https://api.mymemory.translated.net/get"
                f"?q={urllib.parse.quote(text[:500])}"
                f"&langpair={source}|{target}"
            )

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        await interaction.followup.send(
                            embed=self.embed(
                                "Error",
                                "Translation API unavailable.",
                                True
                            )
                        )
                        return

                    data = await resp.json()

            translated = data.get(
                "responseData",
                {}
            ).get(
                "translatedText",
                ""
            )

            detected = data.get(
                "responseData",
                {}
            ).get(
                "detectedLanguage",
                source
            )

            if not translated:
                await interaction.followup.send(
                    embed=self.embed(
                        "Error",
                        "Translation failed.",
                        True
                    )
                )
                return

            embed = discord.Embed(
                title="Translation",
                color=get_success_colour()
            )

            embed.add_field(
                name=f"Original ({detected})",
                value=text[:1000],
                inline=False
            )

            embed.add_field(
                name=f"Translated ({target})",
                value=translated[:1000],
                inline=False
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(
                embed=self.embed(
                    "Error",
                    f"Translation failed: {e}",
                    True
                )
            )

    def embed(self, title, desc, error=False):
        return discord.Embed(
            title=title,
            description=desc,
            color=0xFF0000 if error else 0xFFA500
        )

    @group_1.command(
        name="urban",
        description="Look up a term on Urban Dictionary"
    )
    @app_commands.describe(
        term="Term to look up"
    )
    async def urban(
        self,
        interaction: Interaction,
        term: str
    ):
        await interaction.response.defer()

        try:
            url = (
                "https://api.urbandictionary.com/v0/define"
                f"?term={urllib.parse.quote(term)}"
            )

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    data = await resp.json()

            definitions = data.get("list", [])

            if not definitions:
                await interaction.followup.send(
                    embed=self.embed(
                        "Error",
                        f"No definitions found for `{term}`",
                        True
                    )
                )
                return

            top = definitions[0]

            definition = top.get(
                "definition",
                "N/A"
            )[:1000]

            example = top.get(
                "example",
                ""
            )[:500]

            author = top.get(
                "author",
                "Unknown"
            )

            thumbs_up = top.get(
                "thumbs_up",
                0
            )

            thumbs_down = top.get(
                "thumbs_down",
                0
            )

            permalink = top.get(
                "permalink",
                ""
            )

            embed = discord.Embed(
                title=f"📖 {top.get('word', term)}",
                description=definition,
                color=get_success_colour(),
                url=permalink
            )

            if example:
                embed.add_field(
                    name="Example",
                    value=f"*{example}*",
                    inline=False
                )

            embed.set_footer(
                text=f"👍 {thumbs_up} | 👎 {thumbs_down} • by {author}"
            )

            view = discord.ui.View()

            view.add_item(
                discord.ui.Button(
                    label="View on Urban Dictionary",
                    url=permalink,
                    style=discord.ButtonStyle.link
                )
            )

            await interaction.followup.send(
                embed=embed,
                view=view
            )

        except Exception as e:
            await interaction.followup.send(
                embed=self.embed(
                    "Error",
                    f"Lookup failed: {e}",
                    True
                )
            )

    @group_1.command(
        name="define",
        description="Look up a word definition"
    )
    @app_commands.describe(
        word="Word to define"
    )
    async def define(
        self,
        interaction: Interaction,
        word: str
    ):
        await interaction.response.defer()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"https://api.dictionaryapi.dev/api/v2/entries/en/{urllib.parse.quote(word)}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        await interaction.followup.send(
                            embed=self.embed(
                                "Error",
                                f"No definition found for `{word}`",
                                True
                            )
                        )
                        return

                    data = await resp.json()

            entry = data[0]

            word_title = entry.get(
                "word",
                word
            )

            phonetic = entry.get(
                "phonetic",
                ""
            )

            embed = discord.Embed(
                title=f"📖 {word_title}",
                description=f"*{phonetic}*" if phonetic else "",
                color=get_success_colour()
            )

            for meaning in entry.get(
                "meanings",
                []
            )[:3]:
                pos = meaning.get(
                    "partOfSpeech",
                    ""
                )

                defs = meaning.get(
                    "definitions",
                    []
                )[:2]

                lines = []

                for d in defs:
                    lines.append(
                        f"• {d.get('definition', '')[:200]}"
                    )

                embed.add_field(
                    name=pos.title(),
                    value="\n".join(lines),
                    inline=False
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(
                embed=self.embed(
                    "Error",
                    f"Definition lookup failed: {e}",
                    True
                )
            )

    @group_1.command(
        name="ip",
        description="Look up an IP address"
    )
    @app_commands.describe(
        ip="IP address to look up"
    )
    async def ip(
        self,
        interaction: Interaction,
        ip: str
    ):
        await interaction.response.defer()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://ip-api.com/json/{ip}",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    data = await resp.json()

            if data.get("status") == "fail":
                await interaction.followup.send(
                    embed=self.embed(
                        "Error",
                        f"Could not look up `{ip}`",
                        True
                    )
                )
                return

            embed = discord.Embed(
                title=f"IP: {ip}",
                color=get_success_colour()
            )

            embed.add_field(
                name="Country",
                value=data.get("country", "?"),
                inline=True
            )

            embed.add_field(
                name="Region",
                value=data.get("regionName", "?"),
                inline=True
            )

            embed.add_field(
                name="City",
                value=data.get("city", "?"),
                inline=True
            )

            embed.add_field(
                name="ISP",
                value=data.get("isp", "?"),
                inline=True
            )

            embed.add_field(
                name="Org",
                value=data.get("org", "?"),
                inline=True
            )

            embed.add_field(
                name="AS",
                value=data.get("as", "?"),
                inline=True
            )

            embed.add_field(
                name="Lat/Lon",
                value=f"{data.get('lat', '?')}, {data.get('lon', '?')}",
                inline=True
            )

            embed.add_field(
                name="Timezone",
                value=data.get("timezone", "?"),
                inline=True
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(
                embed=self.embed(
                    "Error",
                    f"Lookup failed: {e}",
                    True
                )
            )

    @group_1.command(
        name="dns",
        description="DNS lookup for a domain"
    )
    @app_commands.describe(
        domain="Domain to look up"
    )
    async def dns(
        self,
        interaction: Interaction,
        domain: str
    ):
        await interaction.response.defer()

        try:
            results = {}

            try:
                ips = socket.getaddrinfo(
                    domain,
                    None
                )

                results["A"] = list(
                    set(
                        addr[4][0]
                        for addr in ips
                    )
                )

            except:
                pass

            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(
                        f"https://dns.google/resolve?name={domain}&type=ANY",
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        data = await resp.json()

                        for answer in data.get(
                            "Answer",
                            []
                        ):
                            rtype = answer.get(
                                "type",
                                0
                            )

                            value = answer.get(
                                "data",
                                ""
                            )

                            type_names = {
                                1: "A",
                                2: "NS",
                                5: "CNAME",
                                6: "SOA",
                                15: "MX",
                                16: "TXT",
                                28: "AAAA",
                                33: "SRV"
                            }

                            type_name = type_names.get(
                                rtype,
                                str(rtype)
                            )

                            if type_name not in results:
                                results[type_name] = []

                            results[type_name].append(value)

                except:
                    pass

            if not results:
                await interaction.followup.send(
                    embed=self.embed(
                        "Error",
                        f"No DNS records found for `{domain}`",
                        True
                    )
                )
                return

            embed = discord.Embed(
                title=f"DNS: {domain}",
                color=get_success_colour()
            )

            for rtype, values in results.items():
                embed.add_field(
                    name=rtype,
                    value="\n".join(values[:5]),
                    inline=False
                )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(
                embed=self.embed(
                    "Error",
                    f"DNS lookup failed: {e}",
                    True
                )
            )

    @group_1.command(
        name="whois",
        description="WHOIS lookup for a domain"
    )
    @app_commands.describe(
        domain="Domain to look up"
    )
    async def whois(
        self,
        interaction: Interaction,
        domain: str
    ):
        await interaction.response.defer()

        try:
            domain = domain.strip().lower()

            data = await asyncio.to_thread(
                whois.whois,
                domain
            )

            embed = discord.Embed(
                title=f"WHOIS: {domain}",
                color=get_success_colour()
            )

            def format_value(value):
                if value is None:
                    return None

                if isinstance(
                    value,
                    (list, tuple, set)
                ):
                    values = []

                    for item in value:
                        if item is not None:
                            values.append(str(item))

                    if not values:
                        return None

                    return "\n".join(values)

                return str(value)

            def add_field(
                name,
                value,
                inline=True,
                limit=1024
            ):
                value = format_value(value)

                if not value:
                    return

                if len(value) > limit:
                    value = value[:limit - 3] + "..."

                embed.add_field(
                    name=name,
                    value=value,
                    inline=inline
                )

            add_field("Domain", data.domain_name)
            add_field("Registrar", data.registrar)
            add_field("WHOIS Server", data.whois_server)
            add_field("Referral URL", data.referral_url)
            add_field("Created", data.creation_date)
            add_field("Updated", data.updated_date)
            add_field("Expires", data.expiration_date)
            add_field("Status", data.status, inline=False)
            add_field("Nameservers", data.name_servers, inline=False)
            add_field("Emails", data.emails, inline=False)
            add_field("DNSSEC", data.dnssec)
            add_field("Name", data.name)
            add_field("Organization", data.org)
            add_field("Country", data.country)
            add_field("State", data.state)
            add_field("City", data.city)
            add_field("Address", data.address)
            add_field("Postal Code", data.zipcode)
            add_field("Registrant Name", data.name)
            add_field("Registrant Organization", data.org)

            if not embed.fields:
                await interaction.followup.send(
                    embed=self.embed(
                        "Error",
                        "No WHOIS information was found for that domain.",
                        True
                    )
                )
                return

            embed.set_footer(
                text="Data retrieved from the domain's WHOIS server"
            )

            await interaction.followup.send(embed=embed)

        except Exception as e:
            await interaction.followup.send(
                embed=self.embed(
                    "Error",
                    f"WHOIS lookup failed: {e}",
                    True
                )
            )

    @group_1.command(
        name="portcheck",
        description="Check if a port is open on a host"
    )
    @app_commands.describe(
        host="Hostname or IP",
        port="Port number"
    )
    async def portcheck(
        self,
        interaction: Interaction,
        host: str,
        port: int
    ):
        await interaction.response.defer()

        try:
            open_port = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: socket.create_connection(
                        (host, port),
                        timeout=3
                    )
                ),
                timeout=5
            )

            open_port.close()

            await interaction.followup.send(
                embed=self.embed(
                    "✅ Port Open",
                    f"**{host}:{port}** is open."
                )
            )

        except (
            socket.timeout,
            ConnectionRefusedError,
            OSError
        ):
            await interaction.followup.send(
                embed=self.embed(
                    "❌ Port Closed",
                    f"**{host}:{port}** is closed or filtered."
                )
            )

        except Exception as e:
            await interaction.followup.send(
                embed=self.embed(
                    "❌ Error",
                    f"Check failed: {e}",
                    True
                )
            )

    @group_1.command(
        name="calculate",
        description="calculate a mathematical equation"
    )
    @app_commands.describe(
        equation="Equation"
    )
    async def calculate(
        self,
        interaction: Interaction,
        equation: str
    ):
        result = 0
        failed = False

        try:
            result = mathparse.parse(equation)
        except:
            failed = True

        result_str = str(result)

        if failed:
            result_str = "Failed, invalid input!"

        embed = discord.Embed(
            title="📐 Calculate",
            description=result_str,
            color=get_success_colour()
        )

        await interaction.response.send_message(
            embed=embed
        )

    @group_1.command(
        name="emojikitchen",
        description="blend two emojis together in the emoji kitchen!"
    )
    @app_commands.describe(
        emojione="Emoji 1",
        emojitwo="Emoji 2"
    )
    async def emojikitchen(
        self,
        interaction: Interaction,
        emojione: str,
        emojitwo: str
    ):
        await interaction.response.defer()

        url = f"https://emojik.vercel.app/s/{emojione}_{emojitwo}?size=512"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        embed = discord.Embed(
                            title="❌ Error",
                            description="The Emoji Kitchen API couldn't make that combination.",
                            color=get_fail_colour()
                        )
                        await interaction.followup.send(embed=embed)
                        return

                    image = await response.read()

            file = discord.File(
                io.BytesIO(image),
                filename="emoji-kitchen.png"
            )

            embed = discord.Embed(
                title="🍳 Emoji Kitchen",
                description=f"{emojione} + {emojitwo}",
                color=get_success_colour()
            )
            embed.set_image(url="attachment://emoji-kitchen.png")

            await interaction.followup.send(
                embed=embed,
                file=file
            )

        except aiohttp.ClientError:
            embed = discord.Embed(
                title="❌ Error",
                description="Failed to connect to the Emoji Kitchen API.",
                color=get_fail_colour()
            )

            await interaction.followup.send(embed=embed)

    group_2 = app_commands.Group(
        name="2",
        description="Utility - page 2"
    )
    
    @group_2.command(
        name ="daysuntilchristmas",
        description="Calculate how many days there are till christmas"
    )
    async def daysuntilchristmas(self, interaction: Interaction):
        now = datetime.now(timezone.utc)

        desired_time = datetime(now.year, 12, 25, tzinfo=timezone.utc)
        if now >= desired_time:
            desired_time = datetime(now.year + 1, 12, 25, tzinfo=timezone.utc)

        if now.day == desired_time.day and now.month == desired_time.month:
            embed = discord.Embed(
                title="🎄 It's Christmas!",
                description="Have a happy holidays, whatever you are celebrating today! 💗",
                color=get_success_colour()
            ) 
            embed.set_footer(
                text=f"Timezone is in UTC (Coordinated Universal Time)"
            )   
            await interaction.response.send_message(
                embed=embed
            )
            return

        diff = desired_time - now

        days = diff.days
        hours, remainder = divmod(diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        embed = discord.Embed(
            title="🎄 Time till Christmas",
            description=f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds left till the 25th of December {now.year}",
            color=get_success_colour()
        )
        embed.set_footer(
            text=f"Timezone is in UTC (Coordinated Universal Time)"
        )   
        
        await interaction.response.send_message(
            embed=embed
        )

    @group_2.command(
        name ="daysuntilhalloween",
        description="Calculate how many days there are till halloween"
    )
    async def daysuntilhalloween(self, interaction: Interaction):
        now = datetime.now(timezone.utc)

        desired_time = datetime(now.year, 10, 31, tzinfo=timezone.utc)
        if now >= desired_time:
            desired_time = datetime(now.year + 1, 10, 31, tzinfo=timezone.utc)

        if now.day == desired_time.day and now.month == desired_time.month:
            embed = discord.Embed(
                title="🎃 It's Halloween!",
                description="Have a happy halloween, whatever you are celebrating today! 💗",
                color=get_success_colour()
            ) 
            embed.set_footer(
                text=f"Timezone is in UTC (Coordinated Universal Time)"
            )   
            await interaction.response.send_message(
                embed=embed
            )
            return

        diff = desired_time - now

        days = diff.days
        hours, remainder = divmod(diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        embed = discord.Embed(
            title="🎃 Time till Halloween",
            description=f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds left till the 31st of October {now.year}",
            color=get_success_colour()
        )
        embed.set_footer(
            text=f"Timezone is in UTC (Coordinated Universal Time)"
        )   
        
        await interaction.response.send_message(
            embed=embed
        )

    @group_2.command(
        name ="daysuntileaster",
        description="Calculate how many days there are till Easter"
    )
    async def daysuntileaster(self, interaction: Interaction):
        now = datetime.now(timezone.utc)
        easter_date = easter(now.year)
        desired_time = datetime(
            easter_date.year,
            easter_date.month,
            easter_date.day,
            tzinfo=timezone.utc
        )

        if now >= desired_time:
            easter_date = easter(now.year + 1)
            desired_time = datetime(
                easter_date.year,
                easter_date.month,
                easter_date.day,
                tzinfo=timezone.utc
            )

        if now.day == desired_time.day and now.month == desired_time.month:
            embed = discord.Embed(
                title="🐣 It's Easter!",
                description="Have a happy Easter, whatever you are celebrating today! 💗",
                color=get_success_colour()
            )
            embed.set_footer(
                text=f"Timezone is in UTC (Coordinated Universal Time)"
            )

            await interaction.response.send_message(
                embed=embed
            )
            return

        diff = desired_time - now
        days = diff.days
        hours, remainder = divmod(diff.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)

        embed = discord.Embed(
            title="🐣 Time till Easter",
            description=f"{days} days, {hours} hours, {minutes} minutes, {seconds} seconds left till Easter {desired_time.year}",
            color=get_success_colour()
        )
        embed.set_footer(
            text=f"Timezone is in UTC (Coordinated Universal Time)"
        )

        await interaction.response.send_message(
            embed=embed
        )

async def setup(bot):
    await bot.add_cog(Utility(bot))