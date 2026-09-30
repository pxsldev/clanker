from discord import app_commands, Interaction
from discord.ext import commands
import discord
import aiohttp
from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageFont, ImageDraw
from pilmoji import Pilmoji
import io
import textwrap
import os
import tempfile
import shutil
import random
from cogs.theming import get_fail_colour, get_success_colour
import math

class Images(commands.GroupCog, group_name="image"):

    image_1 = app_commands.Group(
        name="1",
        description="Images - page 1"
    )

    MAX_DOWNLOAD_SIZE = 50 * 1024 * 1024
    MAX_IMAGE_PIXELS = 12_000_000
    MAX_IMAGE_SIDE = 3000

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
        media_url = None

        if media:
            media_url = media.url

        elif url:
            media_url = url

        elif interaction.message and interaction.message.reference:
            try:
                replied = await interaction.channel.fetch_message(
                    interaction.message.reference.message_id
                )

                if replied.attachments:
                    media_url = replied.attachments[0].url

            except:
                pass

        if not media_url:
            async for message in interaction.channel.history(
                limit=20
            ):
                if message.attachments:
                    media_url = message.attachments[0].url
                    break

        return media_url

    async def download_media(
        self,
        media_url: str,
        output_path: str
    ):
        try:
            timeout = aiohttp.ClientTimeout(
                total=60
            )

            async with aiohttp.ClientSession(
                timeout=timeout
            ) as session:

                async with session.get(
                    media_url,
                    allow_redirects=True
                ) as response:

                    if response.status != 200:
                        return False, "Failed to download the media."

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
                        except:
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
                                file.close()

                                try:
                                    os.remove(output_path)
                                except:
                                    pass

                                return False, (
                                    "That file is too large.\n\n"
                                    "The maximum allowed file size is **50 MB**."
                                )

                            file.write(chunk)

            return True, None

        except aiohttp.ClientError:
            return False, "Failed to download the media."

        except Exception:
            return False, "Failed to download the media."

    async def load_image(
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
                "Missing Image ⚠️",
                "Upload, reply, or provide a URL."
            )

        temp_dir = tempfile.mkdtemp()

        try:
            input_path = os.path.join(
                temp_dir,
                "input"
            )

            success, error = await self.download_media(
                media_url,
                input_path
            )

            if not success:
                return (
                    None,
                    "Error 🚫",
                    error
                )

            try:
                img = Image.open(
                    input_path
                )

                img.load()

                if (
                    img.width * img.height
                    > self.MAX_IMAGE_PIXELS
                ):
                    return (
                        None,
                        "Image Too Large 🚫",
                        "That image has too many pixels."
                    )

                if (
                    img.width > self.MAX_IMAGE_SIDE
                    or img.height > self.MAX_IMAGE_SIDE
                ):
                    img.thumbnail(
                        (
                            self.MAX_IMAGE_SIDE,
                            self.MAX_IMAGE_SIDE
                        ),
                        Image.Resampling.LANCZOS
                    )

                result = img.copy()
                img.close()

                return result, None, None

            except Exception as e:
                print(e)

                return (
                    None,
                    "Invalid Image 🚫",
                    "I couldn't open that file as an image."
                )

        finally:
            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )

    async def send_image(
        self,
        interaction: Interaction,
        img: Image.Image,
        title: str,
        filename: str,
        desc: str = None
    ):
        buffer = io.BytesIO()

        img.save(
            buffer,
            format="PNG"
        )

        buffer.seek(0)

        file = discord.File(
            buffer,
            filename=filename
        )

        embed = discord.Embed(
            title=title,
            description=desc if desc else "",
            color=get_success_colour()
        )

        embed.set_image(
            url=f"attachment://{filename}"
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

    @image_1.command(
        name="invert",
        description="Invert an image"
    )
    async def invert(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        img, err_title, err_desc = await self.load_image(
            interaction,
            media,
            url
        )

        if not img:
            return await self.send_error(
                interaction,
                err_title,
                err_desc
            )

        img = ImageOps.invert(
            img.convert("RGB")
        )

        await self.send_image(
            interaction,
            img,
            "Inverted Image 🌀",
            "invert.png"
        )

        img.close()

    @image_1.command(
        name="greyscale",
        description="Convert an image to greyscale"
    )
    async def greyscale(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        img, err_title, err_desc = await self.load_image(
            interaction,
            media,
            url
        )

        if not img:
            return await self.send_error(
                interaction,
                err_title,
                err_desc
            )

        result = ImageOps.grayscale(
            img
        ).convert("RGB")

        await self.send_image(
            interaction,
            result,
            "Greyscale Image ⚪",
            "greyscale.png"
        )

        img.close()
        result.close()

    @image_1.command(
        name="deepfry",
        description="Deep fry an image"
    )
    async def deepfry(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        img, err_title, err_desc = await self.load_image(
            interaction,
            media,
            url
        )

        if not img:
            return await self.send_error(
                interaction,
                err_title,
                err_desc
            )

        result = img.convert("RGB")

        result = ImageEnhance.Contrast(
            result
        ).enhance(2.0)

        result = ImageEnhance.Color(
            result
        ).enhance(3.0)

        result = result.filter(
            ImageFilter.UnsharpMask(
                radius=2,
                percent=150
            )
        )

        await self.send_image(
            interaction,
            result,
            "Deepfried Image 💥",
            "deepfry.png"
        )

        img.close()
        result.close()

    @image_1.command(
        name="blur",
        description="Blur an image"
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
            min(amount, 25)
        )

        img, err_title, err_desc = await self.load_image(
            interaction,
            media,
            url
        )

        if not img:
            return await self.send_error(
                interaction,
                err_title,
                err_desc
            )

        result = img.filter(
            ImageFilter.GaussianBlur(
                radius=amount
            )
        ).convert("RGB")

        await self.send_image(
            interaction,
            result,
            f"Blurred Image (Amount: {amount}) 💨",
            "blur.png"
        )

        img.close()
        result.close()

    @image_1.command(
        name="bloom",
        description="Add bloom effect to an image"
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
            min(amount, 3.0)
        )

        img, err_title, err_desc = await self.load_image(
            interaction,
            media,
            url
        )

        if not img:
            return await self.send_error(
                interaction,
                err_title,
                err_desc
            )

        result = ImageEnhance.Brightness(
            img
        ).enhance(amount)

        result = result.filter(
            ImageFilter.GaussianBlur(
                radius=5
            )
        ).convert("RGB")

        await self.send_image(
            interaction,
            result,
            f"Bloom Image (Amount: {amount}) ✨",
            "bloom.png"
        )

        img.close()
        result.close()

    @image_1.command(
        name="pixelate",
        description="Pixelate an image"
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
            min(amount, 50)
        )

        img, err_title, err_desc = await self.load_image(
            interaction,
            media,
            url
        )

        if not img:
            return await self.send_error(
                interaction,
                err_title,
                err_desc
            )

        width = max(
            1,
            img.width // amount
        )

        height = max(
            1,
            img.height // amount
        )

        small = img.resize(
            (width, height),
            Image.Resampling.NEAREST
        )

        result = small.resize(
            img.size,
            Image.Resampling.NEAREST
        ).convert("RGB")

        await self.send_image(
            interaction,
            result,
            f"Pixelated Image (Amount: {amount}) 🟫",
            "pixelate.png"
        )

        img.close()
        small.close()
        result.close()

    @image_1.command(
        name="gif",
        description="Turn an image into a GIF"
    )
    async def gif(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        img, err_title, err_desc = await self.load_image(
            interaction,
            media,
            url
        )

        if not img:
            return await self.send_error(
                interaction,
                err_title,
                err_desc
            )

        buffer = io.BytesIO()

        img.convert(
            "RGBA"
        ).save(
            buffer,
            format="GIF",
            save_all=True,
            loop=0
        )

        buffer.seek(0)

        file = discord.File(
            buffer,
            filename="image.gif"
        )

        embed = discord.Embed(
            title="Image → GIF 🖼️",
            description="GIFs are limited to 256 colors - quality may drop ⚠️",
            color=get_success_colour()
        )

        embed.set_image(
            url="attachment://image.gif"
        )

        await interaction.response.send_message(
            embed=embed,
            file=file
        )

        img.close()

    @image_1.command(
        name="png",
        description="Turn an image into a PNG"
    )
    async def png(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        img, err_title, err_desc = await self.load_image(
            interaction,
            media,
            url
        )

        if not img:
            return await self.send_error(
                interaction,
                err_title,
                err_desc
            )

        result = img.convert("RGBA")

        await self.send_image(
            interaction,
            result,
            "Image → PNG 🖼️",
            "image.png",
            "Converted successfully."
        )

        img.close()
        result.close()

    @image_1.command(
        name="jpg",
        description="Turn an image into a JPG"
    )
    async def jpg(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        img, err_title, err_desc = await self.load_image(
            interaction,
            media,
            url
        )

        if not img:
            return await self.send_error(
                interaction,
                err_title,
                err_desc
            )

        if (
            img.mode in ("RGBA", "LA")
            or (
                img.mode == "P"
                and "transparency" in img.info
            )
        ):
            background = Image.new(
                "RGB",
                img.size,
                (255, 255, 255)
            )

            rgba = img.convert("RGBA")

            background.paste(
                rgba,
                mask=rgba.getchannel("A")
            )

            result = background
            rgba.close()

        else:
            result = img.convert("RGB")

        buffer = io.BytesIO()

        result.save(
            buffer,
            format="JPEG",
            quality=95
        )

        buffer.seek(0)

        file = discord.File(
            buffer,
            filename="image.jpg"
        )

        embed = discord.Embed(
            title="Image → JPG 🖼️",
            description="Transparency has been replaced with a white background.",
            color=get_success_colour()
        )

        embed.set_image(
            url="attachment://image.jpg"
        )

        await interaction.response.send_message(
            embed=embed,
            file=file
        )

        img.close()
        result.close()

    @image_1.command(
        name="webp",
        description="Turn an image into a WebP"
    )
    async def webp(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        img, err_title, err_desc = await self.load_image(
            interaction,
            media,
            url
        )

        if not img:
            return await self.send_error(
                interaction,
                err_title,
                err_desc
            )

        result = img.convert("RGBA")

        buffer = io.BytesIO()

        result.save(
            buffer,
            format="WEBP",
            quality=95
        )

        buffer.seek(0)

        file = discord.File(
            buffer,
            filename="image.webp"
        )

        embed = discord.Embed(
            title="Image → WebP 🖼️",
            description="Converted successfully.",
            color=get_success_colour()
        )

        embed.set_image(
            url="attachment://image.webp"
        )

        await interaction.response.send_message(
            embed=embed,
            file=file
        )

        img.close()
        result.close()

    @image_1.command(
        name="caption",
        description="Add a caption to an image or GIF"
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

        img, err_title, err_desc = await self.load_image(
            interaction,
            media,
            url
        )

        if not img:
            return await self.send_error(
                interaction,
                err_title,
                err_desc
            )

        is_gif = getattr(
            img,
            "format",
            None
        ) == "GIF"

        if is_gif:
            frame_count = min(
                getattr(
                    img,
                    "n_frames",
                    1
                ),
                40
            )

            frames = []

            for frame_number in range(
                frame_count
            ):
                img.seek(
                    frame_number
                )

                frames.append(
                    img.convert(
                        "RGBA"
                    ).copy()
                )

            duration = img.info.get(
                "duration",
                100
            )

            loop = img.info.get(
                "loop",
                0
            )

        else:
            frames = [
                img.convert(
                    "RGBA"
                )
            ]

            duration = None
            loop = 0

        processed_frames = []

        try:
            for frame in frames:
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

                processed_frames.append(
                    output
                )

            buffer = io.BytesIO()

            if is_gif:
                processed_frames[0].save(
                    buffer,
                    format="GIF",
                    save_all=True,
                    append_images=processed_frames[1:],
                    duration=duration,
                    loop=loop,
                    disposal=2
                )

                filename = "caption.gif"

            else:
                processed_frames[0].save(
                    buffer,
                    format="PNG"
                )

                filename = "caption.png"

            buffer.seek(0)

            file = discord.File(
                buffer,
                filename=filename
            )

            embed = discord.Embed(
                title="Caption 📝",
                color=get_success_colour()
            )

            embed.set_image(
                url=f"attachment://{filename}"
            )

            await interaction.followup.send(
                embed=embed,
                file=file
            )

        finally:
            for frame in frames:
                frame.close()

            for frame in processed_frames:
                frame.close()

            img.close()

    @image_1.command(
        name="brighten",
        description="Brighten an image"
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
            min(amount, 5)
        )

        img, err_title, err_desc = await self.load_image(
            interaction,
            media,
            url
        )

        if not img:
            return await self.send_error(
                interaction,
                err_title,
                err_desc
            )

        result = ImageEnhance.Brightness(
            img.convert("RGB")
        ).enhance(
            1 + amount * 0.2
        )

        await self.send_image(
            interaction,
            result,
            f"Brightened Image ☀️ (Level: {amount})",
            "brighten.png"
        )

        img.close()
        result.close()

    @image_1.command(
        name="darken",
        description="Darken an image"
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
            min(amount, 5)
        )

        img, err_title, err_desc = await self.load_image(
            interaction,
            media,
            url
        )

        if not img:
            return await self.send_error(
                interaction,
                err_title,
                err_desc
            )

        result = ImageEnhance.Brightness(
            img.convert("RGB")
        ).enhance(
            max(
                0,
                1 - amount * 0.2
            )
        )

        await self.send_image(
            interaction,
            result,
            f"Darkened Image 🌑 (Level: {amount})",
            "darken.png"
        )

        img.close()
        result.close()

    @image_1.command(
        name="sharpen",
        description="Sharpen an image"
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
            min(amount, 10)
        )

        img, err_title, err_desc = await self.load_image(
            interaction,
            media,
            url
        )

        if not img:
            return await self.send_error(
                interaction,
                err_title,
                err_desc
            )

        result = img.convert(
            "RGB"
        ).filter(
            ImageFilter.UnsharpMask(
                radius=2,
                percent=100 + amount * 50,
                threshold=3
            )
        )

        await self.send_image(
            interaction,
            result,
            f"Sharpened Image 🔪 (Amount: {amount})",
            "sharpen.png"
        )

        img.close()
        result.close()

    @image_1.command(
        name="contrast",
        description="Change the contrast of an image"
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
            min(amount, 5)
        )

        img, err_title, err_desc = await self.load_image(
            interaction,
            media,
            url
        )

        if not img:
            return await self.send_error(
                interaction,
                err_title,
                err_desc
            )

        result = ImageEnhance.Contrast(
            img.convert("RGB")
        ).enhance(
            amount
        )

        await self.send_image(
            interaction,
            result,
            f"Contrast Image 🌓 (Amount: {amount})",
            "contrast.png"
        )

        img.close()
        result.close()

    @image_1.command(
        name="destroy",
        description="Absolutely destroy an image"
    )
    async def destroy(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        img, err_title, err_desc = await self.load_image(
            interaction,
            media,
            url
        )

        if not img:
            return await self.send_error(
                interaction,
                err_title,
                err_desc
            )

        img = img.convert(
            "RGB"
        )

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
            12
        )

        applied = []

        for _ in range(amount):
            effect = random.choice(
                effects
            )

            if effect == "blur":
                value = random.randint(
                    1,
                    15
                )

                img = img.filter(
                    ImageFilter.GaussianBlur(
                        value
                    )
                )

                applied.append(
                    f"Blur ({value})"
                )

            elif effect == "sharpen":
                value = random.randint(
                    100,
                    500
                )

                img = img.filter(
                    ImageFilter.UnsharpMask(
                        radius=random.randint(1, 5),
                        percent=value,
                        threshold=random.randint(1, 5)
                    )
                )

                applied.append(
                    f"Sharpen ({value}%)"
                )

            elif effect == "contrast":
                value = random.uniform(
                    0.5,
                    4
                )

                img = ImageEnhance.Contrast(
                    img
                ).enhance(
                    value
                )

                applied.append(
                    f"Contrast ({round(value, 2)})"
                )

            elif effect == "colour":
                value = random.uniform(
                    0,
                    5
                )

                img = ImageEnhance.Color(
                    img
                ).enhance(
                    value
                )

                applied.append(
                    f"Colour ({round(value, 2)})"
                )

            elif effect == "brightness":
                value = random.uniform(
                    0.2,
                    3
                )

                img = ImageEnhance.Brightness(
                    img
                ).enhance(
                    value
                )

                applied.append(
                    f"Brightness ({round(value, 2)})"
                )

            elif effect == "darkness":
                value = random.uniform(
                    0.1,
                    0.8
                )

                img = ImageEnhance.Brightness(
                    img
                ).enhance(
                    value
                )

                applied.append(
                    f"Darkness ({round(value, 2)})"
                )

            elif effect == "pixelate":
                value = random.randint(
                    2,
                    30
                )

                small = img.resize(
                    (
                        max(1, img.width // value),
                        max(1, img.height // value)
                    ),
                    Image.Resampling.NEAREST
                )

                img = small.resize(
                    img.size,
                    Image.Resampling.NEAREST
                )

                small.close()

            elif effect == "noise":
                noise = Image.effect_noise(
                    img.size,
                    random.randint(20, 60)
                ).convert(
                    "RGB"
                )

                img = Image.blend(
                    img,
                    noise,
                    0.25
                )

                noise.close()

                applied.append(
                    "Noise"
                )

            elif effect == "invert":
                img = ImageOps.invert(
                    img
                )

                applied.append(
                    "Invert"
                )

        await self.send_image(
            interaction,
            img,
            "Image Destroyed 💀",
            "destroy.png",
            (
                f"Applied {len(applied)} random effects:\n"
                +
                "\n".join(
                    f"• {effect}"
                    for effect in applied[:10]
                )
            )
        )

        img.close()

    @image_1.command(
        name="rotate",
        description="Change the rotation of an image"
    )
    async def rotate(
        self,
        interaction: Interaction,
        angle: float = 90.0,
        media: discord.Attachment = None,
        url: str = None,
        clockwise: bool = True,
    ):
        img, err_title, err_desc = await self.load_image(
            interaction,
            media,
            url
        )

        if not img:
            return await self.send_error(
                interaction,
                err_title,
                err_desc
            )

        if clockwise:
            angle = -angle

        result = img.rotate(
            angle=angle
        )

        clockwise_str = "Clockwise" if clockwise else "Counter-clockwise"

        await self.send_image(
            interaction,
            result,
            f"Rotate Image 🔄 {clockwise_str} (Angle: {abs(angle)})",
            "rotate.png"
        )

        img.close()
        result.close()

    @image_1.command(
        name="flip",
        description="Flip an image"
    )
    async def flip(
        self,
        interaction: Interaction,
        media: discord.Attachment = None,
        url: str = None,
    ):
        img, err_title, err_desc = await self.load_image(
            interaction,
            media,
            url
        )

        if not img:
            return await self.send_error(
                interaction,
                err_title,
                err_desc
            )

        result = img.transpose(
            method=Image.Transpose.FLIP_LEFT_RIGHT
        )

        await self.send_image(
            interaction,
            result,
            "Flipped Image 🔄",
            "flipped.png"
        )

        img.close()
        result.close()

    @image_1.command(
        name="globe",
        description="project any image onto a spinning sphere"
    )
    @app_commands.describe(
        media="The image to wrap around the globe",
        url="A direct image URL"
    )
    async def globe(
        self,
        interaction: discord.Interaction,
        media: discord.Attachment = None,
        url: str = None
    ):
        await interaction.response.defer()

        img, err_title, err_desc = await self.load_image(
            interaction,
            media,
            url
        )

        if not img:
            return await self.send_error(
                interaction,
                err_title,
                err_desc
            )

        source = None
        output_frames = []

        try:
            source = self.prepare_texture(
                img.convert("RGB")
            )

            width = 256
            height = 256
            frames = 32

            for frame in range(frames):
                output_frames.append(
                    self.render_globe(
                        source,
                        width,
                        height,
                        frame / frames
                    )
                )

            buffer = io.BytesIO()

            output_frames[0].save(
                buffer,
                format="GIF",
                save_all=True,
                append_images=output_frames[1:],
                duration=55,
                loop=0,
                disposal=2,
                optimize=True
            )

            buffer.seek(0)

            file = discord.File(
                buffer,
                filename="globe.gif"
            )

            embed = discord.Embed(
                title="🌎 Globe",
                description="Your image has been projected onto a spinning globe.",
                color=get_success_colour()
            )

            embed.set_image(
                url="attachment://globe.gif"
            )

            await interaction.followup.send(
                embed=embed,
                file=file
            )

        except Exception as e:
            print(
                f"[GLOBE] {e}"
            )

            embed = discord.Embed(
                title="🚫 Globe Generation Failed",
                description="I couldn't create the spinning globe.",
                color=get_fail_colour()
            )

            await interaction.followup.send(
                embed=embed
            )

        finally:
            img.close()

            if source:
                source.close()

            for frame in output_frames:
                frame.close()

    @staticmethod
    def prepare_texture(image):
        width, height = image.size

        ratio = width / height

        if ratio < 2:
            new_width = height * 2
            canvas = Image.new("RGB", (new_width, height))
            canvas.paste(
                image,
                ((new_width - width) // 2, 0)
            )
            image = canvas

        elif ratio > 2:
            new_height = width // 2
            canvas = Image.new("RGB", (width, new_height))
            canvas.paste(
                image,
                (0, (new_height - height) // 2)
            )
            image = canvas

        return image.resize((512, 256), Image.Resampling.LANCZOS)

    @staticmethod
    def render_globe(texture, width, height, rotation):
        frame = Image.new("RGBA", (width, height), (0, 0, 0, 0))

        pixels = frame.load()
        texture_pixels = texture.load()

        radius = width * 0.43
        center_x = width / 2
        center_y = height / 2

        for y in range(height):
            dy = (y - center_y) / radius

            if abs(dy) > 1:
                continue

            for x in range(width):
                dx = (x - center_x) / radius

                distance = dx * dx + dy * dy

                if distance > 1:
                    continue

                dz = math.sqrt(1 - distance)

                longitude = math.atan2(dx, dz)
                latitude = math.asin(-dy)

                longitude += rotation * math.tau

                u = (longitude / math.tau + 0.5) % 1.0
                v = 0.5 - latitude / math.pi

                tx = int(u * 511) % 512
                ty = max(0, min(255, int(v * 255)))

                r, g, b = texture_pixels[tx, ty]

                light = 0.45 + 0.55 * max(0, dz)

                r = int(r * light)
                g = int(g * light)
                b = int(b * light)

                pixels[x, y] = (r, g, b, 255)

        return frame

    @image_1.command(
        name="ascii",
        description="Turn an image into ASCII art"
    )
    @app_commands.describe(
        image="The image to convert into ASCII art",
        url="A direct URL to an image"
    )
    async def ascii(
        self,
        interaction: discord.Interaction,
        image: discord.Attachment = None,
        url: str = None
    ):
        await interaction.response.defer()

        if image is None and not url:
            embed = discord.Embed(
                title="ASCII Conversion Failed 🚫",
                description="Please upload an image or provide an image URL.",
                colour=get_fail_colour()
            )
            await interaction.followup.send(embed=embed)
            return

        if image is not None and url:
            embed = discord.Embed(
                title="ASCII Conversion Failed 🚫",
                description="Please provide either an uploaded image or a URL, not both.",
                colour=get_fail_colour()
            )
            await interaction.followup.send(embed=embed)
            return

        try:
            if image is not None:
                if not image.content_type or not image.content_type.startswith("image/"):
                    embed = discord.Embed(
                        title="ASCII Conversion Failed 🚫",
                        description="Please upload a valid image.",
                        colour=get_fail_colour()
                    )
                    await interaction.followup.send(embed=embed)
                    return

                data = await image.read()
                original_name = image.filename
                thumbnail_url = image.url

            else:
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        url,
                        timeout=aiohttp.ClientTimeout(total=15)
                    ) as response:
                        if response.status != 200:
                            raise ValueError("Failed to download image")

                        content_type = response.headers.get("Content-Type", "").lower()

                        if not content_type.startswith("image/"):
                            raise ValueError("URL does not point to an image")

                        data = await response.read()

                parsed_url = url.split("?", 1)[0].split("#", 1)[0]
                original_name = parsed_url.rstrip("/").split("/")[-1]

                if not original_name or "." not in original_name:
                    original_name = "image"

                thumbnail_url = url

            img = Image.open(io.BytesIO(data))
            img = img.convert("L")

            max_width = 120

            width, height = img.size
            aspect_ratio = height / width

            new_height = max(
                1,
                int(max_width * aspect_ratio * 0.5)
            )

            img = img.resize(
                (max_width, new_height),
                Image.Resampling.LANCZOS
            )

            characters = "@#%$S?*^+;:,. "

            pixels = list(img.getdata())

            ascii_art = ""

            for y in range(img.height):
                for x in range(img.width):
                    pixel = pixels[y * img.width + x]

                    index = int(
                        pixel / 256 * len(characters)
                    )

                    if index >= len(characters):
                        index = len(characters) - 1

                    ascii_art += characters[index]

                ascii_art += "\n"

            ascii_art = ascii_art.rstrip()

            base_name = original_name.rsplit(".", 1)[0]

            file = discord.File(
                io.BytesIO(ascii_art.encode("utf-8")),
                filename=f"{base_name}_ascii.txt"
            )

            embed = discord.Embed(
                title="ASCII Art 🖼️",
                description="Converted image into ASCII text.",
                colour=get_success_colour()
            )

            embed.set_thumbnail(url=thumbnail_url)
            embed.set_footer(
                text=f"Original image: {original_name}"
            )

            await interaction.followup.send(
                embed=embed,
                file=file
            )

        except Exception:
            embed = discord.Embed(
                title="ASCII Conversion Failed 🚫",
                description="I couldn't download or convert that image.",
                colour=get_fail_colour()
            )

            await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(
        Images(bot)
    )