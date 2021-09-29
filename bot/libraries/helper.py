import re
import asyncio
from html.parser import HTMLParser
import aiohttp
from discord.ext import commands
import config


def is_bot_author(id: int):
    return id == 227473074616795137


async def t3_only(ctx):
    return is_bot_author(ctx.author.id) or permission_check(ctx, 4)


async def mod_only(ctx):
    return is_bot_author(ctx.author.id) or permission_check(ctx, 6)


def permission_check(ctx, level: int):
    perms = config.PermissionRoles.fetch_by_lvl(level)
    main_guild = ctx.bot.get_guild(config.Misc.fetch("main_guild_id"))
    if (main_guild_member := main_guild.get_member(ctx.author.id)) is None:
        return False

    has_roles = [role.id for role in (main_guild_member.roles)]

    for role in perms:
        if role.perm_lvl >= level:
            if role.role_id in has_roles:
                return True
        else:
            break
    return False


class aTagParser(HTMLParser):
    link = ''
    view_text = ''

    def clear_output(self):
        self.link = ''
        self.view_text = ''

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            for attr in attrs:
                if attr[0] == 'href':
                    self.link = f'({attr[1]})'

    def handle_endtag(self, tag):
        pass

    def handle_data(self, data):
        self.view_text = f'[{data}]'


def formatDesc(desc):
    revisions = {
        "<b>": "**",
        "</b>": "**",
        "<u>": "__",
        "</u>": "__",
        "<br>": "",
    }
    for old, new in revisions.items():
        desc = desc.replace(old, new)
    items = []
    embeds = dict()
    items.extend([i.groups() for i in re.finditer('(<a.+>.+</a>)', desc)])  # Finds all unhandled links
    for i in items:
        i = i[0]  # regex returns a one-element tuple :/
        parser = aTagParser()
        parser.feed(i)
        embeds.update({i: parser.view_text + parser.link})
    for old, new in embeds.items():
        desc = desc.replace(old, new)

    desc = re.sub('#+ ', "", desc)
    return desc


async def repository_query(query: str, bot):
    bot.logger.info(f"SMR query of length {len(query)} requested")

    async with await bot.web_session.post("https://api.ficsit.app/v2/query", json={"query": query}) as response:
        bot.logger.info(f"SMR query returned with response {response.status}")
        value = await response.json()
        bot.logger.info("SMR response decoded")
        return value
