"""Defines functions related to the database."""
from datetime import datetime
from discord.ext import commands
from utils.config import registration_channel
from cogs.xp import rsn_exists

class Database():
    """Defines database commands."""

    def __init__(self, bot):
        self.bot = bot

    async def handle_registration(self, ctx, rsn, is_main):
        """Handles registration output."""
        async with self.bot.pool.acquire() as con:
            exists = await rsn_exists(con, rsn)
        disc_id = str(ctx.author.id)

        if not exists:
            await ctx.send(f"Username {rsn} not found in clan database.")
            return

        # First check if the user is currently registered for the username.
        names_stmt = """SELECT rsn FROM account_owned WHERE end_dtg IS NULL"""
        async with self.bot.pool.acquire() as con:
            names = await con.fetch(names_stmt, disc_id)

        if rsn in names:
            await ctx.send(f"Username {rsn} already registered.")
            return

        # Send message to registration channel for approval.
        self.bot.reg_ch = self.bot.get_channel(registration_channel)
        approval = await self.bot.reg_ch.send(f"Discord user {ctx.author.name} is attempting to "
                                             f"register Runescape username {rsn}. React with "
                                             ":white_check_mark: to approve, or :x: to disapprove.")

        def approval(reaction, user):
            """Checks for approval reaction."""
            return reaction.emoji == u"\u2705" and reaction.emoji == u"\u274c"

        reaction, user = await self.bot.wait_for('reaction_add', check=approval)

        if reaction.emoji == u"\u2705":
            await ctx.author.send(f"Your registration as {rsn} has been approved.")
            await self.register_user(disc_id, rsn, is_main)
            await approval.delete()
            await self.bot.reg_ch.send(f"Discord user {ctx.author.name} approved as Runescape "
                                       f"user {rsn}.")
        elif reaction.emoji == u"\u274c":
            await ctx.author.send(f"Your registration as {rsn} has been disapproved. "
                                    "You must reregister with a valid username.")
            await approval.delete()
            return

    async def register_user(self, disc_id, rsn, is_main):
        """Inserts account registers into the database."""
        async with self.bot.pool.acquire() as con:
            async with con.transaction():
                disc_stmt = """INSERT INTO account(disc_id, total_caps) VALUES ($1, 0);"""
                await con.execute(disc_stmt, disc_id)
            async with con.transaction():
                account_stmt = """INSERT INTO account_owned(disc_id, rsn, is_main, start_dtg)
                     VALUES ($1, $2, $3, $4);"""
                start_dtg = datetime.now()
                await con.execute(account_stmt, disc_id, rsn, is_main, start_dtg)

    @commands.group()
    async def register(self, ctx):
        """Registers a player in the database if the rsn is valid."""
        pass

    @register.command(name="main")
    async def _main(self, ctx, rsn):
        """Registers the given rsn as the player's current main account."""
        await self.handle_registration(ctx, rsn, True)

    @register.command(name="alt")
    async def _alt(self, ctx, rsn):
        """Registers the given rsn as the player's current main account."""
        await self.handle_registration(ctx, rsn, False)

def setup(bot):
    """Adds the cog to the bot."""
    bot.add_cog(Database(bot))
