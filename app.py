#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import logging
from logging.handlers import WatchedFileHandler
import os
import time
import json as js
import requests

from sanic import Sanic
from sanic.response import text, json
from config import settings
from modules.qa_module.methods import get_next_question

# enable logging
project_path = os.path.dirname(os.path.abspath(__file__))
logdir_path = os.path.join(project_path, "logs")
logfile_path = os.path.join(logdir_path, "bot.log")

if not os.path.exists(logdir_path):
    os.makedirs(logdir_path)

logfile_handler = logging.handlers.WatchedFileHandler(logfile_path, 'a', 'utf-8')
logging.basicConfig(format='[%(asctime)s] [%(name)s] [%(levelname)s] - %(message)s',
                    level=logging.INFO, handlers=[logfile_handler])
logging.getLogger("telegram").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

app = Sanic(__name__)

# Facebook Bot settings
PAT = settings.PAT
VERIFY_TOKEN = settings.VERIFY_TOKEN

# Use this section to Do API calls to push data wherever needed..in this case telegram channel
TELEGRAM_BOT_NAME = settings.TELEGRAM_BOT_NAME
URL = "https://api.telegram.org/bot" + settings.TELEGRAM_BOT_TOKEN
# Set channel id's
DOCTORS_ROOM_TG = settings.DOCTORS_ROOM_TG
PSYCHOLOGIST_ROOM_TG = settings.PSYCHOLOGIST_ROOM_TG
HELPER_ROOM_TG = settings.HELPER_ROOM_TG

# Webhook url
WEBHOOK = settings.WEBHOOK

# USER_DATA handles all the messages coming from messenger
USER_DATA = {}

# This determines the positional state of the happy_path
CURRENT_INTENT = "CURRENT_INTENT"
NEXT_INTENT = "NEXT_INTENT"

# These intents are set throughout the conversation as the user makes his choices
PROFILE = "PROFILE"
REPLY = "REPLY"
LANGUAGE = "LANGUAGE"
LANGUAGE_CHOICE = ['English', 'Russian', 'Spanish']
START_OVER = "START_OVER"
STORY = "STORY"
MEDIA = "MEDIA"
ATTACHMENTS = "ATTACHMENTS"
IMAGE = "IMAGE"
VIDEO = "VIDEO"
VIDEO_FLAG = "VIDEO_FLAG"
AUDIO = "AUDIO"
LOCATION = "LOCATION"
LOCATION_FLAG = "LOCATION_FLAG"
LEGAL = "LEGAL"
EMERGENCY_OR_HELP = "EMERGENCY_OR_HELP"
HELPING = "HELPING"
NEW_MEMBER = "NEW_MEMBER"
MEDICAL_OR_PSYCHOLOGICAL = "MEDICAL_OR_PSYCHOLOGICAL"
PSYCHOLOGICAL = "PSYCHOLOGICAL"
PSYCHOLOGICAL_WAIT = "PSYCHOLOGICAL_WAIT"
PSYCHOLOGICAL_FOUND = "PSYCHOLOGICAL_FOUND"
PSYCHOLOGICAL_QA = "PSYCHOLOGICAL_QA"
MEDICAL = "MEDICAL"
MEDICAL_WAIT = "MEDICAL_WAIT"
MEDICAL_FOUND = "MEDICAL_FOUND"
MEDICAL_QA = "MEDICAL_QA"
QA_FINISH = "QA_FINISH"
WAIT_TIMER = "WAIT_TIMER"
CONSULTATION = "CONSULTATION"
CONSULTATION_FINISHED = "CONSULTATION_FINISHED"
CONSULTANT = "CONSULTANT"
CONSULTANT_REPLY = "CONSULTANT_REPLY"
CONSULTANT_LATEST = "CONSULTANT_LATEST"
CHAT_INSTANCE = "CHAT_INSTANCE"
CHAT_INSTANCE_LATEST = "CHAT_INSTANCE_LATEST"
DONE = "DONE"
CANCEL = "CANCEL"
FINISH = "FINISH"

# Load the default language
f = open("locales/en_US.json", "r")
_en_US = js.loads(f.read())
f.close()
# Load the other languages
f = open("locales/ru_RU.json", "r")
_ru_RU = js.loads(f.read())
f.close()
f = open("locales/es_ES.json", "r")
_es_ES = js.loads(f.read())
f.close()

# Get QA list for medical assessment
QA = { "en": {}, "de": {}}
# QA = []
# for q in range(len(_en_US["medical_assessment"])):
#     QA.append("Q{}".format(q+1))


@app.route('/', methods=['GET'])
async def handle_verification(request):
    # Verifies facebook webhook subscription
    # Successful when verify_token is same as token sent by facebook app

    if request.args.get('hub.verify_token', '') == VERIFY_TOKEN:
        logger.info("succefully verified")
        # Set a get started button
        get_started()
        return text(request.args.get('hub.challenge', ''))
    else:
        logger.error("Wrong verification token!")
        return text("Wrong validation token")


@app.route('/', methods=['POST'])
async def handle_message(request):
    # Performance info
    logger.info("post received - {}".format(time.monotonic()))

    # Handle messages sent by facebook messenger to the application
    data = request.json
    logger.info(data)

    # Facebook message
    if "object" in data:
        handle_fb_message(data)
    # Telegram message
    elif "update_id" in data:
        handle_tg_message(data)

    return text("ok")


