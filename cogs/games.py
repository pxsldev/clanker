import aiohttp
import discord
import random
from discord import app_commands, Interaction
from discord.ext import commands
from cogs.theming import get_fail_colour, get_success_colour

class WordleView(discord.ui.View):
    def __init__(self, user_id, word, valid_words):
        super().__init__(timeout=900)

        self.user_id = user_id
        self.word = word.lower()
        self.valid_words = valid_words
        self.guesses = []
        self.finished = False

        self.guess_button = discord.ui.Button(
            label="Guess",
            style=discord.ButtonStyle.primary,
            emoji="✏️"
        )

        self.guess_button.callback = self.guess

        self.quit_button = discord.ui.Button(
            label="Quit",
            style=discord.ButtonStyle.danger,
            emoji="🚪"
        )

        self.quit_button.callback = self.quit

        self.add_item(self.guess_button)
        self.add_item(self.quit_button)

    async def interaction_check(self, interaction: Interaction):
        if interaction.user.id != self.user_id:
            embed = discord.Embed(
                title="That's not your Wordle! ❌",
                description="You can't interact with someone else's game.",
                color=get_fail_colour()
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

            return False

        return True

    def get_grid(self):
        rows = []

        for guess in self.guesses:
            result = ["⬛"] * 5
            remaining = list(self.word)

            for i in range(5):
                if guess[i] == self.word[i]:
                    result[i] = "🟩"
                    remaining[i] = None

            for i in range(5):
                if result[i] == "🟩":
                    continue

                if guess[i] in remaining:
                    result[i] = "🟨"
                    remaining[remaining.index(guess[i])] = None

            rows.append(f"{guess}  {''.join(result)}")

        while len(rows) < 6:
            rows.append("-----  ⬜⬜⬜⬜⬜")

        return "\n".join(rows)

    def get_embed(self):
        embed = discord.Embed(
            title="Wordle",
            description=f"```text\n{self.get_grid()}\n```",
            color=0x5865F2
        )

        embed.set_footer(
            text=f"Attempt {len(self.guesses)}/6 • Only you can play this game"
        )

        return embed

    async def guess(self, interaction: Interaction):
        if self.finished:
            embed = discord.Embed(
                title="Wordle has ended! ❌",
                description="This game is already finished.",
                color=get_fail_colour()
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

            return

        await interaction.response.send_modal(
            WordleModal(self)
        )

    async def quit(self, interaction: Interaction):
        if self.finished:
            embed = discord.Embed(
                title="Wordle has ended! ❌",
                description="This game is already finished.",
                color=get_fail_colour()
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

            return

        self.finished = True
        self.guess_button.disabled = True
        self.quit_button.disabled = True

        embed = self.get_embed()

        embed.title = "Wordle — You quit! 🚪"

        embed.description = (
            f"```text\n{self.get_grid()}\n```\n"
            f"The word was **{self.word}**.\n"
            f"Better luck next time!"
        )

        embed.color = get_fail_colour()
        embed.set_footer(text="Game ended by you.")

        await interaction.response.edit_message(
            embed=embed,
            view=self
        )

    async def on_timeout(self):
        self.finished = True
        self.guess_button.disabled = True
        self.quit_button.disabled = True

class WordleModal(discord.ui.Modal, title="Make a guess"):
    guess_input = discord.ui.TextInput(
        label="Your 5-letter guess",
        placeholder="Enter a word...",
        min_length=5,
        max_length=5,
        required=True
    )

    def __init__(self, game):
        super().__init__()
        self.game = game

    async def on_submit(self, interaction: Interaction):
        if self.game.finished:
            embed = discord.Embed(
                title="Wordle has ended! ❌",
                description="This game is already finished.",
                color=get_fail_colour()
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

            return

        guess = self.guess_input.value.strip().lower()

        if len(guess) != 5 or not guess.isalpha():
            embed = discord.Embed(
                title="Invalid guess ❌",
                description="Your guess must contain exactly **5 letters**.",
                color=get_fail_colour()
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

            return

        if guess not in self.game.valid_words:
            embed = discord.Embed(
                title="Not a valid word ❌",
                description=f"**{guess}** isn't in the Wordle word list.",
                color=get_fail_colour()
            )

            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )

            return

        self.game.guesses.append(guess)

        if guess == self.game.word:
            attempts = len(self.game.guesses)

            self.game.finished = True
            self.game.guess_button.disabled = True
            self.game.quit_button.disabled = True

            embed = self.game.get_embed()

            embed.title = "Wordle — You won! 🎉"

            embed.description = (
                f"```text\n{self.game.get_grid()}\n```\n"
                f"You guessed the correct word **{self.game.word}** "
                f"in **{attempts} attempt{'s' if attempts != 1 else ''}!**"
            )

            embed.color = get_success_colour()
            embed.set_footer(text="Congratulations! 🎉")

            await interaction.response.edit_message(
                embed=embed,
                view=self.game
            )

            return

        if len(self.game.guesses) >= 6:
            self.game.finished = True
            self.game.guess_button.disabled = True
            self.game.quit_button.disabled = True

            embed = self.game.get_embed()

            embed.title = "Wordle — Game over 💀"

            embed.description = (
                f"```text\n{self.game.get_grid()}\n```\n"
                f"The word was **{self.game.word}**.\n"
                f"Better luck next time!"
            )

            embed.color = get_fail_colour()
            embed.set_footer(text="Maybe you'll get it next time!")

            await interaction.response.edit_message(
                embed=embed,
                view=self.game
            )

            return

        await interaction.response.edit_message(
            embed=self.game.get_embed(),
            view=self.game
        )

@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.allowed_installs(guilds=True, users=True)
class Games(commands.GroupCog, group_name="games"):
    def __init__(self, bot):
        self.bot = bot

    group_1 = app_commands.Group(
        name="1",
        description="Games - page 1",
        allowed_contexts=app_commands.AppCommandContext(guild=True, dm=True, private_channel=True),
        allowed_installs=app_commands.AppInstallationType(guild=True, user=True)
    )

    @group_1.command(
        name="wordle",
        description="Start a random wordle."
    )
    async def wordle(
        self,
        interaction: Interaction
    ):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://api.pxsl.dev/wordle.txt"
                ) as response:
                    response.raise_for_status()
                    text = await response.text()

            words = {
                word.strip().lower()
                for word in text.splitlines()
                if len(word.strip()) == 5
                and word.strip().isalpha()
            }

            if not words:
                raise ValueError(
                    "No valid five-letter words were found."
                )

            chosen = random.choice(list(words))

        except Exception as e:
            print(
                f"[Wordle] Failed to retrieve word list: "
                f"{type(e).__name__}: {e}"
            )

            embed = discord.Embed(
                title="Couldn't start Wordle ❌",
                description=(
                    "I couldn't retrieve the Wordle word list right now.\n"
                    "Please try again in a moment."
                ),
                color=get_fail_colour()
            )

            await interaction.response.send_message(
                embed=embed
            )

            return

        game = WordleView(
            interaction.user.id,
            chosen,
            words
        )

        embed = game.get_embed()

        embed.description = (
            "Guess the **5-letter word**!\n\n"
            f"```text\n{game.get_grid()}\n```\n"
            "🟩 Correct letter and position\n"
            "🟨 Correct letter, wrong position\n"
            "⬛ Letter isn't in the word"
        )

        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url
        )

        await interaction.response.send_message(
            embed=embed,
            view=game
        )

async def setup(bot):
    await bot.add_cog(Games(bot))