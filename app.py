#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import time
import logging

import asyncio
import aiohttp
from sanic import Sanic
from sanic.response import text, json
from config import settings

# enable logging
project_path = os.path.dirname(os.path.abspath(__file__))
logdir_path = os.path.join(project_path, "logs")
logfile_path = os.path.join(logdir_path, "bot.log")

if not os.path.exists(logdir_path):
    os.makedirs(logdir_path)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logfile_handler = logging.FileHandler(logfile_path, 'a', 'utf-8')
logfile_handler.setLevel(logging.ERROR)
logfile_handler.setFormatter(formatter)
logger.addHandler(logfile_handler)

app = Sanic(__name__)

# Facebook Bot settings
PAT = settings.PAT
VERIFY_TOKEN = settings.VERIFY_TOKEN
# REST Settings
INSTANCE_SECURITY_TOKEN = None
INSTANCE_NAME = None

# Use this section to Do API calls to push data wherever needed..in this case telegram channel

# Temporary cache
CACHE = set()
INLINE_BUTTON = dict()
H = {'content-type': 'application/json'}


async def handle_fb_message(data):
    if data["object"] == "page":
        async with aiohttp.ClientSession() as session:
            for entry in data["entry"]:
                for messaging_event in entry["messaging"]:
                    if messaging_event.get("message"):
                        sender_id = int(messaging_event["sender"]["id"])
                        # REQUIRED PAYLOAD
                        payload = {
                            "security_token": INSTANCE_SECURITY_TOKEN,
                            "via_instance": INSTANCE_NAME,
                            "service_in": "facebook",
                            "user": {
                                "user_id": sender_id
                            },
                            "chat": {
                                "chat_id": sender_id
                            }
                        }

                        # If in cache - don't call the profile
                        if sender_id not in CACHE:
                            CACHE.add(sender_id)
                            # Get user profile using facebook graph API
                            par = {
                                "access_token": PAT,
                                "fields": "first_name,last_name,profile_pic"
                            }
                            async with session.get(f"https://graph.facebook.com/{sender_id}", params=par) as resp:
                                profile = await resp.json()
                                # New FB user log
                                logger.info(f"New FB user - {profile}")
                        else:
                            profile = None

                        if profile is not None:
                            payload["user"]["first_name"] = profile['first_name']
                            payload["user"]["last_name"] = profile['first_name']
                            payload['has_file'] = True
                            payload['has_image'] = True
                            payload['files'] = [{
                                "payload": profile['profile_pic']
                            }]

                        if "text" in messaging_event["message"]:
                            text_ = messaging_event["message"]["text"]

                            if sender_id in INLINE_BUTTON:
                                text_ = INLINE_BUTTON[sender_id].get(text_)
                                INLINE_BUTTON.pop(sender_id)

                            #print(text_)
                            payload["has_message"] = True
                            payload["message"] = {
                                "text": text_
                            }

                        # Attachments
                        # TODO: Take care of attachments

                        async with session.post(f"{settings.SERVER_URL}/api/process_message", json=payload, headers=H) as resp:
                            # DEBUG:
                            ret_value = await resp.json()
                            logger.info(f"Server immediate response: {ret_value}")


@app.route('/webhooks/facebook/in', methods=['GET'])
async def handle_verification(request):
    # Verifies facebook webhook subscription
    # Successful when verify_token is same as token sent by facebook app

    if request.args.get('hub.verify_token', '') == VERIFY_TOKEN:
        logger.info("succefully verified")
        return text(request.args.get('hub.challenge', ''))
    else:
        logger.error("Wrong verification token!")
        return text("Wrong validation token")


@app.route('/webhooks/facebook/in', methods=['POST'])
async def handle_incoming_message(request):
    # Performance info [DEBUG]
    logger.info(f"post received - {time.monotonic()}")

    # Handle messages sent by facebook messenger to the application
    data = request.json
    logger.info(data)

    # Handle message
    await handle_fb_message(data)

    return text("ok")


async def handle_server_message(data):
    # Performance info
    logger.info("response sending.. - {}".format(time.monotonic()))

    payload = {
        "recipient": {
            "id": data['user']['user_id']
        },
        "message": {
            "text": data['message']['text'],
        },
    }

    if data['has_file']:
        payload['message']['attachment'] = {
                                            "type": "template",
                                            "payload": {}
                                            }
        payload['message']['attachment']['payload']["template_type"] = "media"
        payload['message']['attachment']['payload']["elements"] = []
        if data['has_image']:
            for each_file in data['file']:
                media = {
                            "media_type": "image",
                            "url": data['payload']
                        }
                payload['message']['attachment']['payload']["elements"].append(media)

    if data['has_buttons']:
        if data['buttons_type'] == 'inline':
            is_inline = True
        else:
            is_inline = False

        if is_inline:
            # Caching to map inlines to values
            INLINE_BUTTON[data['user']['user_id']] = {}

        payload['message']['quick_replies'] = {}
        for index, each_button in enumerate(data['buttons']):
            if is_inline:
                INLINE_BUTTON[data['user']['user_id']][each_button['text']] = each_button['value']

            payload['message']['quick_replies'][str(index)] = {
                "content_type": "text",
                "payload": "<POSTBACK_PAYLOAD>",
                "title": each_button['text']
            }

    # Sending response back to the user using facebook graph API
    async with aiohttp.ClientSession() as session:
        async with session.post("https://graph.facebook.com/v2.6/me/messages",
                                params={"access_token": PAT},
                                headers={"Content-Type": "application/json"},
                                json=payload) as response:
            logger.info("response sent - {}".format(time.monotonic()))


@app.route('/webhooks/facebook/out', methods=['POST'])
async def handle_outgoing_message(request):
    # Performance info [DEBUG]
    logger.info(f"sending post - {time.monotonic()}")
    # TODO: CHECK SECURITY TOKEN FROM THE SERVER
    # Handle messages sent by server into facebook messenger
    data = request.json
    logger.info(data)

    try:
        # Handle message
        await handle_server_message(data)
    except Exception as e:
        return json({"status": 500, "error": str(e), "timestamp": time.monotonic()})

    return json({"status": 200, "timestamp": time.monotonic()})


async def setup():
    global INSTANCE_SECURITY_TOKEN, INSTANCE_NAME
    data = {
        "security_token": settings.SERVER_SECURITY_TOKEN,
        "url": f"{settings.WEBHOOK}/webhooks/facebook/out"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{settings.SERVER_URL}/api/setup", json=data) as response:
            result = await response.json()
            if result['status'] == 200:
                INSTANCE_SECURITY_TOKEN = result['token']
                INSTANCE_NAME = result['name']


if __name__ == '__main__':
    asyncio.get_event_loop().run_until_complete(setup())
    app.run(host='127.0.0.1', port=8443, debug=False)