def handle_fb_message(data):
    if data["object"] == "page":
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                if messaging_event.get("message"):
                    sender_id = messaging_event["sender"]["id"]

                    # If the user ID is unknown, add a new key
                    if sender_id not in USER_DATA:
                        USER_DATA[sender_id] = {}
                        # Get user profile only once
                        get_user_profile(sender_id)

                    # New user starts from the beginning
                    if START_OVER not in USER_DATA[sender_id]:
                        USER_DATA[sender_id][START_OVER] = True
                        USER_DATA[sender_id][ATTACHMENTS] = {}

                    recipient_id = messaging_event["recipient"]["id"]

                    # Capture what the user said, and handle accordingly
                    # Text
                    if "text" in messaging_event["message"]:
                        message_text = messaging_event["message"]["text"]
                        USER_DATA[sender_id][REPLY] = message_text
                        conversation_handler(sender_id)
                    # Attachments
                    elif "attachments" in messaging_event["message"]:
                        USER_DATA[sender_id][MEDIA] = "Yes"
                        USER_DATA[sender_id][REPLY] = "attachment"
                        message_attachments = messaging_event["message"]["attachments"]
                        for _attachment in message_attachments:
                            if _attachment["type"] == "image":
                                USER_DATA[sender_id][ATTACHMENTS][IMAGE] = _attachment["payload"]["url"]
                            elif _attachment["type"] == "audio":
                                USER_DATA[sender_id][ATTACHMENTS][AUDIO] = _attachment["payload"]["url"]
                            elif _attachment["type"] == "video":
                                USER_DATA[sender_id][ATTACHMENTS][VIDEO] = _attachment["payload"]["url"]
                            elif _attachment["type"] == "location":
                                try:
                                    # Facebook sends a Bing URL as attachment for location
                                    # Below is guess work, will add button functionality to extract lat/lon properly
                                    gps = _attachment["payload"]["url"]
                                    a = gps.split('where1%3D')
                                    b = a[1].split('%252C%2B')
                                    c = b[1].split('%26FORM%')
                                    USER_DATA[sender_id][ATTACHMENTS][LOCATION] = {"latitude": b[0], "longitude": c[0]}
                                except Exception as e:
                                    USER_DATA[sender_id][ATTACHMENTS][LOCATION] = _attachment["payload"]["url"]

                        # Check if it is the beginning of a conversation
                        if USER_DATA[sender_id][START_OVER]:
                            USER_DATA[sender_id][START_OVER] = False
                            # Set a default language
                            USER_DATA[sender_id][LANGUAGE] = 'English'
                            language(sender_id)
                            # Set the next intent for the conversation
                            USER_DATA[sender_id][CURRENT_INTENT] = LANGUAGE

                        # after attachment conversation should continue as normal
                        USER_DATA[sender_id][NEXT_INTENT] = USER_DATA[sender_id][CURRENT_INTENT]
                        USER_DATA[sender_id][CURRENT_INTENT] = ATTACHMENTS
                        conversation_handler(sender_id)


