import discord.ext.commands as commands
from google.oauth2 import service_account
from google.cloud import dialogflow
import os
import uuid
import asyncio
import json

DIALOGFLOW_AUTH = json.loads(os.environ.get("DIALOGFLOW_AUTH"))
session_client = dialogflow.SessionsClient(credentials=service_account.Credentials.from_service_account_info(DIALOGFLOW_AUTH))
DIALOGFLOW_PROJECT_ID = DIALOGFLOW_AUTH['project_id']
SESSION_LIFETIME = 10 * 60 # 10 minutes to avoid repeated false positives

class DialogFlow(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session_ids = {}

    async def process_message(self, message):
        if message.content.startswith(self.bot.command_prefix):
            return
        if not self.bot.config["dialogflow state"]:
            return
        if not message.channel.id in self.bot.config["dialogflow_channels"]:
            return
        if not self.bot.config["dialogflow debug state"]:
            roles = message.author.roles[1:]
            if len(roles) != 0 and len(roles) != len(self.bot.config["dialogflow_exception_roles"]):
                return
            for role in roles:
                if role.id not in self.bot.config["dialogflow_exception_roles"]:
                    return

        if message.author.id in self.session_ids:
            session_id = self.session_ids[message.author.id]
        else:
            session_id = uuid.uuid4()
            self.session_ids[message.author.id] = session_id
        
        session = session_client.session_path(DIALOGFLOW_PROJECT_ID, session_id)

        if not message.content:
            return

        text_input = dialogflow.TextInput(text=message.content[0:256], language_code='en')

        query_input = dialogflow.QueryInput(text=text_input)

        response = session_client.detect_intent(request={'session': session, 'query_input': query_input})

        response_text = response.query_result.fulfillment_text
        response_data = response.query_result.parameters
        intent_id = response.query_result.intent.name.split('/')[-1]

        for dialogflowReply in self.bot.config["dialogflow"]:
            if dialogflowReply["id"] == intent_id and (not dialogflowReply["data"] or dialogflowReply["data"] == response_data):
                if not dialogflowReply["response"]:
                    await message.channel.send(message.author.mention + " : " + response_text)
                else:
                    if dialogflowReply["response"].startswith(self.bot.command_prefix):
                        command = dialogflowReply["response"].lower().lstrip(self.bot.command_prefix).split(" ")[0]
                        for automation in self.bot.config["commands"]:
                            if command.lower() == automation["command"].lower():
                                await message.channel.send(automation["response"])
                        
                    else:
                        await message.channel.send(dialogflowReply["response"])

                if dialogflowReply["has_followup"]:
                    def check(message2):
                        return message2.author == message.author and message2.channel == message.channel

                    try:
                        response = await self.bot.wait_for('message', timeout=SESSION_LIFETIME, check=check)
                    except asyncio.TimeoutError:
                        del self.session_ids[message.author.id]
                else:
                    del self.session_ids[message.author.id]
                
                break

      