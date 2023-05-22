"""
def jeyy_api_loader(self):
    for end_point in END_POINTS:

        @commands.command(name=end_point, help=f"{end_point} commnad Generation")
        @commands.bot_has_permissions(attach_files=True)
        @Context.with_type
        async def callback(
            ctx: Context,
            *,
            target: Union[discord.Member, discord.Emoji, str, None] = None,
        ):
            ref = ctx.message.reference
            url = None
            if ref and isinstance(ref.resolved, discord.Message):
                msg: discord.Message = ref.resolved
                if msg.attachments and msg.attachments[0].url.endswith(
                    ("png", "jpeg", "jpg", "gif", "webp")
                ):
                    url = msg.attachments[0].url
                elif msg.embeds and str(msg.embeds[0].image.url).endswith(
                    ("png", "jpeg", "jpg", "gif", "webp")
                ):
                    url = ref.resolved.embeds[0].image.url

            elif isinstance(target, discord.Member):
                url = target.display_avatar.url
            elif isinstance(target, discord.Emoji):
                url = target.url
            elif isinstance(target, str):
                url = f"https://raw.githubusercontent.com/iamcal/emoji-data/master/img-twitter-72/{ord(list(target)[0]):x}.png"
            elif url is not None and LINKS_RE.fullmatch(target):
                url = target

            url = url or ctx.author.display_avatar.url
            params = {"image_url": url}
            r = await self.bot.http_session.get(
                f"https://api.jeyy.xyz/v2/image/{ctx.command.name}", params=params
            )
            file = discord.File(
                io.BytesIO(await r.read()), f"{ctx.command.name}.gif"
            )
            embed = (
                discord.Embed(timestamp=discord.utils.utcnow()).set_image(
                    url=f"attachment://{ctx.command.name}.gif"
                )
            ).set_footer(text=f"{ctx.author}")
            await ctx.reply(embed=embed, file=file)

        self.bot.add_command(callback)

def some_random_api_loader(self):
    bot: Parrot = self.bot
    for endpoint in [
        "gay",
        "glass",
        "horny",
        "jail",
        "lolice",
        "simpcard",
        "triggered",
        "wasted",
    ]:

        @commands.command(name=endpoint)
        @commands.bot_has_permissions(attach_files=True, embed_links=True)
        @commands.max_concurrency(1, per=commands.BucketType.user)
        @Context.with_type
        async def callback(ctx: Context, *, member: discord.Member = None) -> None:
            member = member or ctx.author

            response = await bot.http_session.get(
                "https://some-random-api.ml/canvas/{}?avatar={}".format(
                    ctx.command.name, member.display_avatar.url
                )
            )
            imageData = io.BytesIO(await response.read())  # read the image/bytes

            await ctx.reply(
                file=discord.File(imageData, "gay.png")
            )  # replying the file

        self.bot.add_command(callback)
"""