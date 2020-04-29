#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import logging
import os
import time

import aiohttp
from sanic import Sanic
from sanic.response import text
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

# Use this section to Do API calls to push data wherever needed..in this case telegram channel

# Temporary cache
CACHE = set()
H = {'content-type': 'application/json'}


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
    logger.info("post received - {}".format(time.monotonic()))

    # Handle messages sent by facebook messenger to the application
    data = request.json
    logger.info(data)

    # Handle message
    await handle_fb_message(data)

    return text("ok")


async def handle_fb_message(data):
    if data["object"] == "page":
        async with aiohttp.ClientSession() as session:
            for entry in data["entry"]:
                for messaging_event in entry["messaging"]:
                    if messaging_event.get("message"):
                        sender_id = messaging_event["sender"]["id"]
                        # REQUIRED PAYLOAD
                        payload = {
                            "security_token": settings.INSTANCE_SECURITY_TOKEN,
                            "via_bot": settings.INSTANCE_NAME,
                            "service_in": "facebook",
                            "user": {
                                "user_id": int(sender_id)
                            },
                            "chat": {
                                "chat_id": int(sender_id)
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

                        if "text" in messaging_event["message"]:
                            payload["is_message"] = True
                            payload["message"] = {
                                "text": messaging_event["message"]["text"]
                            }
                            async with session.post(settings.SERVER_URL, json=payload, headers=H) as resp:
                                pass
                                # DEBUG: print(await resp.json())

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8443, debug=False)