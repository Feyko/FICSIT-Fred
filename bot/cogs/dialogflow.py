import discord.ext.commands as commands
from google.oauth2 import service_account
from google.cloud import dialogflow
import os
import uuid
import asyncio
import json
import config

DIALOGFLOW_AUTH = json.loads(os.environ.get("DIALOGFLOW_AUTH"))
session_client = dialogflow.SessionsClient(
    credentials=service_account.Credentials.from_service_account_info(DIALOGFLOW_AUTH))
DIALOGFLOW_PROJECT_ID = DIALOGFLOW_AUTH['project_id']
SESSION_LIFETIME = 10 * 60  # 10 minutes to avoid repeated false positives


class DialogFlow(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.session_ids = {}

    async def process_message(self, message):
        if message.content.startswith(self.bot.command_prefix):
            return
        if not config.Misc.fetch("dialogflow_state"):
            return
        if not config.Misc.fetch("dialogflow_debug_state"):
            # Trying out global NLP
            # if not config.DialogflowChannels.fetch(message.channel.id):
            #     return
            roles = message.author.roles[1:]
            exception_roles = config.DialogflowExceptionRoles.fetch_all()
            if len(roles) != 0 and len(roles) != len(exception_roles):
                return
            for role in roles:
                if role.id not in exception_roles:
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
        formatted_response = str(dict(response_data)).replace("'", '"')
        query = config.Dialogflow.select(f"dialogflow.intent_id = '{intent_id}' AND ((dialogflow.data IS NULL) "
                                         f"OR dialogflow.data = '{formatted_response}')")
        results = list(query)

        if intent_id == config.Misc.fetch("dialogflow_steam_scam_intent_id"):
            await message.delete()
            return

        if not len(results):
            return

        dialogflow_reply = results[0].as_dict()

        if not dialogflow_reply["response"]:
            await self.bot.reply_to_msg(message, response_text)
        else:
            if dialogflow_reply["response"].startswith(self.bot.command_prefix):
                command_name = dialogflow_reply["response"].lower().lstrip(self.bot.command_prefix).split(" ")[0]
                if command := config.Commands.fetch(command_name):
                    await self.bot.reply_to_msg(message, command.response)

            else:
                await self.bot.reply_to_msg(message, dialogflow_reply["response"])

        if dialogflow_reply["has_followup"]:
            def check(message2):
                return message2.author == message.author and message2.channel == message.channel

            try:
                await self.bot.wait_for('message', timeout=SESSION_LIFETIME, check=check)
            except asyncio.TimeoutError:
                del self.session_ids[message.author.id]
        else:
            del self.session_ids[message.author.id]
