from discord import app_commands, Interaction
from discord.ext import commands
import discord
import aiohttp
from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageFont, ImageDraw
from pilmoji import Pilmoji
import io
import textwrap
import os
import zipfile
import shutil
import tempfile
import asyncio
import random
import math

from cogs.theming import get_fail_colour, get_success_colour


class Video(commands.GroupCog, group_name="video"):
    video_1 = app_commands.Group(
        name="1",
        description="Video - page 1"
    )

    MAX_DOWNLOAD_SIZE = 50 * 1024 * 1024
    MAX_OUTPUT_SIZE = 7 * 1024 * 1024
    MAX_VIDEO_DURATION = 20
    MAX_VIDEO_WIDTH = 960
    MAX_VIDEO_HEIGHT = 540
    MAX_VIDEO_FPS = 15
    MAX_FRAMES = 180
    MAX_GIF_FRAMES = 40
    MAX_BOOMERANG_FRAMES = 60

    VIDEO_EXTENSIONS = {
        ".mp4",
        ".mov",
        ".webm",
        ".mkv",
        ".avi",
        ".m4v",
        ".wmv",
        ".flv",
        ".3gp",
        ".mpeg",
        ".mpg",
        ".ts"
    }

    def __init__(self, bot):
        self.bot = bot
        self.video_lock = asyncio.Semaphore(1)

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

    async def get_media(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        if media:
            return media, None

        if url:
            return None, url.strip()

        if interaction.message and interaction.message.reference:
            try:
                replied = await interaction.channel.fetch_message(
                    interaction.message.reference.message_id
                )

                if replied.attachments:
                    return replied.attachments[0], None

            except Exception as e:
                print(f"[MEDIA REPLY] {e}")

        try:
            async for message in interaction.channel.history(limit=20):
                if message.attachments:
                    return message.attachments[0], None
        except Exception as e:
            print(f"[MEDIA HISTORY] {e}")

        return None, None

    def get_extension(
        self,
        media: discord.Attachment = None,
        media_url: str = None,
        path: str = None
    ):
        if media and media.filename:
            extension = os.path.splitext(
                media.filename.lower()
            )[1]

            if extension:
                return extension

        if media_url:
            clean_url = media_url.split("?", 1)[0].split("#", 1)[0]
            extension = os.path.splitext(clean_url.lower())[1]

            if extension in self.VIDEO_EXTENSIONS:
                return extension

        if path:
            extension = os.path.splitext(path.lower())[1]

            if extension:
                return extension

        return ".mp4"

    def is_video(
        self,
        extension: str
    ):
        return extension.lower() in self.VIDEO_EXTENSIONS

    async def download_media(
        self,
        media: discord.Attachment = None,
        media_url: str = None,
        output_path: str = None
    ):
        if not media and not media_url:
            return False, "No media was provided."

        try:
            if media:
                if media.size and media.size > self.MAX_DOWNLOAD_SIZE:
                    return False, (
                        "That file is too large.\n\n"
                        "The maximum allowed file size is **50 MB**."
                    )

                source_url = media.url

            else:
                source_url = media_url

            timeout = aiohttp.ClientTimeout(
                total=90,
                connect=20,
                sock_read=60
            )

            headers = {
                "User-Agent": "Clanker/1.0"
            }

            async with aiohttp.ClientSession(
                timeout=timeout,
                headers=headers
            ) as session:

                async with session.get(
                    source_url,
                    allow_redirects=True
                ) as response:

                    if response.status != 200:
                        print(
                            f"[MEDIA DOWNLOAD] HTTP {response.status} "
                            f"for {source_url}"
                        )

                        return False, (
                            f"Failed to download the media "
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
                        except ValueError:
                            pass

                    total = 0

                    with open(output_path, "wb") as file:
                        async for chunk in response.content.iter_chunked(
                            1024 * 256
                        ):
                            if not chunk:
                                continue

                            total += len(chunk)

                            if total > self.MAX_DOWNLOAD_SIZE:
                                try:
                                    os.remove(output_path)
                                except OSError:
                                    pass

                                return False, (
                                    "That file is too large.\n\n"
                                    "The maximum allowed file size is **50 MB**."
                                )

                            file.write(chunk)

            if not os.path.exists(output_path):
                return False, "Failed to download the media."

            size = os.path.getsize(output_path)

            print(
                f"[MEDIA DOWNLOAD] {size:,} bytes -> {output_path}"
            )

            if size == 0:
                return False, "The downloaded file was empty."

            return True, None

        except asyncio.TimeoutError:
            print("[MEDIA DOWNLOAD] Request timed out.")
            return False, "The media download timed out."

        except aiohttp.ClientError as e:
            print(f"[MEDIA DOWNLOAD] {e}")
            return False, "Failed to download the media."

        except Exception as e:
            print(f"[MEDIA DOWNLOAD] {type(e).__name__}: {e}")
            return False, "Failed to download the media."

    async def run_process(
        self,
        command,
        stdin=None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    ):
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdin=stdin,
                stdout=stdout,
                stderr=stderr
            )

            stdout_data, stderr_data = await process.communicate()

            stdout_text = (
                stdout_data.decode(
                    errors="replace"
                )
                if stdout_data
                else ""
            )

            stderr_text = (
                stderr_data.decode(
                    errors="replace"
                )
                if stderr_data
                else ""
            )

            return process.returncode, stdout_text, stderr_text

        except FileNotFoundError as e:
            print(
                f"[PROCESS] Executable not found: {command[0]}"
            )

            return -1, "", str(e)

        except Exception as e:
            print(
                f"[PROCESS] {type(e).__name__}: {e}"
            )

            return -1, "", str(e)

    async def get_video_info(
        self,
        input_path: str
    ):
        if not os.path.exists(input_path):
            print(
                f"[FFPROBE] File does not exist: {input_path}"
            )
            return None

        file_size = os.path.getsize(input_path)

        print(
            f"[FFPROBE] Checking {input_path} "
            f"({file_size:,} bytes)"
        )

        command = [
            "ffprobe",
            "-hide_banner",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=codec_name,width,height,r_frame_rate,avg_frame_rate",
            "-show_entries",
            "format=duration,format_name",
            "-of",
            "default=noprint_wrappers=1",
            input_path
        ]

        returncode, stdout, stderr = await self.run_process(
            command
        )

        print(
            f"[FFPROBE] Return code: {returncode}"
        )

        if stdout:
            print(
                f"[FFPROBE STDOUT]\n{stdout}"
            )

        if stderr:
            print(
                f"[FFPROBE STDERR]\n{stderr}"
            )

        if returncode != 0:
            return None

        data = {}

        for line in stdout.splitlines():
            if "=" not in line:
                continue

            key, value = line.split(
                "=",
                1
            )

            data[key.strip()] = value.strip()

        try:
            duration = float(
                data.get(
                    "duration",
                    "0"
                )
            )
        except ValueError:
            duration = 0

        try:
            width = int(
                data.get(
                    "width",
                    "0"
                )
            )
        except ValueError:
            width = 0

        try:
            height = int(
                data.get(
                    "height",
                    "0"
                )
            )
        except ValueError:
            height = 0

        fps = 0

        fps_value = data.get(
            "avg_frame_rate"
        )

        if not fps_value or fps_value == "0/0":
            fps_value = data.get(
                "r_frame_rate"
            )

        if fps_value:
            try:
                if "/" in fps_value:
                    numerator, denominator = fps_value.split(
                        "/",
                        1
                    )

                    denominator = float(
                        denominator
                    )

                    if denominator != 0:
                        fps = float(numerator) / denominator
                else:
                    fps = float(
                        fps_value
                    )
            except Exception:
                fps = 0

        codec = data.get(
            "codec_name",
            ""
        )

        format_name = data.get(
            "format_name",
            ""
        )

        if not width or not height:
            return None

        if not duration or duration <= 0:
            return None

        return {
            "duration": duration,
            "width": width,
            "height": height,
            "fps": fps,
            "codec": codec,
            "format": format_name
        }

    async def validate_video(
        self,
        input_path: str
    ):
        info = await self.get_video_info(
            input_path
        )

        if not info:
            return False, "Invalid or unsupported video."

        print(
            "[VIDEO INFO] "
            f"duration={info['duration']:.3f}s "
            f"resolution={info['width']}x{info['height']} "
            f"fps={info['fps']:.3f} "
            f"codec={info['codec']} "
            f"format={info['format']}"
        )

        if info["duration"] > self.MAX_VIDEO_DURATION:
            return False, (
                "That video is too long.\n\n"
                f"Videos are limited to **{self.MAX_VIDEO_DURATION} seconds**."
            )

        if info["width"] <= 0 or info["height"] <= 0:
            return False, "Couldn't determine the video resolution."

        if info["width"] > 3840 or info["height"] > 2160:
            return False, (
                "That video has an unsupported resolution.\n\n"
                "Videos above **3840×2160** aren't supported."
            )

        return True, None

    async def extract_video_frames(
        self,
        input_path: str,
        output_dir: str,
        max_frames: int
    ):
        os.makedirs(
            output_dir,
            exist_ok=True
        )

        output_pattern = os.path.join(
            output_dir,
            "frame_%04d.jpg"
        )

        command = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            input_path,
            "-vf",
            (
                f"fps={self.MAX_VIDEO_FPS},"
                f"scale={self.MAX_VIDEO_WIDTH}:{self.MAX_VIDEO_HEIGHT}:"
                "force_original_aspect_ratio=decrease,"
                "pad=ceil(iw/2)*2:ceil(ih/2)*2"
            ),
            "-frames:v",
            str(max_frames),
            "-q:v",
            "4",
            output_pattern
        ]

        returncode, stdout, stderr = await self.run_process(
            command,
            stdout=asyncio.subprocess.DEVNULL
        )

        if returncode != 0:
            print(
                f"[FFMPEG EXTRACT ERROR]\n{stderr}"
            )
            return False

        frames = [
            filename
            for filename in os.listdir(output_dir)
            if filename.lower().endswith(".jpg")
        ]

        return len(frames) > 0

    async def encode_frames_to_video(
        self,
        frames_dir: str,
        output_path: str,
        fps: float = 15
    ):
        input_pattern = os.path.join(
            frames_dir,
            "frame_%04d.jpg"
        )

        fps = max(
            1,
            min(
                fps,
                self.MAX_VIDEO_FPS
            )
        )

        command = [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-framerate",
            str(fps),
            "-i",
            input_pattern,
            "-vf",
            "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "28",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            "-an",
            output_path
        ]

        returncode, stdout, stderr = await self.run_process(
            command,
            stdout=asyncio.subprocess.DEVNULL
        )

        if returncode != 0:
            print(
                f"[FFMPEG ENCODE ERROR]\n{stderr}"
            )
            return False

        if not os.path.exists(output_path):
            return False

        output_size = os.path.getsize(
            output_path
        )

        print(
            f"[VIDEO OUTPUT] {output_size:,} bytes"
        )

        if output_size > self.MAX_OUTPUT_SIZE:
            try:
                os.remove(output_path)
            except OSError:
                pass

            return False

        return True

    async def process_video_frames(
        self,
        input_path: str,
        output_path: str,
        processor
    ):
        async with self.video_lock:
            temp_dir = tempfile.mkdtemp()

            try:
                input_frames = os.path.join(
                    temp_dir,
                    "input"
                )

                output_frames = os.path.join(
                    temp_dir,
                    "output"
                )

                os.makedirs(
                    input_frames,
                    exist_ok=True
                )

                os.makedirs(
                    output_frames,
                    exist_ok=True
                )

                success = await self.extract_video_frames(
                    input_path,
                    input_frames,
                    self.MAX_FRAMES
                )

                if not success:
                    return False

                frame_files = sorted(
                    filename
                    for filename in os.listdir(input_frames)
                    if filename.lower().endswith(".jpg")
                )

                if not frame_files:
                    return False

                for index, filename in enumerate(frame_files):
                    input_frame = None
                    output_frame = None

                    try:
                        input_frame = Image.open(
                            os.path.join(
                                input_frames,
                                filename
                            )
                        ).convert("RGB")

                        output_frame = processor(
                            input_frame
                        )

                        if not isinstance(
                            output_frame,
                            Image.Image
                        ):
                            return False

                        output_frame = output_frame.convert(
                            "RGB"
                        )

                        output_frame.save(
                            os.path.join(
                                output_frames,
                                f"frame_{index + 1:04d}.jpg"
                            ),
                            "JPEG",
                            quality=86,
                            optimize=False
                        )

                    finally:
                        if input_frame:
                            input_frame.close()

                        if output_frame:
                            output_frame.close()

                info = await self.get_video_info(
                    input_path
                )

                fps = self.MAX_VIDEO_FPS

                if info and info["fps"] > 0:
                    fps = min(
                        info["fps"],
                        self.MAX_VIDEO_FPS
                    )

                return await self.encode_frames_to_video(
                    output_frames,
                    output_path,
                    fps
                )

            finally:
                shutil.rmtree(
                    temp_dir,
                    ignore_errors=True
                )

    async def process_effect(
        self,
        interaction: Interaction,
        media: discord.Attachment,
        url: str,
        processor,
        title: str,
        filename: str,
        description: str = None
    ):
        await interaction.response.defer()

        attachment, media_url = await self.get_media(
            interaction,
            media,
            url
        )

        if not attachment and not media_url:
            return await self.send_error(
                interaction,
                "Missing Video ⚠️",
                "Upload, reply, or provide a video URL."
            )

        temp_dir = tempfile.mkdtemp()

        try:
            extension = self.get_extension(
                attachment,
                media_url,
                None
            )

            input_path = os.path.join(
                temp_dir,
                f"input{extension}"
            )

            success, error = await self.download_media(
                attachment,
                media_url,
                input_path
            )

            if not success:
                return await self.send_error(
                    interaction,
                    "Download Error 🚫",
                    error
                )

            valid, error = await self.validate_video(
                input_path
            )

            if not valid:
                return await self.send_error(
                    interaction,
                    "Video Rejected 🚫",
                    error
                )

            output_path = os.path.join(
                temp_dir,
                filename
            )

            success = await self.process_video_frames(
                input_path,
                output_path,
                processor
            )

            if not success:
                return await self.send_error(
                    interaction,
                    "Processing Error 🚫",
                    "I couldn't process that video."
                )

            embed = discord.Embed(
                title=title,
                description=description or "",
                color=get_success_colour()
            )

            await interaction.followup.send(
                embed=embed,
                file=discord.File(
                    output_path,
                    filename=filename
                )
            )

        finally:
            shutil.rmtree(
                temp_dir,
                ignore_errors=True
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
        def processor(img):
            return ImageOps.invert(
                img.convert("RGB")
            )

        await self.process_effect(
            interaction,
            media,
            url,
            processor,
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
        def processor(img):
            return ImageOps.grayscale(
                img
            ).convert("RGB")

        await self.process_effect(
            interaction,
            media,
            url,
            processor,
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
        def processor(img):
            result = img.convert(
                "RGB"
            )

            result = ImageEnhance.Contrast(
                result
            ).enhance(
                2.0
            )

            result = ImageEnhance.Color(
                result
            ).enhance(
                3.0
            )

            return result.filter(
                ImageFilter.UnsharpMask(
                    radius=2,
                    percent=150
                )
            )

        await self.process_effect(
            interaction,
            media,
            url,
            processor,
            "Deepfried Video 💥",
            "deepfry.mp4"
        )

    @video_1.command(
        name="blur",
        description="Blur a video"
    )
    @app_commands.describe(
        amount="Blur amount"
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

        def processor(img):
            return img.filter(
                ImageFilter.GaussianBlur(
                    radius=amount
                )
            ).convert("RGB")

        await self.process_effect(
            interaction,
            media,
            url,
            processor,
            f"Blurred Video (Amount: {amount}) 💨",
            "blur.mp4"
        )

    @video_1.command(
        name="bloom",
        description="Add bloom effect to a video"
    )
    @app_commands.describe(
        amount="Bloom amount"
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

        def processor(img):
            base = img.convert(
                "RGB"
            )

            bright = ImageEnhance.Brightness(
                base
            ).enhance(
                amount
            )

            blurred = bright.filter(
                ImageFilter.GaussianBlur(
                    radius=5
                )
            )

            return Image.blend(
                base,
                blurred,
                min(
                    0.8,
                    max(
                        0.05,
                        (amount - 0.1) / 3
                    )
                )
            ).convert("RGB")

        await self.process_effect(
            interaction,
            media,
            url,
            processor,
            f"Bloom Video (Amount: {amount}) ✨",
            "bloom.mp4"
        )

    @video_1.command(
        name="pixelate",
        description="Pixelate a video"
    )
    @app_commands.describe(
        amount="Pixelation amount"
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

        def processor(img):
            width = max(
                1,
                img.width // amount
            )

            height = max(
                1,
                img.height // amount
            )

            small = img.resize(
                (
                    width,
                    height
                ),
                Image.Resampling.NEAREST
            )

            return small.resize(
                img.size,
                Image.Resampling.NEAREST
            ).convert("RGB")

        await self.process_effect(
            interaction,
            media,
            url,
            processor,
            f"Pixelated Video (Amount: {amount}) 🟫",
            "pixelate.mp4"
        )

    @video_1.command(
        name="brighten",
        description="Brighten a video"
    )
    @app_commands.describe(
        amount="Brightness level"
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

        def processor(img):
            return ImageEnhance.Brightness(
                img.convert("RGB")
            ).enhance(
                1 + amount * 0.2
            )

        await self.process_effect(
            interaction,
            media,
            url,
            processor,
            f"Brightened Video ☀️ (Level: {amount})",
            "brighten.mp4"
        )

    @video_1.command(
        name="darken",
        description="Darken a video"
    )
    @app_commands.describe(
        amount="Darkness level"
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

        def processor(img):
            return ImageEnhance.Brightness(
                img.convert("RGB")
            ).enhance(
                max(
                    0,
                    1 - amount * 0.2
                )
            )

        await self.process_effect(
            interaction,
            media,
            url,
            processor,
            f"Darkened Video 🌑 (Level: {amount})",
            "darken.mp4"
        )

    @video_1.command(
        name="sharpen",
        description="Sharpen a video"
    )
    @app_commands.describe(
        amount="Sharpen amount"
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

        def processor(img):
            return img.convert(
                "RGB"
            ).filter(
                ImageFilter.UnsharpMask(
                    radius=2,
                    percent=100 + amount * 50,
                    threshold=3
                )
            )

        await self.process_effect(
            interaction,
            media,
            url,
            processor,
            f"Sharpened Video 🔪 (Amount: {amount})",
            "sharpen.mp4"
        )

    @video_1.command(
        name="contrast",
        description="Change the contrast of a video"
    )
    @app_commands.describe(
        amount="Contrast amount"
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

        def processor(img):
            return ImageEnhance.Contrast(
                img.convert("RGB")
            ).enhance(
                amount
            )

        await self.process_effect(
            interaction,
            media,
            url,
            processor,
            f"Contrast Video 🌓 (Amount: {amount})",
            "contrast.mp4"
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

        attachment, media_url = await self.get_media(
            interaction,
            media,
            url
        )

        if not attachment and not media_url:
            return await self.send_error(
                interaction,
                "Missing Video ⚠️",
                "Upload, reply, or provide a video URL."
            )

        temp_dir = tempfile.mkdtemp()

        try:
            extension = self.get_extension(
                attachment,
                media_url,
                None
            )

            input_path = os.path.join(
                temp_dir,
                f"input{extension}"
            )

            output_path = os.path.join(
                temp_dir,
                "video.gif"
            )

            success, error = await self.download_media(
                attachment,
                media_url,
                input_path
            )

            if not success:
                return await self.send_error(
                    interaction,
                    "Download Error 🚫",
                    error
                )

            valid, error = await self.validate_video(
                input_path
            )

            if not valid:
                return await self.send_error(
                    interaction,
                    "Video Rejected 🚫",
                    error
                )

            command = [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                input_path,
                "-t",
                str(self.MAX_VIDEO_DURATION),
                "-vf",
                (
                    f"fps={min(self.MAX_VIDEO_FPS, 10)},"
                    "scale=640:640:"
                    "force_original_aspect_ratio=decrease,"
                    "pad=640:640:(ow-iw)/2:(oh-ih)/2,"
                    "split[s0][s1];"
                    "[s0]palettegen=stats_mode=diff[p];"
                    "[s1][p]paletteuse=dither=sierra2_4a"
                ),
                "-frames:v",
                str(self.MAX_GIF_FRAMES),
                "-loop",
                "0",
                output_path
            ]

            returncode, stdout, stderr = await self.run_process(
                command,
                stdout=asyncio.subprocess.DEVNULL
            )

            if returncode != 0:
                print(
                    f"[GIF ERROR]\n{stderr}"
                )

                return await self.send_error(
                    interaction,
                    "Conversion Error 🚫",
                    "I couldn't convert that video to a GIF."
                )

            if not os.path.exists(output_path):
                return await self.send_error(
                    interaction,
                    "Conversion Error 🚫",
                    "No GIF was created."
                )

            if os.path.getsize(output_path) > self.MAX_OUTPUT_SIZE:
                return await self.send_error(
                    interaction,
                    "Output Too Large 🚫",
                    "The generated GIF is too large."
                )

            embed = discord.Embed(
                title="Video → GIF 🖼️",
                description=(
                    "Converted successfully.\n"
                    "Animated GIFs are limited to 256 colours."
                ),
                color=get_success_colour()
            )

            embed.set_image(
                url="attachment://video.gif"
            )

            await interaction.followup.send(
                embed=embed,
                file=discord.File(
                    output_path,
                    filename="video.gif"
                )
            )

        finally:
            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )

    @video_1.command(
        name="caption",
        description="Add a caption to a video"
    )
    @app_commands.describe(
        media="The video",
        text="Caption text",
        url="A direct video URL"
    )
    async def caption(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        text: str = None,
        url: str = None
    ):
        if not text:
            return await self.send_error(
                interaction,
                "Missing Text ⚠️",
                "Please provide a caption."
            )

        await interaction.response.defer()

        attachment, media_url = await self.get_media(
            interaction,
            media,
            url
        )

        if not attachment and not media_url:
            return await self.send_error(
                interaction,
                "Missing Video ⚠️",
                "Upload, reply, or provide a video URL."
            )

        temp_dir = tempfile.mkdtemp()

        try:
            extension = self.get_extension(
                attachment,
                media_url,
                None
            )

            input_path = os.path.join(
                temp_dir,
                f"input{extension}"
            )

            frames_dir = os.path.join(
                temp_dir,
                "frames"
            )

            output_dir = os.path.join(
                temp_dir,
                "output"
            )

            output_path = os.path.join(
                temp_dir,
                "caption.mp4"
            )

            os.makedirs(
                frames_dir,
                exist_ok=True
            )

            os.makedirs(
                output_dir,
                exist_ok=True
            )

            success, error = await self.download_media(
                attachment,
                media_url,
                input_path
            )

            if not success:
                return await self.send_error(
                    interaction,
                    "Download Error 🚫",
                    error
                )

            valid, error = await self.validate_video(
                input_path
            )

            if not valid:
                return await self.send_error(
                    interaction,
                    "Video Rejected 🚫",
                    error
                )

            success = await self.extract_video_frames(
                input_path,
                frames_dir,
                self.MAX_FRAMES
            )

            if not success:
                return await self.send_error(
                    interaction,
                    "Processing Error 🚫",
                    "Couldn't extract the video frames."
                )

            frame_files = sorted(
                filename
                for filename in os.listdir(frames_dir)
                if filename.lower().endswith(".jpg")
            )

            for index, frame_file in enumerate(frame_files):
                frame = None
                output = None

                try:
                    frame = Image.open(
                        os.path.join(
                            frames_dir,
                            frame_file
                        )
                    ).convert("RGBA")

                    width, height = frame.size

                    font_size = max(
                        24,
                        min(
                            64,
                            width // 10
                        )
                    )

                    font = ImageFont.truetype(
                        "C:/Windows/Fonts/impact.ttf",
                        font_size
                    )

                    chars_per_line = max(
                        8,
                        width // max(
                            1,
                            font_size // 2
                        )
                    )

                    wrapped = textwrap.fill(
                        text,
                        width=chars_per_line
                    )

                    draw = ImageDraw.Draw(
                        frame
                    )

                    bbox = draw.multiline_textbbox(
                        (0, 0),
                        wrapped,
                        font=font,
                        align="center"
                    )

                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]

                    padding = font_size // 2

                    caption_height = (
                        text_height +
                        padding * 2
                    )

                    if caption_height % 2:
                        caption_height += 1

                    output = Image.new(
                        "RGBA",
                        (
                            width,
                            height + caption_height
                        ),
                        "white"
                    )

                    output.paste(
                        frame,
                        (0, caption_height)
                    )

                    x = (
                        width -
                        text_width
                    ) / 2

                    y = (
                        (caption_height - text_height) / 2
                    ) - bbox[1]

                    with Pilmoji(output) as pilmoji:
                        pilmoji.text(
                            (x, y),
                            wrapped,
                            fill="black",
                            font=font,
                            align="center"
                        )

                    output.convert(
                        "RGB"
                    ).save(
                        os.path.join(
                            output_dir,
                            f"frame_{index + 1:04d}.jpg"
                        ),
                        "JPEG",
                        quality=86
                    )

                finally:
                    if frame:
                        frame.close()

                    if output:
                        output.close()

            info = await self.get_video_info(
                input_path
            )

            fps = self.MAX_VIDEO_FPS

            if info and info["fps"] > 0:
                fps = min(
                    info["fps"],
                    self.MAX_VIDEO_FPS
                )

            success = await self.encode_frames_to_video(
                output_dir,
                output_path,
                fps
            )

            if not success:
                return await self.send_error(
                    interaction,
                    "Encoding Error 🚫",
                    "Couldn't create the processed video."
                )

            embed = discord.Embed(
                title="Caption 📝",
                color=get_success_colour()
            )

            await interaction.followup.send(
                embed=embed,
                file=discord.File(
                    output_path,
                    filename="caption.mp4"
                )
            )

        finally:
            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )

    @video_1.command(
        name="frames",
        description="Extract frames from a video"
    )
    async def frames(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        await interaction.response.defer()

        attachment, media_url = await self.get_media(
            interaction,
            media,
            url
        )

        if not attachment and not media_url:
            return await self.send_error(
                interaction,
                "Missing Video ⚠️",
                "Upload a video or provide a URL."
            )

        temp_dir = tempfile.mkdtemp()

        try:
            extension = self.get_extension(
                attachment,
                media_url,
                None
            )

            input_path = os.path.join(
                temp_dir,
                f"input{extension}"
            )

            output_dir = os.path.join(
                temp_dir,
                "frames"
            )

            os.makedirs(
                output_dir,
                exist_ok=True
            )

            success, error = await self.download_media(
                attachment,
                media_url,
                input_path
            )

            if not success:
                return await self.send_error(
                    interaction,
                    "Download Error 🚫",
                    error
                )

            valid, error = await self.validate_video(
                input_path
            )

            if not valid:
                return await self.send_error(
                    interaction,
                    "Video Rejected 🚫",
                    error
                )

            success = await self.extract_video_frames(
                input_path,
                output_dir,
                self.MAX_FRAMES
            )

            if not success:
                return await self.send_error(
                    interaction,
                    "Extraction Error 🚫",
                    "Couldn't extract frames from that video."
                )

            frame_files = sorted(
                filename
                for filename in os.listdir(output_dir)
                if filename.lower().endswith(".jpg")
            )

            if not frame_files:
                return await self.send_error(
                    interaction,
                    "Extraction Error 🚫",
                    "No frames could be extracted."
                )

            zip_path = os.path.join(
                temp_dir,
                "frames.zip"
            )

            with zipfile.ZipFile(
                zip_path,
                "w",
                compression=zipfile.ZIP_DEFLATED
            ) as zipf:
                for frame in frame_files:
                    zipf.write(
                        os.path.join(
                            output_dir,
                            frame
                        ),
                        frame
                    )

            if os.path.getsize(zip_path) > self.MAX_OUTPUT_SIZE:
                return await self.send_error(
                    interaction,
                    "Output Too Large 🚫",
                    "The generated frame archive is too large."
                )

            embed = discord.Embed(
                title="📦 Extracted Frames",
                description=(
                    f"Successfully extracted "
                    f"**{len(frame_files)} frames**!"
                ),
                color=get_success_colour()
            )

            if len(frame_files) >= self.MAX_FRAMES:
                embed.set_footer(
                    text=(
                        f"Limited to the first "
                        f"{self.MAX_FRAMES} frames."
                    )
                )

            await interaction.followup.send(
                embed=embed,
                file=discord.File(
                    zip_path,
                    filename="frames.zip"
                )
            )

        finally:
            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )

    @video_1.command(
        name="boomerang",
        description="Create a boomerang from a video"
    )
    async def boomerang(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        await interaction.response.defer()

        attachment, media_url = await self.get_media(
            interaction,
            media,
            url
        )

        if not attachment and not media_url:
            return await self.send_error(
                interaction,
                "Missing Video ⚠️",
                "Upload a video or provide a URL."
            )

        temp_dir = tempfile.mkdtemp()

        try:
            extension = self.get_extension(
                attachment,
                media_url,
                None
            )

            input_path = os.path.join(
                temp_dir,
                f"input{extension}"
            )

            frames_dir = os.path.join(
                temp_dir,
                "frames"
            )

            output_path = os.path.join(
                temp_dir,
                "boomerang.gif"
            )

            os.makedirs(
                frames_dir,
                exist_ok=True
            )

            success, error = await self.download_media(
                attachment,
                media_url,
                input_path
            )

            if not success:
                return await self.send_error(
                    interaction,
                    "Download Error 🚫",
                    error
                )

            valid, error = await self.validate_video(
                input_path
            )

            if not valid:
                return await self.send_error(
                    interaction,
                    "Video Rejected 🚫",
                    error
                )

            info = await self.get_video_info(
                input_path
            )

            duration = 100

            if info and info["fps"] > 0:
                duration = int(
                    1000 /
                    min(
                        info["fps"],
                        self.MAX_VIDEO_FPS
                    )
                )

            success = await self.extract_video_frames(
                input_path,
                frames_dir,
                self.MAX_BOOMERANG_FRAMES
            )

            if not success:
                return await self.send_error(
                    interaction,
                    "Extraction Error 🚫",
                    "Couldn't extract any video frames."
                )

            frame_files = sorted(
                filename
                for filename in os.listdir(frames_dir)
                if filename.lower().endswith(".jpg")
            )

            frames = []

            try:
                for frame_file in frame_files:
                    frame = Image.open(
                        os.path.join(
                            frames_dir,
                            frame_file
                        )
                    ).convert("RGB")

                    frames.append(
                        frame.copy()
                    )

                    frame.close()

                if not frames:
                    return await self.send_error(
                        interaction,
                        "Extraction Error 🚫",
                        "Couldn't extract any frames."
                    )

                boomerang_frames = (
                    frames +
                    frames[-2::-1]
                )

                boomerang_frames[0].save(
                    output_path,
                    format="GIF",
                    save_all=True,
                    append_images=boomerang_frames[1:],
                    duration=duration,
                    loop=0,
                    disposal=2
                )

            finally:
                for frame in frames:
                    frame.close()

            if os.path.getsize(output_path) > self.MAX_OUTPUT_SIZE:
                return await self.send_error(
                    interaction,
                    "Output Too Large 🚫",
                    "The generated boomerang is too large."
                )

            embed = discord.Embed(
                title="🔁 Boomerang Created",
                description=(
                    f"Created a boomerang with "
                    f"**{len(boomerang_frames)} frames**!"
                ),
                color=get_success_colour()
            )

            if len(frames) >= self.MAX_BOOMERANG_FRAMES:
                embed.set_footer(
                    text=(
                        f"Limited to the first "
                        f"{self.MAX_BOOMERANG_FRAMES} frames."
                    )
                )

            embed.set_image(
                url="attachment://boomerang.gif"
            )

            await interaction.followup.send(
                embed=embed,
                file=discord.File(
                    output_path,
                    filename="boomerang.gif"
                )
            )

        finally:
            shutil.rmtree(
                temp_dir,
                ignore_errors=True
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
            9
        )

        selected = random.sample(
            effects,
            min(
                amount,
                len(effects)
            )
        )

        def processor(img):
            img = img.convert(
                "RGB"
            )

            for effect in selected:
                if effect == "blur":
                    img = img.filter(
                        ImageFilter.GaussianBlur(
                            random.randint(
                                1,
                                8
                            )
                        )
                    )

                elif effect == "sharpen":
                    img = img.filter(
                        ImageFilter.UnsharpMask(
                            radius=random.randint(
                                1,
                                4
                            ),
                            percent=random.randint(
                                100,
                                400
                            ),
                            threshold=random.randint(
                                1,
                                5
                            )
                        )
                    )

                elif effect == "contrast":
                    img = ImageEnhance.Contrast(
                        img
                    ).enhance(
                        random.uniform(
                            0.5,
                            4
                        )
                    )

                elif effect == "colour":
                    img = ImageEnhance.Color(
                        img
                    ).enhance(
                        random.uniform(
                            0,
                            5
                        )
                    )

                elif effect == "brightness":
                    img = ImageEnhance.Brightness(
                        img
                    ).enhance(
                        random.uniform(
                            0.2,
                            3
                        )
                    )

                elif effect == "darkness":
                    img = ImageEnhance.Brightness(
                        img
                    ).enhance(
                        random.uniform(
                            0.1,
                            0.8
                        )
                    )

                elif effect == "pixelate":
                    value = random.randint(
                        2,
                        20
                    )

                    small = img.resize(
                        (
                            max(
                                1,
                                img.width // value
                            ),
                            max(
                                1,
                                img.height // value
                            )
                        ),
                        Image.Resampling.NEAREST
                    )

                    img = small.resize(
                        img.size,
                        Image.Resampling.NEAREST
                    )

                elif effect == "noise":
                    noise = Image.effect_noise(
                        img.size,
                        random.randint(
                            20,
                            60
                        )
                    ).convert(
                        "RGB"
                    )

                    img = Image.blend(
                        img,
                        noise,
                        0.15
                    )

                elif effect == "invert":
                    img = ImageOps.invert(
                        img
                    )

            return img

        await self.process_effect(
            interaction,
            media,
            url,
            processor,
            "Video Destroyed 💀",
            "destroy.mp4",
            "Applied a random combination of effects."
        )

    @video_1.command(
        name="rotate",
        description="Change the rotation of a video"
    )
    @app_commands.describe(
        angle="Rotation angle",
        media="The video",
        url="A direct video URL",
        clockwise="Rotate clockwise"
    )
    async def rotate(
        self,
        interaction: Interaction,
        angle: float = 90.0,
        media: discord.Attachment = None,
        url: str = None,
        clockwise: bool = True
    ):
        if clockwise:
            actual_angle = -angle
            direction = "Clockwise"
        else:
            actual_angle = angle
            direction = "Counter-clockwise"

        def processor(img):
            return img.rotate(
                actual_angle,
                expand=False
            )

        await self.process_effect(
            interaction,
            media,
            url,
            processor,
            (
                f"Rotate Video 🔄 {direction} "
                f"(Angle: {abs(angle)})"
            ),
            "rotate.mp4"
        )

    @video_1.command(
        name="flip",
        description="Flip a video"
    )
    async def flip(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        def processor(img):
            return img.transpose(
                Image.Transpose.FLIP_LEFT_RIGHT
            )

        await self.process_effect(
            interaction,
            media,
            url,
            processor,
            "Flipped Video 🔄",
            "flipped.mp4"
        )

    @app_commands.command(
        name="globe",
        description="Project a video onto a spinning sphere"
    )
    @app_commands.describe(
        media="The video to wrap around the globe",
        url="A direct video URL"
    )
    async def globe(
        self,
        interaction: discord.Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        await interaction.response.defer()

        attachment, media_url = await self.get_media(
            interaction,
            media,
            url
        )

        if not attachment and not media_url:
            return await self.send_error(
                interaction,
                "Missing Video ⚠️",
                "Upload, reply, or provide a video URL."
            )

        temp_dir = tempfile.mkdtemp()

        try:
            extension = self.get_extension(
                attachment,
                media_url,
                None
            )

            input_path = os.path.join(
                temp_dir,
                f"input{extension}"
            )

            output_path = os.path.join(
                temp_dir,
                "globe.mp4"
            )

            success, error = await self.download_media(
                attachment,
                media_url,
                input_path
            )

            if not success:
                return await self.send_error(
                    interaction,
                    "Download Error 🚫",
                    error
                )

            valid, error = await self.validate_video(
                input_path
            )

            if not valid:
                return await self.send_error(
                    interaction,
                    "Video Rejected 🚫",
                    error
                )

            input_process = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                input_path,
                "-t",
                str(self.MAX_VIDEO_DURATION),
                "-vf",
                (
                    f"fps={self.MAX_VIDEO_FPS},"
                    "scale=512:256:"
                    "force_original_aspect_ratio=decrease,"
                    "pad=512:256:(ow-iw)/2:(oh-ih)/2"
                ),
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "pipe:1",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            encoder = await asyncio.create_subprocess_exec(
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgba",
                "-s",
                "256x256",
                "-r",
                str(self.MAX_VIDEO_FPS),
                "-i",
                "pipe:0",
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "28",
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
                "-an",
                output_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.PIPE
            )

            frame_size = (
                512 *
                256 *
                3
            )

            frame_number = 0

            try:
                while True:
                    raw_frame = await input_process.stdout.read(
                        frame_size
                    )

                    if not raw_frame:
                        break

                    if len(raw_frame) != frame_size:
                        print(
                            "[VIDEO GLOBE] Incomplete raw frame received."
                        )
                        break

                    texture = Image.frombytes(
                        "RGB",
                        (
                            512,
                            256
                        ),
                        raw_frame
                    )

                    rotation = (
                        frame_number /
                        self.MAX_VIDEO_FPS
                    ) * 0.35

                    globe_frame = self.render_globe(
                        texture,
                        256,
                        256,
                        rotation
                    )

                    try:
                        encoder.stdin.write(
                            globe_frame.tobytes()
                        )

                        await encoder.stdin.drain()

                    except (BrokenPipeError, ConnectionResetError):
                        break

                    finally:
                        texture.close()
                        globe_frame.close()

                    frame_number += 1

                    if frame_number >= self.MAX_FRAMES:
                        break

            finally:
                if encoder.stdin:
                    try:
                        encoder.stdin.close()
                    except Exception:
                        pass

            await input_process.wait()
            await encoder.wait()

            input_error = (
                await input_process.stderr.read()
            ).decode(
                errors="replace"
            )

            encoder_error = (
                await encoder.stderr.read()
            ).decode(
                errors="replace"
            )

            if input_process.returncode != 0:
                print(
                    f"[VIDEO GLOBE INPUT ERROR]\n{input_error}"
                )

                return await self.send_error(
                    interaction,
                    "Processing Error 🚫",
                    "FFmpeg couldn't decode that video."
                )

            if encoder.returncode != 0:
                print(
                    f"[VIDEO GLOBE ENCODER ERROR]\n{encoder_error}"
                )

                return await self.send_error(
                    interaction,
                    "Encoding Error 🚫",
                    "FFmpeg couldn't create the globe video."
                )

            if frame_number == 0:
                return await self.send_error(
                    interaction,
                    "Processing Error 🚫",
                    "No video frames could be processed."
                )

            if not os.path.exists(output_path):
                return await self.send_error(
                    interaction,
                    "Processing Error 🚫",
                    "No output video was created."
                )

            output_size = os.path.getsize(
                output_path
            )

            if output_size > self.MAX_OUTPUT_SIZE:
                return await self.send_error(
                    interaction,
                    "Output Too Large 🚫",
                    (
                        "The generated video is too large.\n\n"
                        f"The maximum output size is **"
                        f"{self.MAX_OUTPUT_SIZE // 1024 // 1024} MB**."
                    )
                )

            embed = discord.Embed(
                title="🌎 Video Globe",
                description=(
                    "Your video has been projected onto "
                    "a spinning globe."
                ),
                color=get_success_colour()
            )

            embed.add_field(
                name="🎥 Playback",
                value=(
                    "The original video plays while "
                    "the globe spins."
                ),
                inline=False
            )

            await interaction.followup.send(
                embed=embed,
                file=discord.File(
                    output_path,
                    filename="video-globe.mp4"
                )
            )

        except Exception as e:
            print(
                f"[VIDEO GLOBE] "
                f"{type(e).__name__}: {e}"
            )

            if interaction.response.is_done():
                await interaction.followup.send(
                    embed=discord.Embed(
                        title="🚫 Video Globe Failed",
                        description=(
                            "I couldn't create the "
                            "spinning video globe."
                        ),
                        color=get_fail_colour()
                    )
                )

        finally:
            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )

    @staticmethod
    def prepare_texture(image):
        width, height = image.size

        ratio = width / height

        if ratio < 2:
            new_width = int(
                height * 2
            )

            canvas = Image.new(
                "RGB",
                (
                    new_width,
                    height
                )
            )

            canvas.paste(
                image,
                (
                    (new_width - width) // 2,
                    0
                )
            )

            image = canvas

        elif ratio > 2:
            new_height = int(
                width / 2
            )

            canvas = Image.new(
                "RGB",
                (
                    width,
                    new_height
                )
            )

            canvas.paste(
                image,
                (
                    0,
                    (new_height - height) // 2
                )
            )

            image = canvas

        return image.resize(
            (
                512,
                256
            ),
            Image.Resampling.LANCZOS
        )

    @staticmethod
    def render_globe(
        texture,
        width,
        height,
        rotation
    ):
        frame = Image.new(
            "RGBA",
            (
                width,
                height
            ),
            (
                0,
                0,
                0,
                0
            )
        )

        pixels = frame.load()
        texture_pixels = texture.load()

        radius = width * 0.43

        center_x = width / 2
        center_y = height / 2

        for y in range(height):
            dy = (
                y -
                center_y
            ) / radius

            if abs(dy) > 1:
                continue

            for x in range(width):
                dx = (
                    x -
                    center_x
                ) / radius

                distance = (
                    dx * dx +
                    dy * dy
                )

                if distance > 1:
                    continue

                dz = math.sqrt(
                    1 -
                    distance
                )

                longitude = math.atan2(
                    dx,
                    dz
                )

                latitude = math.asin(
                    -dy
                )

                longitude += (
                    rotation *
                    math.tau
                )

                u = (
                    longitude /
                    math.tau +
                    0.5
                ) % 1.0

                v = (
                    0.5 -
                    latitude /
                    math.pi
                )

                tx = int(
                    u * 511
                ) % 512

                ty = max(
                    0,
                    min(
                        255,
                        int(
                            v * 255
                        )
                    )
                )

                r, g, b = texture_pixels[
                    tx,
                    ty
                ]

                light = (
                    0.45 +
                    0.55 *
                    max(
                        0,
                        dz
                    )
                )

                r = int(
                    r *
                    light
                )

                g = int(
                    g *
                    light
                )

                b = int(
                    b *
                    light
                )

                pixels[x, y] = (
                    r,
                    g,
                    b,
                    255
                )

        return frame

async def setup(bot):
    await bot.add_cog(
        Video(bot)
    )