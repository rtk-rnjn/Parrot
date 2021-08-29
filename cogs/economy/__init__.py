from discord.ext import commands
import discord, random
from core import Parrot, Context, Cog
from datetime import datetime

from utilities.database import ge_update, economy_db

collection = economy_db['global_economy']


class economy(Cog):
    """Parrot Economy to get some Parrot Coins as to make calls"""
    def __init__(self, bot: Parrot):
        self.bot = bot
    
    @commands.command(aliases=['reseteconomy'])
    @commands.cooldown(1, 5, commands.BucketType.member)
    @Context.with_type
    async def reseteco(self, ctx: Context):
        """To reset the economy, this can not be undone"""
        x = await collection.find_one({'_id': ctx.author.id})
        if not x:
            return await ctx.reply(f"{ctx.author.mention} you already dont have a economy")
        else:
            await ctx.reply(f"{ctx.author.mention} Are you sure about that? If yes, then type `YES`")
            def check(m):
                return m.author.id == ctx.author.id and m.channel.id == ctx.channel.id
            try:
                msg = self.bot.wait_for('message', timeout=60, check=check)
            except Exception:
                return await ctx.reply(f"{ctx.author.mention} you didnt answer on time")
            if msg.content.upper() == 'YES':
                await collection.delete_one({'_id': ctx.author.id})
                return await ctx.reply(f"{ctx.author.mention} deleted successfully")
        
    @commands.command(aliases=['starteconomy'])
    @commands.cooldown(1, 5, commands.BucketType.member)
    @Context.with_type
    async def starteco(self, ctx: Context):
        """
        To start the Parrot Economy.
        """
        x = await collection.find_one({'_id': ctx.author.id})
        if not x: 
            await collection.insert_one({'_id':ctx.author.id, 'bank': 0, 'wallet': 400})
            await ctx.reply(f"{ctx.author.mention} successfully started your Parort Bank. You have **0** coins in the bank and **400** coins in the wallet")
        else:
            await ctx.reply(f"{ctx.author.mention} you already started your Parort Bank.")

    @commands.command(aliases=["with"])
    @commands.cooldown(1, 5, commands.BucketType.member)
    @Context.with_type
    async def withdraw(self, ctx: Context, money: int):
        """
		Withdraw your money, from your bank account
		"""
        if money < 0:
            return await ctx.reply(
                f'{ctx.author.mention} money can not be negative')

        x = await collection.find_one({'_id': ctx.author.id})
        if x:
            coins_walt = x['wallet']
            coins_bank = x['bank']

            if coins_bank - money < 0:
                return await ctx.reply(
                    f'{ctx.author.mention} you do not have enough money to withdraw money'
                )
            else:
                coins_walt += money
                coins_bank -= money
                await ge_update(ctx.author.id, coins_bank, coins_walt)
                return await ctx.reply(
                    f"{ctx.author.mention} deposited **{money}** coins in the bank"
                )
        else:
            await ctx.reply(f"{ctx.author.mention} you don't have started your Parrot Bank yet. Consider doing `{ctx.clean_prefix}starteco` to get started!")

    @commands.command(aliases=['rob'])
    @commands.cooldown(1, 30, commands.BucketType.member)
    @Context.with_type
    async def steal(self, ctx, *, member: discord.Member):
        """
		Want more money? Try stealing others.
		"""

        x = await collection.find_one({'_id': ctx.author.id})
        y = await collection.find_one({'_id': member.id})

        if x and y:
            coins_walt_x = x['wallet']
            coins_bank_x = x['bank']
            coins_walt_y = y['wallet']
            coins_bank_y = y['bank']
            if coins_walt_y == 0:
                return await ctx.reply(
                    f"{ctx.author.mention} **{member.name}#{member.discriminator}** don't have enough money to be robbed."
                )
            money = random.randint(0, coins_walt_y)
            coins_walt_y -= money
            coins_walt_x += money

            await ge_update(member.id, coins_bank_y, coins_walt_y)
            await ge_update(ctx.author.id, coins_bank_x, coins_walt_x)

            return await ctx.reply(
                f"{ctx.author.mention} you robbed **{member.name}#{member.discriminator}** and received **{money}**"
            )
        if not y:
            return await ctx.reply(
                f"{ctx.author.mention} **{member.name}#{member.discriminator}** don't have Parrot Bank"
            )
        if not x:
            await ctx.reply(f"{ctx.author.mention} you don't have started your Parrot Bank yet. Consider doing `{ctx.clean_prefix}starteco` to get started!")

    @commands.command()
    @commands.cooldown(1, 10, commands.BucketType.member)
    @Context.with_type
    async def slots(self, ctx: Context, money: int):
        '''Want more money? Try gambling slots'''

        if money < 0:
            return await ctx.reply(
                f'{ctx.author.mention} money can not be negative')

        x = await collection.find_one({'_id': ctx.author.id})

        if x:
            coins_walt = x['wallet']
            coins_bank = x['bank']
            if coins_walt - money < 0:
                return await ctx.reply(
                    f"{ctx.author.mention} you don't have enough money to slots"
                )

            emoji = ["🍇", "🍉", "🍊", "🍎"]
            first = random.choice(emoji)
            second = random.choice(emoji)
            third = random.choice(emoji)
            if first == second == third:
                await ctx.reply(
                    f"{ctx.author.mention}\n\nYour slots results:\n> |{first}|{second}|{third}|\n\nYayy!! you won **{money*10}** money"
                )
                coins_walt['wallet'] += (money * 10)
            else:
                await ctx.reply(
                    f"{ctx.author.mention}\n\nYour slots results:\n> |{first}|{second}|{third}|\n\nYou lost {money} money :'("
                )
                coins_walt['wallet'] -= money

            await ge_update(ctx.author.id, coins_bank, coins_walt)
        else:
            await ctx.reply(f"{ctx.author.mention} you don't have started your Parrot Bank yet. Consider doing `{ctx.clean_prefix}starteco` to get started!")

    @commands.command(aliases=['send'])
    @commands.cooldown(1, 5, commands.BucketType.member)
    @Context.with_type
    async def give(self, ctx: Context, member: discord.Member, money: int):
        '''
				You can give your Parrot coins to other user too
				'''

        if money < 0:
            return await ctx.reply(
                f'{ctx.author.mention} money can not be negative')

        x = await collection.find_one({'_id': ctx.author.id})
        y = await collection.find_one({'_id': member.id})

        if x and y:
            coins_walt_x = x['wallet'] - money
            coins_bank_x = x['bank']
            if coins_walt_x < 0:
                return await ctx.reply(
                    f"{ctx.author.mention} you don't have **{money}** in your wallet to send it to **{member.name}#{member.discriminator}**"
                )
            coins_walt_y = y['wallet'] + money
            coins_bank_y = y['bank']

            await ge_update(member.id, coins_bank_y, coins_walt_y)
            await ge_update(ctx.author.id, coins_bank_x, coins_walt_x)

            return await ctx.reply(
                f"{ctx.author.mention} **{member.name}#{member.discriminator}** received **{money}** from you"
            )
        if not y:
            return await ctx.reply(
                f"{ctx.author.mention} **{member.name}#{member.discriminator}** don't have Parrot Economy"
            )
        if not x:
            await ctx.reply(f"{ctx.author.mention} you don't have started your Parrot Bank yet. Consider doing `{ctx.clean_prefix}starteco` to get started!")

    @commands.command(aliases=["dep"])
    @commands.cooldown(1, 5, commands.BucketType.member)
    @Context.with_type
    async def deposit(self, ctx: Context, money: int):
        '''
				Save your money by depositing all the money in the bank
				'''

        if money < 0:
            return await ctx.reply(
                f'{ctx.author.mention} money can not be negative')

        x = await collection.find_one({'_id': ctx.author.id})
        if x:
            coins_walt = x['wallet']
            coins_bank = x['bank']

            if coins_walt - money < 0:
                return await ctx.reply(
                    f'{ctx.author.mention} you do not have enough money to deposit money'
                )
            else:
                coins_walt -= money
                coins_bank += money
                await ge_update(ctx.author.id, coins_bank, coins_walt)
                return await ctx.reply(
                    f"{ctx.author.mention} deposited **{money}** coins in the bank"
                )
        else:
            await ctx.reply(f"{ctx.author.mention} you don't have started your Parrot Bank yet. Consider doing `{ctx.clean_prefix}starteco` to get started!")

    @commands.command()
    @commands.cooldown(1, 30, commands.BucketType.member)
    @Context.with_type
    async def beg(self, ctx: Context):
        '''
				Beg from internet, hope someone will give you money
				'''

        inc = random.randint(0, 100)
        someone = [
            "someone", "Mr. X", "Mother nature", "PewDiePie", "CarryMinati", "Discord",
            "Parrot", "this internet", "the guy who punched you yesterday", "Ritik Ranjan",
            "girl with whom you had fun last night", "your father", "the Boss", "your mom"
        ]

        gives = [
            'gives you', 'gifted you', 'unconditionally gives you',
            'slaps, and give', 'transfer'
        ]

        x = await collection.find_one({'_id': ctx.author.id})
        if x:
            coins_walt = x['wallet'] + inc
            coins_bank = x['bank']
            await ctx.reply(
                f"{ctx.author.mention} {random.choice(someone)} {random.choice(gives)} **{inc}** coins to you"
            )
            await ge_update(ctx.author.id, coins_bank, coins_walt)
            return
        else:
            await ctx.reply(f"{ctx.author.mention} you don't have started your Parrot Bank yet. Consider doing `{ctx.clean_prefix}starteco` to get started!")

    @commands.command(aliases=['bal', 'wallet', 'bank'])
    @commands.cooldown(1, 5, commands.BucketType.member)
    @Context.with_type
    async def balance(self, ctx: Context, *, member: discord.User = None):
        '''
				To check your balance, if not, then it will open a Parrot Economy bank account for you
				'''
        target = ctx.author or member
        if target.bot: return

        x = await collection.find_one({'_id': target.id})

        if not x:
            if target is ctx.author:
                return await ctx.reply(f"{ctx.author.mention} you don't have started your Parrot Bank yet. Consider doing `{ctx.clean_prefix}starteco` to get started!")
            else:
                return await ctx.reply(
                    f"{ctx.author.mention} **{member.name}#{member.discriminator}** don't have Parrot Economy"
                )
        
        return await ctx.reply(f"{ctx.author.mention if target is ctx.author else target.name} has **{x['bank']}** in bank and **{x['wallet']}** in wallet")
        

    @commands.command(aliases=['cointoss', 'cf', 'ct'])
    @commands.cooldown(1, 5, commands.BucketType.member)
    @Context.with_type
    async def coinflip(self, ctx: Context, money: int, choose: str = None):
        """
        A another gambling command for earn more money
        """
        choose = 'tails' if choose in ['tails', 'tail', 't'] else 'heads'
        
        x = await collection.find_one({'_id': ctx.author.id})
        if not x: 
            return await ctx.reply(f"{ctx.author.mention} you don't have started your Parrot Bank yet. Consider doing `{ctx.clean_prefix}starteco` to get started!")
        
        coins_bank = x['bank']
        coins_walt = x['wallet']
        result = random.choice(['heads', 'tails'])
        if result == choose:
            coins_walt = coins_walt + money
            await ge_update(ctx.author.id, coins_bank, coins_walt)
            await ctx.reply(f"{ctx.author.mention} you choose {choose} | Coin landed on {result} | You won {money}")

        elif result != choose:
            coins_walt = coins_walt - money
            await ge_update(ctx.author.id, coins_bank, coins_walt)
            await ctx.reply(f"{ctx.author.mention} you choose {choose} | Coin landed on {result} | You lose {money}")
            
def setup(bot):
    bot.add_cog(economy(bot))