def handle_tg_message(data):
    if "message" in data:
        # Handle text messages from TG
        if "text" in data["message"]:
            consultant = data["message"]["from"]["id"]
            reply = data["message"]["text"]

            # Check for Commands
            # Start of conversation
            if "/start" in reply:
                try:
                    sender_id = reply.split()
                    sender_id = sender_id[1]

                    print(sender_id)

                    # Doctor has connected, let the user know
                    if USER_DATA:
                        USER_DATA[sender_id][CONSULTATION][CONSULTANT] = consultant
                        # Set the latest consultant that accepted the case for the user
                        USER_DATA[sender_id][CONSULTANT_LATEST] = consultant
                        # Check the current room the user is in, according to the user's latest intent
                        if USER_DATA[sender_id][CURRENT_INTENT] == PSYCHOLOGICAL_WAIT:
                            USER_DATA[sender_id][CURRENT_INTENT] = PSYCHOLOGICAL_FOUND
                            USER_DATA[sender_id][PSYCHOLOGICAL_FOUND] = True
                            psychological_found(sender_id)
                        elif USER_DATA[sender_id][CURRENT_INTENT] == MEDICAL_WAIT:
                            USER_DATA[sender_id][CURRENT_INTENT] = MEDICAL_FOUND
                            USER_DATA[sender_id][MEDICAL_FOUND] = True
                            medical_found(sender_id)

                    # Doctor cannot have one-on-one conversations with multiple-users
                    # If doctor accepts a new case, then end the conversation with the other users
                    for user in USER_DATA:
                        if CONSULTANT_LATEST in USER_DATA[user]:
                            # Skip for current accepted user
                            if USER_DATA[sender_id][CONSULTANT_LATEST] == consultant:
                                continue
                            # For the rest of the users, let them know the doctor has left
                            if USER_DATA[user][CONSULTANT_LATEST] == consultant:
                                payload = {"text": "The conversation ended."}
                                send_message(sender_id, payload)
                                # Clear the consultation section in the context
                                USER_DATA[sender_id].pop(CONSULTANT_LATEST)
                                USER_DATA[sender_id].pop(CONSULTATION)
                                # Let the user start over
                                USER_DATA[sender_id][CURRENT_INTENT] = FINISH
                            # This will not be reached, but it is there anyway
                            else:
                                payload = "The user has left the room."
                                send_message_to_telegram(consultant, payload)
                # If TG user press the same /start command twice in the assigned case
                except Exception as e:
                    payload = "Please use the start command only once per acceptance."
                    send_message_to_telegram(consultant, payload)

            # Doctor ended the conversation
            elif "/stop" in reply:
                # Find the correct user in the context
                for sender_id in USER_DATA:
                    if CONSULTANT_LATEST in USER_DATA[sender_id]:
                        if USER_DATA[sender_id][CONSULTANT_LATEST] == consultant:
                            USER_DATA[sender_id][CONSULTATION][CONSULTANT_REPLY] = reply
                            payload = {"text": "The conversation ended."}
                            send_message(sender_id, payload)
                            # Clear the consultation section in the context
                            USER_DATA[sender_id].pop(CONSULTANT_LATEST)
                            USER_DATA[sender_id].pop(CONSULTATION)
                            # Let the user start over
                            USER_DATA[sender_id][CURRENT_INTENT] = FINISH

            # Chat in progress
            else:
                # Find the correct user in the context
                _user_is_there = False
                for sender_id in USER_DATA:
                    if CONSULTANT_LATEST in USER_DATA[sender_id]:
                        if USER_DATA[sender_id][CONSULTANT_LATEST] == consultant:
                            _user_is_there = True
                            USER_DATA[sender_id][CONSULTATION][CONSULTANT_REPLY] = reply
                            payload = {"text": reply}
                            send_message(sender_id, payload)
                if _user_is_there is False:
                    payload = "The user has left the room."
                    send_message_to_telegram(consultant, payload)

        elif "callback_query" in data:
            # Answer the callback_query
            par = {
                "callback_query_id": data["callback_query"]["id"],
                "text": "reporting {}. Thank you for the report.".format(data["callback_query"]["data"]),
                "show_alert": True
            }
            r = requests.post(url=URL + "/answerCallbackQuery",
                              headers={"Content-Type": "application/json"},
                              data=js.dumps(par))

            logger.info(r.json())

            sender_id = data["callback_query"]["data"]
            if sender_id in USER_DATA:
                payload = {"text": "Your data has been reported, we'll get back to you. Goodbye."}
                send_message(sender_id, payload)
                # Clear all user data
                USER_DATA.pop(sender_id)


def get_user_profile(sender_id):
    # Get user profile using facebook graph API
    par = {
        "access_token": PAT,
        "fields": "first_name,last_name,profile_pic"}
    r = requests.get(url="https://graph.facebook.com/" + sender_id, params=par)

    USER_DATA[sender_id][PROFILE] = r.json()
    logger.info("New FB user - {}".format(USER_DATA[sender_id][PROFILE]))

    return json(r.content)


def set_telegram_webhook():
    par = {
        "url": WEBHOOK
    }
    r = requests.get(url=URL + "/setWebhook", params=par)

    logger.info(r.content)

    return


def get_started():
    # Sending response back to the user using facebook graph API
    r = requests.post("https://graph.facebook.com/v2.6/me/messages",
                      params={"access_token": PAT},
                      headers={"Content-Type": "application/json"},
                      data=js.dumps({
                          "payload": "Get Started"
                      }))

    return json(r.content)


def send_message(sender_id, payload):
    # Performance info
    logger.info("response sending.. - {}".format(time.monotonic()))

    # Sending response back to the user using facebook graph API
    r = requests.post("https://graph.facebook.com/v2.6/me/messages",
                      params={"access_token": PAT},
                      headers={"Content-Type": "application/json"},
                      data=js.dumps({
                          "recipient": {"id": sender_id},
                          "message": payload
                      }))

    # Performance info
    logger.info("response sent - {}".format(time.monotonic()))

    return json(r.content)


def send_media(sender_id, payload):
    # Performance info
    logger.info("response sending attachment.. - {}".format(time.monotonic()))
    # Sending response back to the user using facebook graph API
    r = requests.post("https://graph.facebook.com/v2.6/me/messages",
                      params={"access_token": PAT},
                      headers={"Content-Type": "application/json"},
                      data=js.dumps({
                          "recipient": {"id": sender_id},
                          "message": {
                              "attachment": {
                                  "type": "template",
                                  "payload": {
                                      "template_type": "media",
                                      "elements": [
                                          {
                                              "media_type": "image",
                                              "url": payload
                                          }
                                      ]
                                  }
                              }
                          }
                      }))

    # Performance info
    logger.info("response attachment sent - {}".format(time.monotonic()))

    return json(r.content)


def send_message_to_telegram(user_id, payload):
    par = {
        "chat_id": user_id,
        "text": payload
    }
    r = requests.get(url=URL + "/sendMessage", params=par)

    return


