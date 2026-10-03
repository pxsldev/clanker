import asyncio
import io
import os
import shutil
import tempfile
from urllib.parse import urlparse
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from cogs.theming import get_fail_colour, get_success_colour
import random


MAX_DOWNLOAD_SIZE = 50 * 1024 * 1024
MAX_DURATION = 300


class Audio(commands.GroupCog, group_name="audio"):
    def __init__(self, bot):
        self.bot = bot

    audio_1 = app_commands.Group(
        name="1",
        description="Audio - page 1"
    )

    async def get_audio_data(
        self,
        attachment: discord.Attachment = None,
        url: str = None
    ):
        if not attachment and not url:
            raise ValueError("You need to provide an audio file or URL.")

        if attachment:
            if attachment.size > MAX_DOWNLOAD_SIZE:
                raise ValueError("That file is too large. The maximum size is 50 MB.")

            async with aiohttp.ClientSession() as session:
                async with session.get(attachment.url) as response:
                    if response.status != 200:
                        raise ValueError("I couldn't download that audio file.")

                    data = await response.read()

                    if len(data) > MAX_DOWNLOAD_SIZE:
                        raise ValueError("That file is too large. The maximum size is 50 MB.")

                    return data, attachment.filename

        parsed = urlparse(url)

        if parsed.scheme not in ("http", "https"):
            raise ValueError("Please provide a valid HTTP or HTTPS URL.")

        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(
                    url,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status != 200:
                        raise ValueError(
                            f"I couldn't download that URL. HTTP status: {response.status}"
                        )

                    content_length = response.headers.get("Content-Length")

                    if content_length:
                        try:
                            if int(content_length) > MAX_DOWNLOAD_SIZE:
                                raise ValueError(
                                    "That file is too large. The maximum size is 50 MB."
                                )
                        except ValueError as e:
                            if "too large" in str(e):
                                raise

                    data = await response.read()

                    if len(data) > MAX_DOWNLOAD_SIZE:
                        raise ValueError(
                            "That file is too large. The maximum size is 50 MB."
                        )

                    filename = os.path.basename(parsed.path) or "audio"

                    return data, filename

            except asyncio.TimeoutError:
                raise ValueError("The download timed out.")

    async def process_audio(
        self,
        data: bytes,
        filename: str,
        filters: str,
        output_format: str = "mp3"
    ):
        temp_dir = tempfile.mkdtemp(prefix="clanker_audio_")

        try:
            input_path = os.path.join(temp_dir, "input")
            output_path = os.path.join(temp_dir, f"output.{output_format}")

            with open(input_path, "wb") as f:
                f.write(data)

            probe_command = [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                input_path
            ]

            probe = await asyncio.create_subprocess_exec(
                *probe_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await probe.communicate()

            if probe.returncode != 0:
                raise ValueError("That doesn't appear to be a valid audio file.")

            try:
                duration = float(stdout.decode().strip())
            except (ValueError, AttributeError):
                duration = 0

            if duration > MAX_DURATION:
                raise ValueError(
                    "That audio file is too long. The maximum duration is 5 minutes."
                )

            command = [
                "ffmpeg",
                "-y",
                "-i",
                input_path,
                "-vn",
                "-af",
                filters,
                "-c:a",
                "libmp3lame",
                "-b:a",
                "192k",
                output_path
            ]

            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0 or not os.path.exists(output_path):
                error = stderr.decode(errors="ignore")

                if "Invalid data" in error:
                    raise ValueError("FFmpeg couldn't read that audio file.")

                raise ValueError("I couldn't process that audio file.")

            with open(output_path, "rb") as f:
                output_data = f.read()

            return output_data

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    async def send_result(
        self,
        interaction: discord.Interaction,
        data: bytes,
        filename: str,
        description: str
    ):
        if len(data) > 25 * 1024 * 1024:
            raise ValueError(
                "The processed audio is too large for Discord's upload limit."
            )

        embed = discord.Embed(
            title="Audio Edited",
            description=description,
            color=get_success_colour()
        )

        embed.set_footer(text="Clanker Audio")

        safe_name = os.path.splitext(filename)[0]
        safe_name = safe_name[:80]

        file = discord.File(
            io.BytesIO(data),
            filename=f"{safe_name}.mp3"
        )

        await interaction.followup.send(
            embed=embed,
            file=file
        )

    async def run_effect(
        self,
        interaction: discord.Interaction,
        attachment: discord.Attachment,
        url: str,
        filters: str,
        description: str
    ):
        await interaction.response.defer()

        try:
            data, filename = await self.get_audio_data(
                attachment=attachment,
                url=url
            )

            output = await self.process_audio(
                data,
                filename,
                filters
            )

            await self.send_result(
                interaction,
                output,
                filename,
                description
            )

        except ValueError as e:
            embed = discord.Embed(
                title="Audio Processing Failed",
                description=str(e),
                color=get_fail_colour()
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

        except Exception:
            embed = discord.Embed(
                title="Audio Processing Failed",
                description="Something went wrong while processing that audio.",
                color=get_fail_colour()
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

    @audio_1.command(
        name="mono",
        description="Convert audio to mono"
    )
    @app_commands.describe(
        audio="The audio file to edit",
        url="A URL to an audio file"
    )
    async def mono(
        self,
        interaction: discord.Interaction,
        audio: discord.Attachment = None,
        url: str = None
    ):
        await self.run_effect(
            interaction,
            audio,
            url,
            "pan=mono|c0=0.5*c0+0.5*c1",
            "Converted the audio to mono."
        )

    @audio_1.command(
        name="stereo",
        description="Convert mono audio to stereo"
    )
    @app_commands.describe(
        audio="The audio file to edit",
        url="A URL to an audio file"
    )
    async def stereo(
        self,
        interaction: discord.Interaction,
        audio: discord.Attachment = None,
        url: str = None
    ):
        await self.run_effect(
            interaction,
            audio,
            url,
            "pan=stereo|c0=c0|c1=c0",
            "Converted the audio to stereo."
        )

    @audio_1.command(
        name="volume",
        description="Change the volume"
    )
    @app_commands.describe(
        amount="Volume multiplier from 0.1x to 10x",
        audio="The audio file to edit",
        url="A URL to an audio file"
    )
    async def volume(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[float, 0.1, 10.0],
        audio: discord.Attachment = None,
        url: str = None
    ):
        await self.run_effect(
            interaction,
            audio,
            url,
            f"volume={amount}",
            f"Changed the volume to {amount:g}x."
        )

    @audio_1.command(
        name="bass",
        description="Boost or reduce bass"
    )
    @app_commands.describe(
        amount="Bass adjustment from -20 to +20 dB",
        audio="The audio file to edit",
        url="A URL to an audio file"
    )
    async def bass(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[float, -20.0, 20.0],
        audio: discord.Attachment = None,
        url: str = None
    ):
        await self.run_effect(
            interaction,
            audio,
            url,
            f"bass=g={amount}:f=100",
            f"Adjusted bass by {amount:g} dB."
        )

    @audio_1.command(
        name="treble",
        description="Boost or reduce treble"
    )
    @app_commands.describe(
        amount="Treble adjustment from -20 to +20 dB",
        audio="The audio file to edit",
        url="A URL to an audio file"
    )
    async def treble(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[float, -20.0, 20.0],
        audio: discord.Attachment = None,
        url: str = None
    ):
        await self.run_effect(
            interaction,
            audio,
            url,
            f"treble=g={amount}:f=3000",
            f"Adjusted treble by {amount:g} dB."
        )

    @audio_1.command(
        name="speed",
        description="Speed up or slow down audio"
    )
    @app_commands.describe(
        amount="Playback speed from 0.25x to 4x",
        audio="The audio file to edit",
        url="A URL to an audio file"
    )
    async def speed(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[float, 0.25, 4.0],
        audio: discord.Attachment = None,
        url: str = None
    ):
        if amount >= 0.5 and amount <= 2.0:
            filters = f"atempo={amount}"
        elif amount > 2.0:
            filters = f"atempo=2.0,atempo={amount / 2}"
        else:
            filters = f"atempo=0.5,atempo={amount / 0.5}"

        await self.run_effect(
            interaction,
            audio,
            url,
            filters,
            f"Changed playback speed to {amount:g}x."
        )

    @audio_1.command(
        name="pitch",
        description="Change the pitch of audio"
    )
    @app_commands.describe(
        amount="Pitch adjustment from -12 to +12 semitones",
        audio="The audio file to edit",
        url="A URL to an audio file"
    )
    async def pitch(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[float, -12.0, 12.0],
        audio: discord.Attachment = None,
        url: str = None
    ):
        ratio = 2 ** (amount / 12)

        filters = (
            f"asetrate=44100*{ratio},"
            f"aresample=44100,"
            f"atempo={1 / ratio}"
        )

        await self.run_effect(
            interaction,
            audio,
            url,
            filters,
            f"Changed pitch by {amount:g} semitones."
        )

    @audio_1.command(
        name="reverse",
        description="Reverse the audio"
    )
    @app_commands.describe(
        audio="The audio file to reverse",
        url="A URL to an audio file"
    )
    async def reverse(
        self,
        interaction: discord.Interaction,
        audio: discord.Attachment = None,
        url: str = None
    ):
        await self.run_effect(
            interaction,
            audio,
            url,
            "areverse",
            "Reversed the audio."
        )

    @audio_1.command(
        name="fade",
        description="Add a fade in and fade out"
    )
    @app_commands.describe(
        amount="Fade duration from 0.1 to 30 seconds",
        audio="The audio file to edit",
        url="A URL to an audio file"
    )
    async def fade(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[float, 0.1, 30.0],
        audio: discord.Attachment = None,
        url: str = None
    ):
        await interaction.response.defer()

        try:
            data, filename = await self.get_audio_data(audio, url)

            temp_dir = tempfile.mkdtemp(prefix="clanker_audio_")

            try:
                input_path = os.path.join(temp_dir, "input")
                output_path = os.path.join(temp_dir, "output.mp3")

                with open(input_path, "wb") as f:
                    f.write(data)

                probe_command = [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    input_path
                ]

                probe = await asyncio.create_subprocess_exec(
                    *probe_command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                stdout, _ = await probe.communicate()

                try:
                    total_duration = float(stdout.decode().strip())
                except ValueError:
                    raise ValueError("I couldn't determine the audio duration.")

                if total_duration > MAX_DURATION:
                    raise ValueError(
                        "That audio file is too long. The maximum duration is 5 minutes."
                    )

                if amount * 2 > total_duration:
                    raise ValueError(
                        "The fade amount is too long for this audio."
                    )

                filters = (
                    f"afade=t=in:st=0:d={amount},"
                    f"afade=t=out:st={total_duration - amount}:d={amount}"
                )

                command = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    input_path,
                    "-vn",
                    "-af",
                    filters,
                    "-c:a",
                    "libmp3lame",
                    "-b:a",
                    "192k",
                    output_path
                ]

                process = await asyncio.create_subprocess_exec(
                    *command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )

                _, stderr = await process.communicate()

                if process.returncode != 0:
                    raise ValueError("FFmpeg couldn't create the fade effect.")

                with open(output_path, "rb") as f:
                    output = f.read()

            finally:
                shutil.rmtree(temp_dir, ignore_errors=True)

            await self.send_result(
                interaction,
                output,
                filename,
                f"Added a {amount:g}-second fade in and fade out."
            )

        except ValueError as e:
            embed = discord.Embed(
                title="Audio Processing Failed",
                description=str(e),
                color=get_fail_colour()
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

        except Exception:
            embed = discord.Embed(
                title="Audio Processing Failed",
                description="Something went wrong while processing that audio.",
                color=get_fail_colour()
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

    @audio_1.command(
        name="echo",
        description="Add an echo effect"
    )
    @app_commands.describe(
        delay="Echo delay from 50 to 2000 milliseconds",
        decay="Echo volume decay from 0.1 to 0.9",
        audio="The audio file to edit",
        url="A URL to an audio file"
    )
    async def echo(
        self,
        interaction: discord.Interaction,
        delay: app_commands.Range[int, 50, 2000],
        decay: app_commands.Range[float, 0.1, 0.9],
        audio: discord.Attachment = None,
        url: str = None
    ):
        filters = f"aecho=0.8:0.9:{delay}:{decay}"

        await self.run_effect(
            interaction,
            audio,
            url,
            filters,
            f"Added an echo with a {delay}ms delay and {decay:g} decay."
        )

    @audio_1.command(
        name="reverb",
        description="Add a reverb effect"
    )
    @app_commands.describe(
        amount="Reverb strength from 0.1 to 1.0",
        audio="The audio file to edit",
        url="A URL to an audio file"
    )
    async def reverb(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[float, 0.1, 1.0],
        audio: discord.Attachment = None,
        url: str = None
    ):
        filters = (
            f"aecho=0.8:0.88:60:0.4,"
            f"aecho=0.8:0.88:120:{amount}"
        )

        await self.run_effect(
            interaction,
            audio,
            url,
            filters,
            f"Added reverb at {amount:g} strength."
        )

    @audio_1.command(
        name="distortion",
        description="Add distortion"
    )
    @app_commands.describe(
        amount="Distortion strength from 1 to 10",
        audio="The audio file to edit",
        url="A URL to an audio file"
    )
    async def distortion(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[float, 1.0, 10.0],
        audio: discord.Attachment = None,
        url: str = None
    ):
        filters = f"acrusher=bits=8:mix={min(amount / 10, 1.0)}"

        await self.run_effect(
            interaction,
            audio,
            url,
            filters,
            f"Added distortion at {amount:g} strength."
        )

    @audio_1.command(
        name="normalize",
        description="Normalize the audio volume"
    )
    @app_commands.describe(
        audio="The audio file to normalize",
        url="A URL to an audio file"
    )
    async def normalize(
        self,
        interaction: discord.Interaction,
        audio: discord.Attachment = None,
        url: str = None
    ):
        await self.run_effect(
            interaction,
            audio,
            url,
            "loudnorm",
            "Normalized the audio volume."
        )

    @audio_1.command(
        name="bassboost",
        description="Give the audio heavy bass"
    )
    @app_commands.describe(
        amount="Bass boost from 1 to 20 dB",
        audio="The audio file to edit",
        url="A URL to an audio file"
    )
    async def bassboost(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[float, 1.0, 20.0],
        audio: discord.Attachment = None,
        url: str = None
    ):
        filters = (
            f"bass=g={amount}:f=100,"
            f"equalizer=f=60:t=q:w=1:g={amount / 2}"
        )

        await self.run_effect(
            interaction,
            audio,
            url,
            filters,
            f"Applied a {amount:g} dB bass boost."
        )

    @audio_1.command(
        name="nightcore",
        description="Turn audio into a nightcore-style version"
    )
    @app_commands.describe(
        amount="Nightcore speed from 1.05x to 1.75x",
        audio="The audio file to edit",
        url="A URL to an audio file"
    )
    async def nightcore(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[float, 1.05, 1.75],
        audio: discord.Attachment = None,
        url: str = None
    ):
        ratio = amount

        filters = (
            f"asetrate=44100*{ratio},"
            f"aresample=44100,"
            f"atempo=1.0"
        )

        await self.run_effect(
            interaction,
            audio,
            url,
            filters,
            f"Created a nightcore-style version at {amount:g}x speed."
        )

    @audio_1.command(
        name="slowed",
        description="Make the audio slowed and lower-pitched"
    )
    @app_commands.describe(
        amount="Slowed speed from 0.5x to 0.95x",
        audio="The audio file to edit",
        url="A URL to an audio file"
    )
    async def slowed(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[float, 0.5, 0.95],
        audio: discord.Attachment = None,
        url: str = None
    ):
        ratio = amount

        filters = (
            f"asetrate=44100*{ratio},"
            f"aresample=44100,"
            f"atempo=1.0"
        )

        await self.run_effect(
            interaction,
            audio,
            url,
            filters,
            f"Slowed the audio to {amount:g}x speed."
        )

    @audio_1.command(
        name="8d",
        description="Add a moving 8D-style stereo effect"
    )
    @app_commands.describe(
        amount="Movement speed from 0.05 to 1.0",
        audio="The audio file to edit",
        url="A URL to an audio file"
    )
    async def eight_d(
        self,
        interaction: discord.Interaction,
        amount: app_commands.Range[float, 0.05, 1.0],
        audio: discord.Attachment = None,
        url: str = None
    ):
        filters = f"apulsator=hz={amount}:width=1"

        await self.run_effect(
            interaction,
            audio,
            url,
            filters,
            f"Added an 8D-style stereo movement effect at {amount:g} movement speed."
        )

    @audio_1.command(
        name="destroy",
        description="Absolutely destroy the audio with random effects"
    )
    @app_commands.describe(
        audio="The audio file to destroy",
        url="A URL to an audio file"
    )
    async def destroy(
        self,
        interaction: discord.Interaction,
        audio: discord.Attachment = None,
        url: str = None
    ):
        await interaction.response.defer()

        try:
            data, filename = await self.get_audio_data(
                attachment=audio,
                url=url
            )

            effects = []

            possible_effects = [
                "volume",
                "bass",
                "treble",
                "speed",
                "pitch",
                "echo",
                "reverb",
                "distortion",
                "bassboost",
                "8d",
                "reverse"
            ]

            effect_count = random.randint(3, 7)
            selected_effects = random.sample(
                possible_effects,
                min(effect_count, len(possible_effects))
            )

            for effect in selected_effects:
                if effect == "volume":
                    amount = random.uniform(0.2, 4.0)
                    effects.append(f"volume={amount:.2f}")

                elif effect == "bass":
                    amount = random.uniform(-15, 15)
                    effects.append(
                        f"bass=g={amount:.2f}:f={random.randint(60, 180)}"
                    )

                elif effect == "treble":
                    amount = random.uniform(-15, 15)
                    effects.append(
                        f"treble=g={amount:.2f}:f={random.randint(2000, 6000)}"
                    )

                elif effect == "speed":
                    amount = random.uniform(0.5, 2.0)
                    effects.append(f"atempo={amount:.2f}")

                elif effect == "pitch":
                    amount = random.uniform(-7, 7)
                    ratio = 2 ** (amount / 12)

                    effects.extend([
                        f"asetrate=44100*{ratio:.4f}",
                        "aresample=44100",
                        f"atempo={1 / ratio:.4f}"
                    ])

                elif effect == "echo":
                    delay = random.randint(100, 1200)
                    decay = random.uniform(0.2, 0.8)

                    effects.append(
                        f"aecho=0.8:0.9:{delay}:{decay:.2f}"
                    )

                elif effect == "reverb":
                    decay = random.uniform(0.2, 0.9)

                    effects.extend([
                        f"aecho=0.8:0.88:{random.randint(40, 100)}:{decay:.2f}",
                        f"aecho=0.8:0.88:{random.randint(100, 250)}:{decay / 2:.2f}"
                    ])

                elif effect == "distortion":
                    amount = random.uniform(0.2, 1.0)

                    effects.append(
                        f"acrusher=bits={random.randint(4, 10)}:mix={amount:.2f}"
                    )

                elif effect == "bassboost":
                    amount = random.uniform(5, 18)

                    effects.extend([
                        f"bass=g={amount:.2f}:f=100",
                        f"equalizer=f={random.randint(40, 100)}:t=q:w=1:g={amount / 2:.2f}"
                    ])

                elif effect == "8d":
                    hz = random.uniform(0.05, 0.8)

                    effects.append(
                        f"apulsator=hz={hz:.3f}:width=1"
                    )

                elif effect == "reverse":
                    effects.append("areverse")

            filters = ",".join(effects)

            output = await self.process_audio(
                data,
                filename,
                filters
            )

            effect_names = ", ".join(
                effect.replace("8d", "8D")
                for effect in selected_effects
            )

            await self.send_result(
                interaction,
                output,
                filename,
                f"Completely destroyed the audio with {len(selected_effects)} random effects.\n\n"
                f"**Effects:** {effect_names}"
            )

        except ValueError as e:
            embed = discord.Embed(
                title="Audio Destruction Failed",
                description=str(e),
                color=get_fail_colour()
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

        except Exception:
            embed = discord.Embed(
                title="Audio Destruction Failed",
                description="Something went wrong while destroying that audio.",
                color=get_fail_colour()
            )

            await interaction.followup.send(
                embed=embed,
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Audio(bot))