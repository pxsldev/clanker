from discord import app_commands, Interaction
from discord.ext import commands
import discord
import aiohttp
import asyncio
import os
import tempfile
import shutil
import random
import subprocess
from cogs.theming import get_fail_colour, get_success_colour
import math
from PIL import Image


class Video(commands.GroupCog, group_name="video"):

    video_1 = app_commands.Group(
        name="1",
        description="Videos - page 1"
    )

    MAX_DOWNLOAD_SIZE = 50 * 1024 * 1024
    MAX_DURATION = 30
    MAX_OUTPUT_SIZE = 50 * 1024 * 1024
    FFMPEG_PATH = r"C:\Users\pxslb\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffmpeg.exe"
    FFPROBE_PATH = r"C:\Users\pxslb\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.1-full_build\bin\ffprobe.exe"

    def __init__(self, bot):
        self.bot = bot

    async def send_error(
        self,
        interaction: Interaction,
        title: str,
        desc: str
    ):
        embed = discord.Embed(
            title=title,
            description=desc,
            color=get_fail_colour()
        )

        if interaction.response.is_done():
            await interaction.followup.send(
                embed=embed
            )
        else:
            await interaction.response.send_message(
                embed=embed
            )

    async def get_media_url(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        if media:
            return media.url

        if url:
            return url

        if interaction.message and interaction.message.reference:
            try:
                replied = await interaction.channel.fetch_message(
                    interaction.message.reference.message_id
                )

                if replied.attachments:
                    return replied.attachments[0].url

            except Exception:
                pass

        try:
            async for message in interaction.channel.history(
                limit=20
            ):
                if message.attachments:
                    return message.attachments[0].url

        except Exception:
            pass

        return None

    async def download_media(
        self,
        media_url: str,
        output_path: str
    ):
        try:
            timeout = aiohttp.ClientTimeout(
                total=120
            )

            async with aiohttp.ClientSession(
                timeout=timeout
            ) as session:

                async with session.get(
                    media_url,
                    allow_redirects=True
                ) as response:

                    if response.status != 200:
                        return False, (
                            f"Failed to download the video "
                            f"(HTTP {response.status})."
                        )

                    content_length = response.headers.get(
                        "Content-Length"
                    )

                    if content_length:
                        try:
                            if int(content_length) > self.MAX_DOWNLOAD_SIZE:
                                return False, (
                                    "That file is too large.\n\n"
                                    "The maximum allowed file size is **50 MB**."
                                )
                        except Exception:
                            pass

                    total = 0

                    with open(
                        output_path,
                        "wb"
                    ) as file:

                        async for chunk in response.content.iter_chunked(
                            1024 * 256
                        ):
                            total += len(chunk)

                            if total > self.MAX_DOWNLOAD_SIZE:
                                try:
                                    os.remove(output_path)
                                except Exception:
                                    pass

                                return False, (
                                    "That file is too large.\n\n"
                                    "The maximum allowed file size is **50 MB**."
                                )

                            file.write(chunk)

            if not os.path.exists(output_path):
                return False, "The downloaded file does not exist."

            if os.path.getsize(output_path) <= 0:
                return False, "The downloaded file is empty."

            return True, None

        except asyncio.TimeoutError:
            return False, "The video download timed out."

        except aiohttp.ClientError as e:
            print(
                f"[VIDEO DOWNLOAD] {e}"
            )

            return False, "Failed to download the video."

        except Exception as e:
            print(
                f"[VIDEO DOWNLOAD] {e}"
            )

            return False, "Failed to download the video."

    async def run_process(
        self,
        command,
        timeout=120
    ):
        process = None

        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout
            )

            return (
                process.returncode,
                stdout.decode(
                    errors="ignore"
                ),
                stderr.decode(
                    errors="ignore"
                )
            )

        except FileNotFoundError as e:
            print(
                f"[VIDEO PROCESS] Executable not found: {e}"
            )

            return (
                -1,
                "",
                "Required media processing executable was not found."
            )

        except asyncio.TimeoutError:
            if process:
                try:
                    process.kill()
                except Exception:
                    pass

                try:
                    await process.wait()
                except Exception:
                    pass

            return (
                -1,
                "",
                "FFmpeg timed out."
            )

        except Exception as e:
            print(
                f"[VIDEO PROCESS] {e}"
            )

            return (
                -1,
                "",
                str(e)
            )

    async def validate_video(self, path):
        if not os.path.exists(path):
            return False, "The downloaded video file does not exist."

        if os.path.getsize(path) <= 0:
            return False, "The downloaded video file is empty."

        code, stdout, stderr = await self.run_process([
            self.FFMPEG_PATH,
            "-hide_banner",
            "-v",
            "error",
            "-i",
            path,
            "-map",
            "0:v:0",
            "-frames:v",
            "1",
            "-f",
            "null",
            "-"
        ], timeout=30)

        if code != 0:
            print("\n========== VIDEO VALIDATION ERROR ==========")
            print(f"File: {path}")
            print(f"Return code: {code}")
            print(f"stdout: {stdout}")
            print(f"stderr: {stderr}")
            print("============================================\n")

            return False, stderr or "FFmpeg could not decode the video."

        return True, None

    async def get_video_duration(
        self,
        input_path
    ):
        command = [
            self.FFMPEG_PATH,
            "-hide_banner",
            "-i",
            input_path
        ]

        code, stdout, stderr = await self.run_process(
            command,
            timeout=30
        )

        combined = (
            stdout +
            "\n" +
            stderr
        )

        marker = "Duration:"

        if marker not in combined:
            return None

        try:
            duration_text = combined.split(
                marker,
                1
            )[1].split(
                ",",
                1
            )[0].strip()

            hours, minutes, seconds = duration_text.split(
                ":"
            )

            return (
                int(hours) * 3600
                +
                int(minutes) * 60
                +
                float(seconds)
            )

        except Exception as e:
            print(
                f"[VIDEO DURATION] {e}"
            )

            return None

    async def load_video(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        media_url = await self.get_media_url(
            interaction,
            media,
            url
        )

        if not media_url:
            return (
                None,
                None,
                "Missing Video ⚠️",
                "Upload, reply, or provide a direct video URL."
            )

        temp_dir = tempfile.mkdtemp()

        extension = ".mp4"

        if media:
            attachment_name = media.filename.lower()

            if "." in attachment_name:
                extension = os.path.splitext(
                    attachment_name
                )[1]

        input_path = os.path.join(
            temp_dir,
            f"input{extension}"
        )

        success, error = await self.download_media(
            media_url,
            input_path
        )

        if not success:
            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )

            return (
                None,
                None,
                "Download Failed 🚫",
                error
            )

        valid, error = await self.validate_video(
            input_path
        )

        if not valid:
            print(
                f"[VIDEO] Invalid input: {input_path}"
            )

            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )

            return (
                None,
                None,
                "Invalid Video 🚫",
                error
            )

        duration = await self.get_video_duration(
            input_path
        )

        if duration is not None:
            if duration > self.MAX_DURATION:
                shutil.rmtree(
                    temp_dir,
                    ignore_errors=True
                )

                return (
                    None,
                    None,
                    "Video Too Long 🚫",
                    (
                        f"Videos are limited to "
                        f"**{self.MAX_DURATION} seconds**."
                    )
                )

        return (
            temp_dir,
            input_path,
            None,
            None
        )

    async def finish_video(
        self,
        interaction: Interaction,
        temp_dir,
        output_path,
        title,
        filename,
        description=None
    ):
        try:
            if not os.path.exists(
                output_path
            ):
                return await self.send_error(
                    interaction,
                    "Processing Failed 🚫",
                    "FFmpeg didn't produce an output file."
                )

            size = os.path.getsize(
                output_path
            )

            if size <= 0:
                return await self.send_error(
                    interaction,
                    "Processing Failed 🚫",
                    "The generated video was empty."
                )

            if size > self.MAX_OUTPUT_SIZE:
                return await self.send_error(
                    interaction,
                    "Output Too Large 🚫",
                    "The processed video is larger than **50 MB**."
                )

            file = discord.File(
                output_path,
                filename=filename
            )

            embed = discord.Embed(
                title=title,
                description=description or "",
                color=get_success_colour()
            )

            if interaction.response.is_done():
                await interaction.followup.send(
                    embed=embed,
                    file=file
                )
            else:
                await interaction.response.send_message(
                    embed=embed,
                    file=file
                )

        finally:
            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )

    async def process(
        self,
        interaction,
        media,
        url,
        filters,
        title,
        filename="video.mp4",
        description=None
    ):
        await interaction.response.defer()

        (
            temp_dir,
            input_path,
            error_title,
            error_desc
        ) = await self.load_video(
            interaction,
            media,
            url
        )

        if not input_path:
            return await self.send_error(
                interaction,
                error_title,
                error_desc
            )

        output_path = os.path.join(
            temp_dir,
            filename
        )

        command = [
            self.FFMPEG_PATH,
            "-y",
            "-hide_banner",
            "-i",
            input_path,
            "-map",
            "0:v:0",
            "-map",
            "0:a?"
        ]

        if filters:
            command.extend([
                "-vf",
                filters
            ])

        command.extend([
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            output_path
        ])

        code, stdout, stderr = await self.run_process(
            command,
            timeout=180
        )

        if code != 0:
            print(
                "[VIDEO PROCESSING ERROR]"
            )

            print(
                stderr[-6000:]
            )

            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )

            return await self.send_error(
                interaction,
                "Video Processing Failed 🚫",
                "FFmpeg couldn't process that video."
            )

        await self.finish_video(
            interaction,
            temp_dir,
            output_path,
            title,
            filename,
            description
        )

    @video_1.command(
        name="invert",
        description="Invert a video"
    )
    async def invert(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        await self.process(
            interaction,
            media,
            url,
            "negate",
            "Inverted Video 🌀",
            "invert.mp4"
        )

    @video_1.command(
        name="greyscale",
        description="Convert a video to greyscale"
    )
    async def greyscale(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        await self.process(
            interaction,
            media,
            url,
            "format=gray",
            "Greyscale Video ⚪",
            "greyscale.mp4"
        )

    @video_1.command(
        name="deepfry",
        description="Deep fry a video"
    )
    async def deepfry(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        await self.process(
            interaction,
            media,
            url,
            (
                "eq="
                "contrast=2.2:"
                "saturation=3:"
                "brightness=0.05,"
                "unsharp=5:5:1.5:5:5:0"
            ),
            "Deepfried Video 💥",
            "deepfry.mp4"
        )

    @video_1.command(
        name="blur",
        description="Blur a video"
    )
    async def blur(
        self,
        interaction: Interaction,
        amount: int = 5,
        media: discord.Attachment = None,
        url: str = None
    ):
        amount = max(
            0,
            min(
                amount,
                25
            )
        )

        sigma = max(
            0.1,
            amount / 2
        )

        await self.process(
            interaction,
            media,
            url,
            f"gblur=sigma={sigma}",
            f"Blurred Video (Amount: {amount}) 💨",
            "blur.mp4"
        )

    @video_1.command(
        name="bloom",
        description="Add bloom effect to a video"
    )
    async def bloom(
        self,
        interaction: Interaction,
        amount: float = 1.5,
        media: discord.Attachment = None,
        url: str = None
    ):
        amount = max(
            0.1,
            min(
                amount,
                3.0
            )
        )

        await self.process(
            interaction,
            media,
            url,
            (
                f"split=2[main][glow];"
                f"[glow]gblur=sigma={4 + amount * 4}[blur];"
                f"[main][blur]blend=all_mode=screen:"
                f"all_opacity={min(0.8, amount * 0.25)}"
            ),
            f"Bloom Video (Amount: {amount}) ✨",
            "bloom.mp4"
        )

    @video_1.command(
        name="pixelate",
        description="Pixelate a video"
    )
    async def pixelate(
        self,
        interaction: Interaction,
        amount: int = 10,
        media: discord.Attachment = None,
        url: str = None
    ):
        amount = max(
            2,
            min(
                amount,
                50
            )
        )

        await self.process(
            interaction,
            media,
            url,
            (
                f"scale="
                f"ceil(iw/{amount}/2)*2:"
                f"ceil(ih/{amount}/2)*2:"
                f"flags=neighbor,"
                f"scale=iw*{amount}:"
                f"ih*{amount}:"
                f"flags=neighbor"
            ),
            f"Pixelated Video (Amount: {amount}) 🟫",
            "pixelate.mp4"
        )

    @video_1.command(
        name="gif",
        description="Turn a video into a GIF"
    )
    async def gif(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        await interaction.response.defer()

        (
            temp_dir,
            input_path,
            error_title,
            error_desc
        ) = await self.load_video(
            interaction,
            media,
            url
        )

        if not input_path:
            return await self.send_error(
                interaction,
                error_title,
                error_desc
            )

        output_path = os.path.join(
            temp_dir,
            "video.gif"
        )

        palette_path = os.path.join(
            temp_dir,
            "palette.png"
        )

        palette_command = [
            self.FFMPEG_PATH,
            "-y",
            "-hide_banner",
            "-i",
            input_path,
            "-vf",
            "fps=15,scale=720:-1:flags=lanczos,palettegen=stats_mode=diff",
            palette_path
        ]

        code, _, stderr = await self.run_process(
            palette_command,
            timeout=120
        )

        if code != 0:
            print(
                stderr[-5000:]
            )

            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )

            return await self.send_error(
                interaction,
                "GIF Conversion Failed 🚫",
                "FFmpeg couldn't generate a GIF palette."
            )

        gif_command = [
            self.FFMPEG_PATH,
            "-y",
            "-hide_banner",
            "-i",
            input_path,
            "-i",
            palette_path,
            "-filter_complex",
            (
                "[0:v]"
                "fps=15,"
                "scale=720:-1:flags=lanczos"
                "[x];"
                "[x][1:v]"
                "paletteuse=dither=sierra2_4a"
            ),
            "-loop",
            "0",
            output_path
        ]

        code, _, stderr = await self.run_process(
            gif_command,
            timeout=180
        )

        if code != 0:
            print(
                stderr[-5000:]
            )

            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )

            return await self.send_error(
                interaction,
                "GIF Conversion Failed 🚫",
                "FFmpeg couldn't create the GIF."
            )

        await self.finish_video(
            interaction,
            temp_dir,
            output_path,
            "Video → GIF 🎞️",
            "video.gif",
            "Converted successfully."
        )

    async def extract_frame(
        self,
        interaction,
        media,
        url,
        extension,
        title,
        codec
    ):
        await interaction.response.defer()

        (
            temp_dir,
            input_path,
            error_title,
            error_desc
        ) = await self.load_video(
            interaction,
            media,
            url
        )

        if not input_path:
            return await self.send_error(
                interaction,
                error_title,
                error_desc
            )

        output_path = os.path.join(
            temp_dir,
            f"frame.{extension}"
        )

        command = [
            self.FFMPEG_PATH,
            "-y",
            "-hide_banner",
            "-i",
            input_path,
            "-frames:v",
            "1",
            "-vf",
            "scale='min(3000,iw)':'min(3000,ih)':force_original_aspect_ratio=decrease"
        ]

        if extension == "jpg":
            command.extend([
                "-q:v",
                "2"
            ])

        command.extend([
            "-c:v",
            codec,
            output_path
        ])

        code, _, stderr = await self.run_process(
            command,
            timeout=60
        )

        if code != 0:
            print(
                stderr[-5000:]
            )

            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )

            return await self.send_error(
                interaction,
                "Frame Extraction Failed 🚫",
                "I couldn't extract a frame from that video."
            )

        await self.finish_video(
            interaction,
            temp_dir,
            output_path,
            title,
            f"video.{extension}"
        )

    @video_1.command(
        name="png",
        description="Extract the first frame as PNG"
    )
    async def png(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        await self.extract_frame(
            interaction,
            media,
            url,
            "png",
            "Video → PNG 🖼️",
            "png"
        )

    @video_1.command(
        name="jpg",
        description="Extract the first frame as JPG"
    )
    async def jpg(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        await self.extract_frame(
            interaction,
            media,
            url,
            "jpg",
            "Video → JPG 🖼️",
            "mjpeg"
        )

    @video_1.command(
        name="webp",
        description="Extract the first frame as WebP"
    )
    async def webp(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        await self.extract_frame(
            interaction,
            media,
            url,
            "webp",
            "Video → WebP 🖼️",
            "libwebp"
        )

    @video_1.command(
        name="caption",
        description="Add a caption to a video"
    )
    async def caption(
        self,
        interaction: Interaction,
        text: str,
        media: discord.Attachment = None,
        url: str = None
    ):
        if not text:
            return await self.send_error(
                interaction,
                "Missing Text ⚠️",
                "Please provide a caption."
            )

        await interaction.response.defer()

        (
            temp_dir,
            input_path,
            error_title,
            error_desc
        ) = await self.load_video(
            interaction,
            media,
            url
        )

        if not input_path:
            return await self.send_error(
                interaction,
                error_title,
                error_desc
            )

        output_path = os.path.join(
            temp_dir,
            "caption.mp4"
        )

        safe_text = (
            text
            .replace(
                "\\",
                "\\\\"
            )
            .replace(
                ":",
                "\\:"
            )
            .replace(
                "'",
                "\\'"
            )
            .replace(
                "[",
                "\\["
            )
            .replace(
                "]",
                "\\]"
            )
            .replace(
                "%",
                "\\%"
            )
        )

        font = "C:/Windows/Fonts/impact.ttf"

        if not os.path.exists(
            font
        ):
            font = "C:/Windows/Fonts/arial.ttf"

        filters = (
            f"drawtext="
            f"fontfile='{font}':"
            f"text='{safe_text}':"
            f"fontcolor=black:"
            f"fontsize=min(64\,w/10):"
            f"x=(w-text_w)/2:"
            f"y=20:"
            f"box=1:"
            f"boxcolor=white:"
            f"boxborderw=20"
        )

        command = [
            self.FFMPEG_PATH,
            "-y",
            "-hide_banner",
            "-i",
            input_path,
            "-vf",
            filters,
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-movflags",
            "+faststart",
            output_path
        ]

        code, _, stderr = await self.run_process(
            command,
            timeout=180
        )

        if code != 0:
            print(
                f"[VIDEO CAPTION]\n{stderr[-5000:]}"
            )

            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )

            return await self.send_error(
                interaction,
                "Caption Failed 🚫",
                "I couldn't add that caption to the video."
            )

        await self.finish_video(
            interaction,
            temp_dir,
            output_path,
            "Caption 📝",
            "caption.mp4"
        )

    @video_1.command(
        name="brighten",
        description="Brighten a video"
    )
    async def brighten(
        self,
        interaction: Interaction,
        amount: int = 1,
        media: discord.Attachment = None,
        url: str = None
    ):
        amount = max(
            0,
            min(
                amount,
                5
            )
        )

        await self.process(
            interaction,
            media,
            url,
            f"eq=brightness={amount * 0.2}",
            f"Brightened Video ☀️ (Level: {amount})",
            "brighten.mp4"
        )

    @video_1.command(
        name="darken",
        description="Darken a video"
    )
    async def darken(
        self,
        interaction: Interaction,
        amount: int = 1,
        media: discord.Attachment = None,
        url: str = None
    ):
        amount = max(
            0,
            min(
                amount,
                5
            )
        )

        await self.process(
            interaction,
            media,
            url,
            f"eq=brightness={-(amount * 0.2)}",
            f"Darkened Video 🌑 (Level: {amount})",
            "darken.mp4"
        )

    @video_1.command(
        name="sharpen",
        description="Sharpen a video"
    )
    async def sharpen(
        self,
        interaction: Interaction,
        amount: int = 1,
        media: discord.Attachment = None,
        url: str = None
    ):
        amount = max(
            1,
            min(
                amount,
                10
            )
        )

        await self.process(
            interaction,
            media,
            url,
            f"unsharp=5:5:{amount * 0.7}:5:5:0",
            f"Sharpened Video 🔪 (Amount: {amount})",
            "sharpen.mp4"
        )

    @video_1.command(
        name="contrast",
        description="Change video contrast"
    )
    async def contrast(
        self,
        interaction: Interaction,
        amount: float = 1.5,
        media: discord.Attachment = None,
        url: str = None
    ):
        amount = max(
            0,
            min(
                amount,
                5
            )
        )

        await self.process(
            interaction,
            media,
            url,
            f"eq=contrast={amount}",
            f"Contrast Video 🌓 (Amount: {amount})",
            "contrast.mp4"
        )

    @video_1.command(
        name="destroy",
        description="Absolutely destroy a video"
    )
    async def destroy(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        effects = [
            "blur",
            "sharpen",
            "contrast",
            "colour",
            "brightness",
            "darkness",
            "pixelate",
            "noise",
            "invert"
        ]

        amount = random.randint(
            5,
            10
        )

        filters = []
        applied = []

        for _ in range(
            amount
        ):
            effect = random.choice(
                effects
            )

            if effect == "blur":
                value = random.randint(
                    1,
                    8
                )

                filters.append(
                    f"gblur=sigma={value}"
                )

                applied.append(
                    f"Blur ({value})"
                )

            elif effect == "sharpen":
                value = random.uniform(
                    0.5,
                    2.5
                )

                filters.append(
                    f"unsharp=5:5:{value}:5:5:0"
                )

                applied.append(
                    f"Sharpen ({round(value, 2)})"
                )

            elif effect == "contrast":
                value = random.uniform(
                    0.5,
                    3.5
                )

                filters.append(
                    f"eq=contrast={value}"
                )

                applied.append(
                    f"Contrast ({round(value, 2)})"
                )

            elif effect == "colour":
                value = random.uniform(
                    0,
                    4
                )

                filters.append(
                    f"eq=saturation={value}"
                )

                applied.append(
                    f"Colour ({round(value, 2)})"
                )

            elif effect == "brightness":
                value = random.uniform(
                    0.1,
                    0.8
                )

                filters.append(
                    f"eq=brightness={value}"
                )

                applied.append(
                    f"Brightness ({round(value, 2)})"
                )

            elif effect == "darkness":
                value = random.uniform(
                    -0.8,
                    -0.1
                )

                filters.append(
                    f"eq=brightness={value}"
                )

                applied.append(
                    f"Darkness ({round(abs(value), 2)})"
                )

            elif effect == "pixelate":
                value = random.randint(
                    4,
                    20
                )

                filters.append(
                    f"scale="
                    f"ceil(iw/{value}/2)*2:"
                    f"ceil(ih/{value}/2)*2:"
                    f"flags=neighbor,"
                    f"scale=iw*{value}:"
                    f"ih*{value}:"
                    f"flags=neighbor"
                )

                applied.append(
                    f"Pixelate ({value})"
                )

            elif effect == "noise":
                value = random.randint(
                    5,
                    30
                )

                filters.append(
                    f"noise=alls={value}:allf=t+u"
                )

                applied.append(
                    f"Noise ({value})"
                )

            elif effect == "invert":
                filters.append(
                    "negate"
                )

                applied.append(
                    "Invert"
                )

        await self.process(
            interaction,
            media,
            url,
            ",".join(
                filters
            ),
            "Video Destroyed 💀",
            "destroy.mp4",
            (
                f"Applied {len(applied)} random effects:\n"
                +
                "\n".join(
                    f"• {effect}"
                    for effect in applied[:10]
                )
            )
        )

    @video_1.command(
        name="rotate",
        description="Rotate a video"
    )
    async def rotate(
        self,
        interaction: Interaction,
        angle: float = 90.0,
        media: discord.Attachment = None,
        url: str = None,
        clockwise: bool = True
    ):
        angle = max(
            -360,
            min(
                angle,
                360
            )
        )

        actual_angle = (
            -angle
            if clockwise
            else angle
        )

        radians = (
            actual_angle *
            3.141592653589793 /
            180
        )

        await self.process(
            interaction,
            media,
            url,
            f"rotate={radians}:fillcolor=black",
            (
                "Rotate Video 🔄 "
                f"{'Clockwise' if clockwise else 'Counter-clockwise'} "
                f"(Angle: {abs(angle)})"
            ),
            "rotate.mp4"
        )

    @video_1.command(
        name="flip",
        description="Flip a video horizontally"
    )
    async def flip(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        await self.process(
            interaction,
            media,
            url,
            "hflip",
            "Flipped Video 🔄",
            "flipped.mp4"
        )

async def setup(bot):
    await bot.add_cog(
        Video(bot)
    )