def conversation_handler(sender_id):
    # This portion handles the flow logic of the conversation per user based on the user intents
    # Check if it is the beginning of a conversation
    if USER_DATA[sender_id][START_OVER]:
        USER_DATA[sender_id][START_OVER] = False
        # Set a default language
        USER_DATA[sender_id][LANGUAGE] = 'English'
        language(sender_id)
        # Set the next intent for the conversation
        USER_DATA[sender_id][CURRENT_INTENT] = LANGUAGE

    # Handle the messages according to the conversation flow
    else:
        # Command handler
        if USER_DATA[sender_id][REPLY] == "Stop":
            # Set the next intent for the conversation
            USER_DATA[sender_id][CURRENT_INTENT] = CANCEL

        # Handle all the intents from the flow
        # Get and set language, preferably this should come from user locale
        if USER_DATA[sender_id][CURRENT_INTENT] == LANGUAGE:
            if USER_DATA[sender_id][REPLY] in ['English', 'Russian', 'Spanish']:
                USER_DATA[sender_id][LANGUAGE] = USER_DATA[sender_id][REPLY]
                # welcome(sender_id)
                legal(sender_id)
                # Set the next intent for the conversation
                #USER_DATA[sender_id][CURRENT_INTENT] = STORY
                USER_DATA[sender_id][CURRENT_INTENT] = LEGAL

            else:
                unknown(sender_id)
                language(sender_id)

        # Get the user story
        elif USER_DATA[sender_id][CURRENT_INTENT] == STORY:
            USER_DATA[sender_id][STORY] = USER_DATA[sender_id][REPLY]
            media(sender_id)
            #emergency_or_help(sender_id)
            # Set the next intent for the conversation
            USER_DATA[sender_id][CURRENT_INTENT] = MEDIA
            #USER_DATA[sender_id][CURRENT_INTENT] = EMERGENCY_OR_HELP

        # Get the user media
        elif USER_DATA[sender_id][CURRENT_INTENT] == MEDIA:
            USER_DATA[sender_id][MEDIA] = USER_DATA[sender_id][REPLY]
            #legal(sender_id)
            medical(sender_id)
            # Set the next intent for the conversation
            #USER_DATA[sender_id][CURRENT_INTENT] = LEGAL
            USER_DATA[sender_id][CURRENT_INTENT] = MEDICAL

        # Get the disclaimer reply
        elif USER_DATA[sender_id][CURRENT_INTENT] == LEGAL:
            if USER_DATA[sender_id][REPLY] in ['Accept', 'accept', 'принимать', 'Aceptar', 'aceptar']:
                USER_DATA[sender_id][LEGAL] = USER_DATA[sender_id][REPLY]
                #emergency_or_help(sender_id)
                welcome(sender_id)
                # Set the next intent for the conversation
                # USER_DATA[sender_id][CURRENT_INTENT] = EMERGENCY_OR_HELP
                USER_DATA[sender_id][CURRENT_INTENT] = STORY

            elif USER_DATA[sender_id][REPLY] in ['Reject', 'reject', 'отклонять', 'Rechazar', 'rechazar']:
                USER_DATA[sender_id][LEGAL] = USER_DATA[sender_id][REPLY]
                bye(sender_id)
                # Set the next intent for the conversation
                USER_DATA[sender_id][CURRENT_INTENT] = FINISH
                # Clear all user data
                USER_DATA.pop(sender_id)

            else:
                unknown(sender_id)
                legal(sender_id)

        # Check if user wants to help or not
        elif USER_DATA[sender_id][CURRENT_INTENT] == EMERGENCY_OR_HELP:
            if USER_DATA[sender_id][REPLY] in ['Yes', 'yes', 'да', 'Sí']:
                USER_DATA[sender_id][EMERGENCY_OR_HELP] = USER_DATA[sender_id][REPLY]
                medical_or_psychological(sender_id)
                # Set the next intent for the conversation
                USER_DATA[sender_id][CURRENT_INTENT] = MEDICAL_OR_PSYCHOLOGICAL

            elif USER_DATA[sender_id][REPLY] in ['No', 'no', 'нет']:
                USER_DATA[sender_id][EMERGENCY_OR_HELP] = USER_DATA[sender_id][REPLY]
                helping(sender_id)
                # Set the next intent for the conversation
                USER_DATA[sender_id][CURRENT_INTENT] = HELPING

            else:
                unknown(sender_id)
                emergency_or_help(sender_id)

        # Check if user really wants to help or not
        elif USER_DATA[sender_id][CURRENT_INTENT] == HELPING:
            if USER_DATA[sender_id][REPLY] in ['Yes', 'yes', 'да', 'Sí']:
                USER_DATA[sender_id][HELPING] = USER_DATA[sender_id][REPLY]
                new_member_info(sender_id)
                # Set the next intent for the conversation
                USER_DATA[sender_id][CURRENT_INTENT] = NEW_MEMBER

            elif USER_DATA[sender_id][REPLY] in ['No', 'no', 'нет']:
                USER_DATA[sender_id][EMERGENCY_OR_HELP] = USER_DATA[sender_id][REPLY]
                bye(sender_id)
                # Set the next intent for the conversation
                USER_DATA[sender_id][CURRENT_INTENT] = FINISH

            else:
                unknown(sender_id)
                helping(sender_id)

        # Ask new member for info
        elif USER_DATA[sender_id][CURRENT_INTENT] == NEW_MEMBER:
            USER_DATA[sender_id][NEW_MEMBER] = USER_DATA[sender_id][REPLY]
            new_member_confirm(sender_id)
            # Set the next intent for the conversation
            USER_DATA[sender_id][CURRENT_INTENT] = FINISH
            bye(sender_id)
            # Clear all user data
            USER_DATA.pop(sender_id)

        # Check if user wants medical or psychological help
        elif USER_DATA[sender_id][CURRENT_INTENT] == MEDICAL_OR_PSYCHOLOGICAL:
            if USER_DATA[sender_id][REPLY] in ['Yes', 'yes', 'да', 'Sí']:
                USER_DATA[sender_id][MEDICAL_OR_PSYCHOLOGICAL] = USER_DATA[sender_id][REPLY]
                medical(sender_id)
                # Set the next intent for the conversation
                USER_DATA[sender_id][CURRENT_INTENT] = MEDICAL

            elif USER_DATA[sender_id][REPLY] in ['No', 'no', 'нет']:
                USER_DATA[sender_id][MEDICAL_OR_PSYCHOLOGICAL] = USER_DATA[sender_id][REPLY]
                psychological(sender_id)
                # Set the next intent for the conversation
                USER_DATA[sender_id][CURRENT_INTENT] = PSYCHOLOGICAL

            else:
                unknown(sender_id)
                medical_or_psychological(sender_id)

        # Do psychological assessment
        elif USER_DATA[sender_id][CURRENT_INTENT] == PSYCHOLOGICAL:
            USER_DATA[sender_id][PSYCHOLOGICAL] = USER_DATA[sender_id][REPLY]
            psychological_assessment(sender_id)
            # Set the next intent for the conversation
            USER_DATA[sender_id][CURRENT_INTENT] = PSYCHOLOGICAL_WAIT

        # Do a psychological case assignment
        elif USER_DATA[sender_id][CURRENT_INTENT] == PSYCHOLOGICAL_WAIT:
            # If there is no doctor connected, then continue to wait
            if CONSULTATION in USER_DATA[sender_id]:
                psychological_wait(sender_id)
                if time.time() - USER_DATA[sender_id][CONSULTATION][WAIT_TIMER] > 15*60:
                    user_waiting(sender_id, PSYCHOLOGIST_ROOM_TG)

            else:
                USER_DATA[sender_id][PSYCHOLOGICAL_QA] = USER_DATA[sender_id][REPLY]
                psychological_case(sender_id)

        # Chatting to the psychologist
        elif USER_DATA[sender_id][CURRENT_INTENT] == PSYCHOLOGICAL_FOUND:
            send_message_to_telegram(USER_DATA[sender_id][CONSULTATION][CONSULTANT], USER_DATA[sender_id][REPLY])

        # Start medical examination
        elif USER_DATA[sender_id][CURRENT_INTENT] == MEDICAL:
            medical_assessment(sender_id)

            # Check if the assessment is complete
            if USER_DATA[sender_id][MEDICAL][MEDICAL_QA] == DONE:
                # Ask for video
                get_video(sender_id)
                # Set the next intent for the conversation
                USER_DATA[sender_id][CURRENT_INTENT] = VIDEO_FLAG

        # Get video
        elif USER_DATA[sender_id][CURRENT_INTENT] == VIDEO_FLAG:
            if USER_DATA[sender_id][REPLY] in ["Skip"]:
                # Ask location
                get_location(sender_id)
                # Set the next intent for the conversation
                USER_DATA[sender_id][CURRENT_INTENT] = LOCATION_FLAG

        # Get location
        elif USER_DATA[sender_id][CURRENT_INTENT] == LOCATION_FLAG:
            if USER_DATA[sender_id][REPLY] in ["Skip"]:
                # Do a medical case assignment
                # Forward the info and assign a case
                medical_case(sender_id)
                # Set the next intent for the conversation
                USER_DATA[sender_id][CURRENT_INTENT] = MEDICAL_WAIT

        # Do a medical case assignment
        elif USER_DATA[sender_id][CURRENT_INTENT] == MEDICAL_WAIT:
            # If there is no doctor connected, then continue to wait
            if CONSULTATION in USER_DATA[sender_id]:
                medical_wait(sender_id)
                if time.time() - USER_DATA[sender_id][CONSULTATION][WAIT_TIMER] > 15*60:
                    user_waiting(sender_id, DOCTORS_ROOM_TG)

        # Chatting to the doctor
        elif USER_DATA[sender_id][CURRENT_INTENT] == MEDICAL_FOUND:
            send_message_to_telegram(USER_DATA[sender_id][CONSULTATION][CONSULTANT], USER_DATA[sender_id][REPLY])

        # Cancelled the Conversation
        elif USER_DATA[sender_id][CURRENT_INTENT] == CANCEL:
            cancel(sender_id)
            # Clear all user data
            USER_DATA.pop(sender_id)

        # Finish the Conversation
        elif USER_DATA[sender_id][CURRENT_INTENT] == FINISH:
            bye(sender_id)
            # Clear all user data
            USER_DATA.pop(sender_id)

        # User sent a attachment
        elif USER_DATA[sender_id][CURRENT_INTENT] == ATTACHMENTS:
            attachment(sender_id)
            USER_DATA[sender_id][CURRENT_INTENT] = USER_DATA[sender_id][NEXT_INTENT]

            # Depending on the current flow, ask the following based on the next intent
            if USER_DATA[sender_id][CURRENT_INTENT] == VIDEO_FLAG:
                # Ask location
                get_location(sender_id)
                # Set the next intent for the conversation
                USER_DATA[sender_id][CURRENT_INTENT] = LOCATION_FLAG
            elif USER_DATA[sender_id][CURRENT_INTENT] == LOCATION_FLAG:
                # Do a medical case assignment
                # Forward the info and assign a case
                medical_case(sender_id)
                # Set the next intent for the conversation
                USER_DATA[sender_id][CURRENT_INTENT] = MEDICAL_WAIT


    # Debug info
    print('\n{}\n'.format(USER_DATA))

    return


