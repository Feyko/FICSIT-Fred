import discord
import asyncio
import config
import libraries.createembed as CreateEmbed
import json
import libraries.helper as Helper
from algoliasearch.search_client import SearchClient
import requests
import io
import typing

from discord.ext import commands


async def t3_only(ctx):
    return (ctx.author.id == 227473074616795137 or
            ctx.author.permissions_in(ctx.bot.get_channel(config.Misc.get_filter_channel())).send_messages)


async def mod_only(ctx):
    return (ctx.author.id == 227473074616795137 or
            ctx.author.permissions_in(ctx.bot.modchannel).send_messages)


class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        # We get an error about commands being found when using "runtime" commands, so we have to ignore that
        if isinstance(error, commands.CommandNotFound):
            command = ctx.message.content.lower().lstrip(self.bot.command_prefix).split(" ")[0]
            if config.Commands.fetch(command):
                return
        await ctx.send("I encountered an error while trying to call this command. Feyko has been notified")
        raise error

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not self.bot.running:
            return
        if message.content.startswith(self.bot.command_prefix):
            name = message.content.lower().lstrip(self.bot.command_prefix).split(" ")[0]
            if command := config.Commands.fetch(name):
                await message.channel.send(command["content"])
                return

    @commands.command()
    async def version(self, ctx):
        await ctx.send(self.bot.version)

    @commands.command()
    async def help(self, ctx):
        await ctx.send("Sorry, this command is temporarily unavailable")

    @commands.command()
    async def mod(self, ctx, *args):
        if len(args) < 1:
            await ctx.send("This command requires at least one argument")
            return
        if args[0] == "help":
            await ctx.send("I search for the provided mod name in the SMR database, returning the details "
                           "of the mod if it is found. If multiple are found, it will state so. Same for "
                           "if none are found. If someone reacts to the clipboard in 4m, I will send them "
                           "the full description of the mod.")
            return
        args = " ".join(args)
        result, desc = CreateEmbed.mod(args)
        if result is None:
            await ctx.send("No mods found!")
        elif isinstance(result, str):
            await ctx.send("multiple mods found")
        else:
            newmessage = await ctx.send(content=None, embed=result)
            if desc:
                await newmessage.add_reaction("📋")
                await asyncio.sleep(0.5)

                def check(reaction, user):
                    if reaction.emoji == "📋" and reaction.message.id == newmessage.id:
                        return True

                while True:
                    try:
                        r = await self.bot.wait_for('reaction_add', timeout=240.0, check=check)
                        member = r[1]
                        if not member.dm_channel:
                            await member.create_dm()
                        try:
                            await member.dm_channel.send(content=None, embed=CreateEmbed.desc(desc))
                            await newmessage.add_reaction("✅")
                        except:
                            await ctx(
                                "I was unable to send you a direct message. Please check your discord "
                                "settings regarding those !")
                    except asyncio.TimeoutError:
                        break

    @commands.command()
    async def docsearch(self, ctx, *, args):
        yaml = requests.get("https://raw.githubusercontent.com/satisfactorymodding/Documentation/Dev/antora.yml")
        yamlf = io.BytesIO(yaml.content)
        version = str(yamlf.read()).split("version: ")[1].split("\\")[0]

        search = SearchClient.create('BH4D9OD16A', '53b3a8362ea7b391f63145996cfe8d82')
        index = search.init_index('ficsit')
        query = index.search(args + " " + version)
        await ctx.send("This is the best result I got from the SMD :\n" + query["hits"][0]["url"])

    @commands.group()
    @commands.check(t3_only)
    async def add(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid sub command passed...')
            return

    @commands.group()
    @commands.check(t3_only)
    async def remove(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid sub command passed...')
            return

    @commands.group()
    @commands.check(t3_only)
    async def set(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid sub command passed...')
            return

    @commands.group()
    @commands.check(t3_only)
    async def modify(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send('Invalid sub command passed...')
            return

    @add.command(name="mediaonly")
    async def addmediaonly(self, ctx, *args):
        if ctx.message.channel_mentions:
            id = int(ctx.message.channel_mentions[0].id)
        else:
            if len(args) > 0:
                id = int(args[0])
            else:
                id = int(await Helper.waitResponse(self.bot, ctx.message, "What is the ID for the channel? e.g. "
                                                                          "``709509235028918334``"))

        if config.MediaOnlyChannels.fetch(id):
            await ctx.send("This channel is already a media only channel")
            return

        config.MediaOnlyChannels(channel_id=id)
        await ctx.send("Media only channel " + self.bot.get_channel(id).mention + " added !")

    @remove.command(name="mediaonly")
    async def removemediaonly(self, ctx, *args):
        if ctx.message.channel_mentions:
            id = int(ctx.message.channel_mentions[0].id)
        else:
            if len(args) > 0:
                id = int(args[0])
            else:
                id = int(await Helper.waitResponse(self.bot, ctx.message, "What is the ID for the channel? e.g. "
                                                                          "``709509235028918334``"))

        if not config.MediaOnlyChannels.fetch(id):
            await ctx.send("Media Only Channel could not be found !")
            return

        config.MediaOnlyChannels.deleteBy(channel_id=id)
        await ctx.send("Media Only Channel removed !")

    @add.command(name="command")
    async def addcommand(self, ctx, *args):
        if args:
            command = args[0]
        else:
            command = await Helper.waitResponse(self.bot, ctx.message, "What is the command? e.g. ``install``")

        if config.Commands.fetch(command):
            await ctx.send("This command already exists !")
            return
        if config.ReservedCommands.fetch(command):
            await ctx.send("This command name is reserved")
            return

        if len(args) == 2:
            response = args[1]
        elif len(args) > 1:
            response = " ".join(args[1:])
        else:
            response = await Helper.waitResponse(self.bot, ctx.message, "What is the response? e.g. ``Hello there`` "
                                                                        "or an image or link to an image")

        config.Commands(name=command, content=response)
        await ctx.send("Command '" + command + "' added !")

    @remove.command(name="command")
    async def removecommand(self, ctx, *args):
        if args:
            commandname = args[0]
        else:
            commandname = await Helper.waitResponse(self.bot, ctx.message, "What is the command? e.g. ``install``")

        if not config.Commands.fetch(commandname):
            await ctx.send("Command could not be found !")
            return

        config.Commands.deleteBy(name=commandname)
        await ctx.send("Command removed !")

    @modify.command(name="command")
    async def modifycommand(self, ctx, *args):
        if args:
            commandname = args[0]
        else:
            commandname = await Helper.waitResponse(self.bot, ctx.message,
                                                    "What is the command to modify ? e.g. ``install``")

        if config.ReservedCommands.fetch(commandname):
            await ctx.send("This command is special and cannot be modified")
            return

        commandname = commandname.lower()
        query = config.Commands.selectBy(name=commandname)
        results = list(query)
        if not results:
            createcommand = await Helper.waitResponse(self.bot, ctx.message,
                                                      "Command could not be found ! Do you want to create it ?")
            if createcommand.lower() in ["0", "false", "no", "off"]:
                await ctx.send("Understood. Aborting")
                return
        if len(args) == 2:
            response = args[1]
        elif len(args) > 1:
            response = " ".join(args[1:])
        else:
            response = await Helper.waitResponse(self.bot, ctx.message, "What is the response? e.g. ``Hello there`` "
                                                                        "or an image or link to an image")

        if not results:
            config.Commands(name=commandname, content=response)
            await ctx.send("Command '" + commandname + "' added !")
        else:
            results[0].content = response
            await ctx.send("Command '" + commandname + "' modified !")

    @add.command(name="crash")
    async def addcrash(self, ctx, *args):
        if len(args) > 3:
            ctx.send("Please put your parameters between double quotes `\"`.")
            return
        if len(args) > 0:
            name = args[0]
        else:
            name = await Helper.waitResponse(self.bot, ctx.message, "What would you like to name this known "
                                                                    "crash? e.g. ``CommandDave``")
        name = name.lower()

        if config.Crashes.fetch(name):
            await ctx.send("A crash with this name already exists")
            return

        if len(args) > 1:
            crash = args[1]
        else:
            crash = await Helper.waitResponse(self.bot, ctx.message,
                                              "What is the string to search for in the crash logs ? e.g. \"Assertion "
                                              "failed: ObjectA == nullptr\"")
        if len(args) > 2:
            response = args[2]
        else:
            response = await Helper.waitResponse(self.bot, ctx.message,
                                                 "What response do you want it to provide? e.g. ``Thanks for saying my "
                                                 "keywords {user}`` (use {user} to ping the user)")

        config.Crashes(name=name, crash=crash, response=response)
        await ctx.send("Known crash '" + name + "' added!")

    @remove.command(name="crash")
    async def removecrash(self, ctx, *args):
        if args:
            name = args[0]
        else:
            name = await Helper.waitResponse(self.bot, ctx.message, "Which known crash do you want to remove ?")

        if not config.Crashes.fetch(name):
            await ctx.send("Crash could not be found!")
            return

        config.Crashes.deleteBy(name=name)
        await ctx.send("Crash removed!")

    @add.command(name="dialogflow")
    async def adddialogflow(self, ctx, id: str, response: typing.Union[bool, str], has_followup: bool, *args):
        if len(args) == 0:
            data = False
        else:
            data = {arg.split('=')[0]: arg.split('=')[1] for arg in args}

        if response == True:
            await ctx.send("Response should be a string or False (use the response from dialogflow)")
            return

        if config.Dialogflow.fetch(id, data):
            should_delete = await Helper.waitResponse(self.bot, ctx.message,
                                                      "Dialogflow response with this parameters already exists. Do you want to replace it? (Yes/No)")
            should_delete = should_delete.lower()
            if should_delete == 'no' or should_delete == 'n' or should_delete == 'false':
                return
            await self.removedialogflow(ctx, id, *args)

        config.Dialogflow(intent_id=id, data=data, response=response, has_followup=has_followup)
        await ctx.send(
            "Dialogflow response for '" + id + "' (" + (json.dumps(data) if data else 'any data') + ") added!")

    @remove.command(name="dialogflow")
    async def removedialogflow(self, ctx, id: str, *args):
        if len(args) == 0:
            data = False
        else:
            data = {arg.split('=')[0]: arg.split('=')[1] for arg in args}

        if not config.Dialogflow.fetch(id, data):
            await ctx.send("Couldn't find the dialogflow reply")
            return

        config.Dialogflow.deleteBy(intent_id=id, data=data)
        await ctx.send("Dialogflow reply deleted")

    @add.command(name="dialogflowChannel")
    async def adddialogflowchannel(self, ctx, *args):
        if ctx.message.channel_mentions:
            id = int(ctx.message.channel_mentions[0].id)
        else:
            if len(args) > 0:
                id = int(args[0])
            else:
                id = int(await Helper.waitResponse(self.bot, ctx.message, "What is the ID for the channel? e.g. "
                                                                          "``709509235028918334``"))
        if config.DialogflowChannels.fetch(id):
            await ctx.send("This channel is already a dialogflow channel")
            return

        config.DialogflowChannels(channel_id=id)
        await ctx.send("Dialogflow channel " + self.bot.get_channel(id).mention + " added!")

    @remove.command(name="dialogflowChannel")
    async def removedialogflowchannel(self, ctx, *args):
        if ctx.message.channel_mentions:
            id = int(ctx.message.channel_mentions[0].id)
        else:
            if len(args) > 0:
                id = int(args[0])
            else:
                id = int(await Helper.waitResponse(self.bot, ctx.message, "What is the ID for the channel? e.g. "
                                                                          "``709509235028918334``"))
        index = 0
        if config.DialogflowChannels.fetch(id):
            config.DialogflowChannels.deleteBy(channel_id=id)
            await ctx.send("Dialogflow Channel removed!")
        else:
            await ctx.send("Dialogflow channel could not be found!")

    @add.command(name="dialogflowRole")
    async def adddialogflowrole(self, ctx, *args):
        if ctx.message.role_mentions:
            id = int(ctx.message.role_mentions[0].id)
        else:
            if len(args) > 0:
                id = int(args[0])
            else:
                id = int(await Helper.waitResponse(self.bot, ctx.message, "What is the ID for the role? e.g. "
                                                                          "``809710343533232129``"))

        if config.DialogflowExceptionRoles.fetch(id):
            await ctx.send("This role is already a dialogflow exception role")
            return

        config.DialogflowExceptionRoles(role_id=id)
        await ctx.send("Dialogflow role " + ctx.message.guild.get_role(id).name + " added!")

    @remove.command(name="dialogflowRole")
    async def removedialogflowrole(self, ctx, *args):
        if ctx.message.role_mentions:
            id = int(ctx.message.role_mentions[0].id)
        else:
            if len(args) > 0:
                id = int(args[0])
            else:
                id = int(await Helper.waitResponse(self.bot, ctx.message, "What is the ID for the role? e.g. "
                                                                          "``809710343533232129``"))
        index = 0
        if config.DialogflowExceptionRoles.fetch(id):
            config.DialogflowExceptionRoles.deleteBy(role_id=id)
            await ctx.send("Dialogflow role removed!")
        else:
            await ctx.send("Dialogflow role could not be found!")

    @set.command(name="NLP_state")
    async def setNLPstate(self, ctx, *args):
        if len(args) > 0:
            data = args[0]
        else:
            data = await Helper.waitResponse(self.bot, ctx.message, "Should the NLP be on or off ?")
        if data.lower() in ["0", "false", "no", "off"]:
            config.Misc.set_dialogflow_state(False)
            await ctx.send("The NLP is now off !")
        else:
            config.Misc.set_dialogflow_state(True)
            await ctx.send("The NLP is now on !")

    @set.command(name="NLP_debug")
    async def setNLPdebug(self, ctx, *args):
        if len(args) > 0:
            data = args[0]
        else:
            data = await Helper.waitResponse(self.bot, ctx.message, "Should the NLP be in debugging mode ?")
        if data.lower() in ["0", "false", "no", "off"]:
            config.Misc.set_dialogflow_debug_state(False)
            await ctx.send("The NLP debugging mode is now off !")
        else:
            config.Misc.set_dialogflow_debug_state(True)
            await ctx.send("The NLP debugging mode is now on !")

    @set.command(name="welcome_message")
    async def setwelcomemessage(self, ctx, *args):
        if len(args) > 0:
            data = " ".join(args)
        else:
            data = await Helper.waitResponse(self.bot, ctx.message, "What should the welcome message be ? (Anything "
                                                                    "under 10 characters will completely disable the "
                                                                    "mesage)")
        if len(data) < 10:
            config.Misc.set_welcome_message("")
            await ctx.send("The welcome message is now disabled")
        else:
            config.Misc.set_welcome_message(data)
            await ctx.send("The welcome message has been changed !")

    @set.command(name="latest_info")
    async def setlatestinfo(self, ctx, *args):
        if len(args) > 0:
            data = " ".join(args)
        else:
            data = await Helper.waitResponse(self.bot, ctx.message, "What should the welcome message be ? (Anything "
                                                                    "under 10 characters will completely disable the "
                                                                    "mesage)")
        if len(data) < 10:
            config.Misc.set_latest_info("")
            await ctx.send("The latest info message is now disabled")
        else:
            config.Misc.set_latest_info(data)
            await ctx.send("The latest info message has been changed !")

    @commands.command()
    @commands.check(t3_only)
    async def saveconfig(self, ctx, *args):
        if not ctx.author.dm_channel:
            await ctx.author.create_dm()
        try:
            await ctx.author.dm_channel.send(content="WARNING : THIS IS OUTDATED, config is now managed via the DB",
                                             file=discord.File(open("../config/config.json", "r"),
                                                               filename="config.json"))
            await ctx.message.add_reaction("✅")
        except:
            await ctx.send("I was unable to send you a direct message. Please check your discord "
                           "settings regarding those !")

    @commands.command()
    @commands.check(mod_only)
    async def engineers(self, ctx, *args):
        if ctx.message.channel_mentions:
            id = int(ctx.message.channel_mentions[0].id)
        else:
            if args:
                id = int(args[0])
            else:
                id = int(await Helper.waitResponse(self.bot, ctx.message,
                                                   "What is the ID for the channel? e.g. ``709509235028918334``"))
        config.Misc.set_filter_channel(id)
        await ctx.send(
            "The filter channel for the engineers is now " + self.bot.get_channel(int(id)).mention + "!")

    @commands.command()
    @commands.check(mod_only)
    async def moderators(self, ctx, *args):
        if ctx.message.channel_mentions:
            id = int(ctx.message.channel_mentions[0].id)
        else:
            if args:
                id = int(args[0])
            else:
                id = int(await Helper.waitResponse(self.bot, ctx.message,
                                                   "What is the ID for the channel? e.g. ``709509235028918334``"))
        config.Misc.set_mod_channel(id)
        await ctx.send(
            "The filter channel for the moderators is now " + self.bot.get_channel(int(id)).mention + "!")

    @commands.command()
    @commands.check(mod_only)
    async def githook(self, ctx, *args):
        if ctx.message.channel_mentions:
            id = int(ctx.message.channel_mentions[0].id)
        else:
            if args:
                id = int(args[0])
            else:
                id = int(await Helper.waitResponse(self.bot, ctx.message,
                                                   "What is the ID for the channel? e.g. ``709509235028918334``"))
        config.Misc.set_githook_channel(id)
        await ctx.send(
            "The channel for the github hooks is now " + self.bot.get_channel(int(id)).mention + "!")

    @commands.command()
    @commands.check(mod_only)
    async def prefix(self, ctx, *args):
        if not args:
            await ctx.send("Please specify a prefix")
            return
        config.Misc.set_prefix(args[0])
        self.bot.command_prefix = args[0]
        await ctx.send("Prefix changed to " + args[0])