def choose_language(lang):
    # Set the user language
    if lang == 'English':
        return _en_US
    elif lang == 'Russian':
        return _ru_RU
    elif lang == 'Spanish':
        return _es_ES


def welcome(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["welcome"]
    send_message(sender_id, payload)

    return


def language(sender_id):
    payload = "https://www.facebook.com/photo.php?fbid=106333174351080"
    send_media(sender_id, payload)
    # Always start with English
    payload = _en_US["language"]
    send_message(sender_id, payload)

    return


def media(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["media"]
    send_message(sender_id, payload)

    return


def get_video(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["coughing"]
    send_message(sender_id, payload)

    return


def get_location(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["location"]
    send_message(sender_id, payload)

    return


def user_waiting(sender_id, channel_id):
    par = {
        "chat_id": channel_id,
        "text": "User {} {} ({}) is waiting for > 15 minutes!".format(USER_DATA[sender_id][PROFILE]["first_name"],
                                                                       USER_DATA[sender_id][PROFILE]["last_name"],
                                                                       sender_id)
    }
    r = requests.get(url=URL + "/sendMessage", params=par)

    return


def attachment(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["attachment"]
    send_message(sender_id, payload)

    return


def send_attachments(sender_id, channel_id):
    # Send facebook profile pic
    par = {
        "chat_id": channel_id,
        "photo": USER_DATA[sender_id][PROFILE]["profile_pic"],
        "caption": "{} {}".format(USER_DATA[sender_id][PROFILE]["first_name"],
                                  USER_DATA[sender_id][PROFILE]["last_name"])
    }
    r = requests.get(url=URL + "/sendPhoto", params=par)

    # Prepare attachments
    for attachment in USER_DATA[sender_id][ATTACHMENTS]:
        if IMAGE in attachment:
            par = {
                "chat_id": channel_id,
                "photo": USER_DATA[sender_id][ATTACHMENTS][IMAGE],
                "caption": "{} {}".format(USER_DATA[sender_id][PROFILE]["first_name"],
                                          USER_DATA[sender_id][PROFILE]["last_name"])
            }

            r = requests.get(url=URL + "/sendPhoto", params=par)
        elif AUDIO in attachment:
            par = {
                "chat_id": channel_id,
                "audio": USER_DATA[sender_id][ATTACHMENTS][AUDIO],
                "caption": "{} {}".format(USER_DATA[sender_id][PROFILE]["first_name"],
                                          USER_DATA[sender_id][PROFILE]["last_name"])
            }
            r = requests.get(url=URL + "/sendAudio", params=par)
        elif VIDEO in attachment:
            par = {
                "chat_id": channel_id,
                "video": USER_DATA[sender_id][ATTACHMENTS][VIDEO],
                "caption": "{} {}".format(USER_DATA[sender_id][PROFILE]["first_name"],
                                          USER_DATA[sender_id][PROFILE]["last_name"])
            }
            r = requests.get(url=URL + "/sendVideo", params=par)

        elif LOCATION in attachment:
            try:
                if "latitude" in USER_DATA[sender_id][ATTACHMENTS][LOCATION]:
                    par = {
                        "chat_id": channel_id,
                        "latitude": USER_DATA[sender_id][ATTACHMENTS][LOCATION]["latitude"],
                        "longitude": USER_DATA[sender_id][ATTACHMENTS][LOCATION]["longitude"]
                    }
                    r = requests.get(url=URL + "/sendLocation", params=par)
                else:
                    par = {
                        "chat_id": channel_id,
                        "text": USER_DATA[sender_id][ATTACHMENTS][LOCATION]}
                    r = requests.get(url=URL + "/sendMessage", params=par)
            except Exception as e:
                par = {
                    "chat_id": channel_id,
                    "text": USER_DATA[sender_id][ATTACHMENTS][LOCATION]}
                r = requests.get(url=URL + "/sendMessage", params=par)

    return


def legal(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["disclaimer"]
    send_message(sender_id, payload)

    return


def emergency_or_help(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["emergency_or_help"]
    send_message(sender_id, payload)

    return


def helping(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["helping"]
    send_message(sender_id, payload)

    return


def new_member_info(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["new_member_info"]
    send_message(sender_id, payload)

    return


def new_member_confirm(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["new_member_confirm"]
    send_message(sender_id, payload)

    # Send attachments
    send_attachments(sender_id, HELPER_ROOM_TG)

    # Match questions and answers after assessment
    exam = "A user wants to help\n\n"
    exam += "Name: {} {}\n".format(USER_DATA[sender_id][PROFILE]["first_name"],
                                   USER_DATA[sender_id][PROFILE]["last_name"])
    exam += "FB UserId: {}\n".format(sender_id)
    exam += "Short story: {}\n".format(USER_DATA[sender_id][STORY])
    exam += "Case description: {}\n".format(USER_DATA[sender_id][NEW_MEMBER])

    # Send info
    par = {
        "chat_id": HELPER_ROOM_TG,
        "text": exam,
        "reply_markup": {"inline_keyboard": [[{"text": "Report User", "callback_data": sender_id}]]}
    }
    r = requests.post(url=URL + "/sendMessage",
                      headers={"Content-Type": "application/json"},
                      data=js.dumps(par))

    return


def medical_or_psychological(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["medical_or_psychological"]
    send_message(sender_id, payload)

    return


def psychological(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["psychological"]
    send_message(sender_id, payload)

    return


def psychological_assessment(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["psychological_assessment"]
    send_message(sender_id, payload)

    return


def psychological_case(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["psychological_case"]
    send_message(sender_id, payload)

    # Send attachments
    send_attachments(sender_id, PSYCHOLOGIST_ROOM_TG)

    # Match questions and answers after assessment
    exam = "A user wants to talk!\n\n"
    exam += "Name: {} {}\n".format(USER_DATA[sender_id][PROFILE]["first_name"],
                                   USER_DATA[sender_id][PROFILE]["last_name"])
    exam += "FB UserId: {}\n".format(sender_id)
    exam += "Short story: {}\n".format(USER_DATA[sender_id][STORY])
    exam += "Case description: {}: {}\n".format(lang["psychological"]["text"], USER_DATA[sender_id][PSYCHOLOGICAL])
    exam += "Assessment: {}\n".format(USER_DATA[sender_id][PSYCHOLOGICAL_QA])

    # Send examination
    par = {
        "chat_id": PSYCHOLOGIST_ROOM_TG,
        "text": exam,
        "reply_markup": {"inline_keyboard": [[{"text": "Assign Case to me",
                                               "url": "https://t.me/{}?start={}".format(TELEGRAM_BOT_NAME, sender_id)},
                                             {"text": "Report User", "callback_data": sender_id}]]}
    }
    r = requests.post(url=URL + "/sendMessage",
                      headers={"Content-Type": "application/json"},
                      data=js.dumps(par))

    USER_DATA[sender_id][CONSULTATION] = {}
    USER_DATA[sender_id][CONSULTATION][WAIT_TIMER] = time.time()

    return


def psychological_wait(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["psychological_wait"]
    send_message(sender_id, payload)

    return


def psychological_found(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["psychological_found"]
    send_message(sender_id, payload)

    return


def payload_prepare(response):
    if "answers" in response:
        # This will build a quick_reply dict to be sent back to facebook
        answers = response["answers"]
        quick_replies = {}
        i = 0
        try:
            for key, values in answers.items():
                quick_replies[str(i)] = {
                    "content_type": "text",
                    "payload": "<POSTBACK_PAYLOAD>",
                    "title": key
                }
                i += 1
            # Add command at the end
            quick_replies[str(i)] = {
                "content_type": "text",
                "payload": "<POSTBACK_PAYLOAD>",
                "title": "Stop"
            }
            payload = {"text": response["text"], "quick_replies": quick_replies}
        except Exception as e:
            payload = {"text": response["text"]}

    else:
        payload = {"text": response["text"]}

    return payload


def check_answer(response, answer):
    if "answers" in response:
        try:
            if response["free"]:
                print("free form answer like a date input")
                return response["answers"]

            elif answer in response["answers"]:
                # return the next question id
                return response["answers"][answer]

            else:
                # check if this is a truncated answer or did the user just type something bogus
                if len(answer) > 19:
                    print("truncation - {} :{}".format(answer, len(answer)))
                    for k in response["answers"]:
                        c = str(k)
                        if answer[0:20] == c[0:20]:
                            # return the next question id
                            return response["answers"][k]

                # User made a mistake
                return None

        except Exception as e:
            print("the supplied user answer is not in the response answers")
            return None
    else:
        print("there is no answers key")
        return None


def medical(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["medical"]
    send_message(sender_id, payload)

    # payload = lang["medical_assessment"]["Q1"]
    # send_message(sender_id, payload)

    # P0 is the entry point for Q&A
    # Add the MEDICAL key if it does not exist
    if MEDICAL not in USER_DATA[sender_id]:
        USER_DATA[sender_id][MEDICAL] = {}
        USER_DATA[sender_id][MEDICAL][MEDICAL_QA] = "P0"

    response = eval(repr(get_next_question(sender_id, "en", USER_DATA[sender_id][MEDICAL][MEDICAL_QA])))
    # Update QA builder
    QA["en"][USER_DATA[sender_id][MEDICAL][MEDICAL_QA]] = response["text"]
    payload = payload_prepare(response)
    send_message(sender_id, payload)

    return


def medical_assessment(sender_id):
    # Example of what this function does in a loop depending on the amount of questions
    # if USER_DATA[sender_id][MEDICAL][MEDICAL_QA] == Q1:
    #     # Record answer
    #     USER_DATA[sender_id][MEDICAL][Q1] = USER_DATA[sender_id][REPLY]
    #     # Set the next intent for the conversation
    #     USER_DATA[sender_id][MEDICAL][MEDICAL_QA] = Q2
    #     payload = BOT_LANGUAGE["medical_assessment"][Q2]
    #     send_message(sender_id, payload)

    lang = choose_language(USER_DATA[sender_id][LANGUAGE])

    # # Add the MEDICAL key if it does not exist
    # if MEDICAL not in USER_DATA[sender_id]:
    #     USER_DATA[sender_id][MEDICAL] = {}
    #     USER_DATA[sender_id][MEDICAL][MEDICAL_QA] = "Q1"
    #
    # for i in range(len(QA)):
    #     # Command handler
    #     if USER_DATA[sender_id][REPLY] == "Stop":
    #         # Set the next intent for the conversation
    #         USER_DATA[sender_id][MEDICAL][MEDICAL_QA] = DONE
    #         USER_DATA[sender_id][CURRENT_INTENT] = CANCEL
    #         break
    #
    #     # Check if the last question was answered
    #     if QA[i] == QA[len(QA)-1]:
    #         # Record answer
    #         USER_DATA[sender_id][MEDICAL][QA[i]] = USER_DATA[sender_id][REPLY]
    #         # Set the next intent for the conversation
    #         USER_DATA[sender_id][MEDICAL][MEDICAL_QA] = DONE
    #         break
    #
    #     # Continue with examination
    #     elif USER_DATA[sender_id][MEDICAL][MEDICAL_QA] == QA[i]:
    #         # Record answer
    #         USER_DATA[sender_id][MEDICAL][QA[i]] = USER_DATA[sender_id][REPLY]
    #         # Set the next intent for the conversation
    #         USER_DATA[sender_id][MEDICAL][MEDICAL_QA] = QA[i+1]
    #         payload = lang["medical_assessment"][QA[i+1]]
    #         send_message(sender_id, payload)
    #         break

    # Command handler
    if USER_DATA[sender_id][REPLY] == "Stop":
        # Set the next intent for the conversation
        USER_DATA[sender_id][MEDICAL][MEDICAL_QA] = DONE
        USER_DATA[sender_id][CURRENT_INTENT] = CANCEL
        payload = lang["qa_finish"]
        send_message(sender_id, payload)

        return

    else:
        # Record answer
        current_question = USER_DATA[sender_id][MEDICAL][MEDICAL_QA]
        USER_DATA[sender_id][MEDICAL][current_question] = USER_DATA[sender_id][REPLY]
        # Check what the next question should be
        response = eval(repr(get_next_question(sender_id, "en", current_question)))

        if response:
            # Update QA builder
            QA["en"][USER_DATA[sender_id][MEDICAL][MEDICAL_QA]] = response["text"]
            next_question = check_answer(response, USER_DATA[sender_id][MEDICAL][current_question])

            if next_question is not None:
                USER_DATA[sender_id][MEDICAL][MEDICAL_QA] = next_question
                if next_question is not None:
                    response = eval(repr(get_next_question(sender_id, "en", next_question)))
                    if response:
                        # Update QA builder
                        QA["en"][USER_DATA[sender_id][MEDICAL][MEDICAL_QA]] = response["text"]
                        payload = payload_prepare(response)
                        send_message(sender_id, payload)
                    # If response is False, end of the assessment is reached
                    else:
                        # Set the next intent for the conversation
                        USER_DATA[sender_id][MEDICAL][MEDICAL_QA] = DONE
                        payload = lang["qa_finish"]
                        send_message(sender_id, payload)

            # User made a mistake
            else:
                # Ask the same question again
                payload = payload_prepare(response)
                send_message(sender_id, payload)

        # If response is False, end of the assessment is reached
        else:
            # Set the next intent for the conversation
            USER_DATA[sender_id][MEDICAL][MEDICAL_QA] = DONE
            USER_DATA[sender_id][CURRENT_INTENT] = CANCEL
            payload = lang["qa_finish"]
            send_message(sender_id, payload)

            return
    return


def medical_case(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["medical_case"]
    send_message(sender_id, payload)

    # Send attachments
    send_attachments(sender_id, DOCTORS_ROOM_TG)

    # Match questions and answers after assessment
    exam = "A user requested medical help!\n\n"
    exam += "Name: {} {}\n".format(USER_DATA[sender_id][PROFILE]["first_name"],
                                   USER_DATA[sender_id][PROFILE]["last_name"])
    exam += "FB UserId: {}\n".format(sender_id)
    exam += "Short story: {}\n".format(USER_DATA[sender_id][STORY])

    for questions in USER_DATA[sender_id][MEDICAL]:
        if questions in QA["en"]:
            exam += "{}: {}\n".format(QA["en"][questions],
                                      USER_DATA[sender_id][MEDICAL][questions])

    # Send examination
    par = {
        "chat_id": DOCTORS_ROOM_TG,
        "text": exam,
        "reply_markup": {"inline_keyboard": [[{"text": "Assign Case to me",
                                               "url": "https://t.me/{}?start={}".format(TELEGRAM_BOT_NAME, sender_id)},
                                             {"text": "Report User", "callback_data": sender_id}]]}
    }
    r = requests.post(url=URL + "/sendMessage",
                      headers={"Content-Type": "application/json"},
                      data=js.dumps(par))

    USER_DATA[sender_id][CONSULTATION] = {}
    USER_DATA[sender_id][CONSULTATION][WAIT_TIMER] = time.time()

    return


def medical_wait(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["medical_wait"]
    send_message(sender_id, payload)

    return


def medical_found(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["medical_found"]
    send_message(sender_id, payload)

    return


def unknown(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["unknown"]
    send_message(sender_id, payload)

    return


def cancel(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["cancel"]
    send_message(sender_id, payload)

    return


def bye(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["bye"]
    send_message(sender_id, payload)

    return


if __name__ == '__main__':
    set_telegram_webhook()
    app.run(host='0.0.0.0', port=8443, debug=False)
