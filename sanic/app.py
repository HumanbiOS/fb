import sys
import time
import json as js
import requests

from sanic import Sanic
from sanic.response import text, json


app = Sanic(__name__)

PAT = 'EAArISv5K1gEBAOTgv1jyQYZC0bbQhvaE0naKxliTOhVwFjF3EinFZC5vskFV1xd7G89ZBh2W4MUSx2fBYzsZCeyW92lVvzHlTMmHXZCBjWjuZAtNLUsPG80k6mFxb5mx4ZA8LbJtaN9stU0zSoJpch7q7IzBMxhfA1ZAQbwXHWRaEYIfmIZBwupZCO'
VERIFY_TOKEN = 'thisisarandomstringtotest'

# USER_DATA handles all the messages coming from messenger
USER_DATA = {}

# This determines the positional state of the happy_path
CURRENT_INTENT = "CURRENT_INTENT"

# These intents are set throughout the conversation as the user makes his choices
REPLY = "REPLY"
LANGUAGE = "LANGUAGE"
LANGUAGE_CHOICE = ['English', 'Russian', 'Spanish']
START_OVER = "START_OVER"
STORY = "STORY"
PICTURE = "PICTURE"
LEGAL = "LEGAL"
EMERGENCY_OR_HELP = "EMERGENCY_OR_HELP"
HELPING = "HELPING"
NEW_MEMBER = "NEW_MEMBER"
MEDICAL_OR_PSYCHOLOGICAL = "MEDICAL_OR_PSYCHOLOGICAL"
PSYCHOLOGICAL = "PSYCHOLOGICAL"
PSYCHOLOGICAL_WAIT = "PSYCHOLOGICAL_WAIT"
PSYCHOLOGIST_FOUND = "PSYCHOLOGIST_FOUND"
MEDICAL = "MEDICAL"
MEDICAL_WAIT = "MEDICAL_WAIT"
MEDICAL_FOUND = "MEDICAL_FOUND"
MEDICAL_QA = "MEDICAL_QA"
QA_FINISH = "QA_FINISH"
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
QA = []
for q in range(len(_en_US["medical_assessment"])):
    QA.append("Q{}".format(q+1))


@app.route('/', methods=['GET'])
async def handle_verification(request):
    # Verifies facebook webhook subscription
    # Successful when verify_token is same as token sent by facebook app

    if request.args.get('hub.verify_token', '') == VERIFY_TOKEN:
        print("succefully verified")
        return text(request.args.get('hub.challenge', ''))
    else:
        print("Wrong verification token!")
        return text("Wrong validation token")


@app.route('/', methods=['POST'])
async def handle_message(request):
    # Handle messages sent by facebook messenger to the application
    print("post received - {}".format(time.monotonic()))
    data = request.json
    if data["object"] == "page":
        for entry in data["entry"]:
            for messaging_event in entry["messaging"]:
                if messaging_event.get("message"):
                    sender_id = messaging_event["sender"]["id"]
                    # If the user ID is unknown, add a new key
                    if sender_id not in USER_DATA:
                        USER_DATA[sender_id] = {}

                    # New user starts from the beginning
                    if START_OVER not in USER_DATA[sender_id]:
                        USER_DATA[sender_id][START_OVER] = True

                    recipient_id = messaging_event["recipient"]["id"]

                    # Messages replies must contain text, for now...
                    if "text" not in messaging_event["message"]:
                        continue

                    message_text = messaging_event["message"]["text"]
                    # Capture what the user said, and handle accordingly
                    USER_DATA[sender_id][REPLY] = message_text
                    conversation_handler(sender_id)

    return text("ok")


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
        if USER_DATA[sender_id][REPLY] == "/cancel":
            # Set the next intent for the conversation
            USER_DATA[sender_id][CURRENT_INTENT] = CANCEL

        # Handle all the intents from the flow
        # Get and set language, preferably this should come from user locale
        if USER_DATA[sender_id][CURRENT_INTENT] == LANGUAGE:
            if USER_DATA[sender_id][REPLY] in ['English', 'Russian', 'Spanish']:
                USER_DATA[sender_id][LANGUAGE] = USER_DATA[sender_id][REPLY]
                welcome(sender_id)
                # Set the next intent for the conversation
                USER_DATA[sender_id][CURRENT_INTENT] = STORY

            else:
                unknown(sender_id)
                language(sender_id)

        # Get the user story
        elif USER_DATA[sender_id][CURRENT_INTENT] == STORY:
            USER_DATA[sender_id][STORY] = USER_DATA[sender_id][REPLY]
            picture(sender_id)
            # Set the next intent for the conversation
            USER_DATA[sender_id][CURRENT_INTENT] = PICTURE

        # Get the user picture
        elif USER_DATA[sender_id][CURRENT_INTENT] == PICTURE:
            USER_DATA[sender_id][PICTURE] = USER_DATA[sender_id][REPLY]
            legal(sender_id)
            # Set the next intent for the conversation
            USER_DATA[sender_id][CURRENT_INTENT] = LEGAL

        # Get the disclaimer reply
        elif USER_DATA[sender_id][CURRENT_INTENT] == LEGAL:
            if USER_DATA[sender_id][REPLY] in ['Yes', 'yes', 'да', 'Sí']:
                USER_DATA[sender_id][LEGAL] = USER_DATA[sender_id][REPLY]
                emergency_or_help(sender_id)
                # Set the next intent for the conversation
                USER_DATA[sender_id][CURRENT_INTENT] = EMERGENCY_OR_HELP

            elif USER_DATA[sender_id][REPLY] in ['No', 'no', 'нет']:
                USER_DATA[sender_id][LEGAL] = USER_DATA[sender_id][REPLY]
                bye(sender_id)
                # Set the next intent for the conversation
                USER_DATA[sender_id][CURRENT_INTENT] = FINISH

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
            psychological_case(sender_id)
            # Set the next intent for the conversation
            USER_DATA[sender_id][CURRENT_INTENT] = PSYCHOLOGIST_FOUND

        # Chatting to the psychologist
        elif USER_DATA[sender_id][CURRENT_INTENT] == PSYCHOLOGIST_FOUND:
            USER_DATA[sender_id][PSYCHOLOGIST_FOUND] = True
            psychological_found(sender_id)

            # Set the next intent for the conversation
            USER_DATA[sender_id][CURRENT_INTENT] = FINISH

        # Start medical examination
        elif USER_DATA[sender_id][CURRENT_INTENT] == MEDICAL:
            medical_assessment(sender_id)

        # # Check if medical examination is done
        # elif USER_DATA[sender_id][CURRENT_INTENT] == QA_FINISH:
        #     # Set the next intent for the conversation
        #     USER_DATA[sender_id][CURRENT_INTENT] = MEDICAL_WAIT

        # Do a medical case assignment
        elif USER_DATA[sender_id][CURRENT_INTENT] == MEDICAL_WAIT:

            # Set the next intent for the conversation
            USER_DATA[sender_id][CURRENT_INTENT] = MEDICAL_FOUND

        # Chatting to the psychologist
        elif USER_DATA[sender_id][CURRENT_INTENT] == MEDICAL_FOUND:
            USER_DATA[sender_id][MEDICAL_FOUND] = True
            medical_found(sender_id)

            # Set the next intent for the conversation
            USER_DATA[sender_id][CURRENT_INTENT] = FINISH

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

    # Debug info
    print('\n{}\n'.format(USER_DATA))

    return


def send_message(sender_id, payload):
    print("response sending.. - {}".format(time.monotonic()))
    # Sending response back to the user using facebook graph API
    r = requests.post("https://graph.facebook.com/v2.6/me/messages",
                      params={"access_token": PAT},
                      headers={"Content-Type": "application/json"},
                      data=js.dumps({
                          "recipient": {"id": sender_id},
                          "message": payload
                      }))
    print("response sent - {}".format(time.monotonic()))
    return json(r.content)


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
    # Always start with English
    payload = _en_US["language"]
    send_message(sender_id, payload)

    return


def picture(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["picture"]
    send_message(sender_id, payload)

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

    return


def psychological_found(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["psychological_found"]
    send_message(sender_id, payload)

    return


def medical(sender_id):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["medical"]
    send_message(sender_id, payload)

    payload = lang["medical_assessment"]["Q1"]
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

    # Add the MEDICAL key if it does not exist
    if MEDICAL not in USER_DATA[sender_id]:
        USER_DATA[sender_id][MEDICAL] = {}
        USER_DATA[sender_id][MEDICAL][MEDICAL_QA] = "Q1"

    for i in range(len(QA)):
        # Command handler
        if USER_DATA[sender_id][REPLY] == "/cancel":
            # Set the next intent for the conversation
            USER_DATA[sender_id][MEDICAL][MEDICAL_QA] = DONE
            USER_DATA[sender_id][CURRENT_INTENT] = CANCEL
            break

        # Check if the last question was answered
        if QA[i] == QA[len(QA)-1]:
            # Record answer
            USER_DATA[sender_id][MEDICAL][QA[i]] = USER_DATA[sender_id][REPLY]
            # Set the next intent for the conversation
            USER_DATA[sender_id][MEDICAL][MEDICAL_QA] = DONE
            break

        # Continue with examination
        elif USER_DATA[sender_id][MEDICAL][MEDICAL_QA] == QA[i]:
            # Record answer
            USER_DATA[sender_id][MEDICAL][QA[i]] = USER_DATA[sender_id][REPLY]
            # Set the next intent for the conversation
            USER_DATA[sender_id][MEDICAL][MEDICAL_QA] = QA[i+1]
            payload = lang["medical_assessment"][QA[i+1]]
            send_message(sender_id, payload)
            break

    if USER_DATA[sender_id][MEDICAL][MEDICAL_QA] == DONE:
        payload = lang["qa_finish"]
        send_message(sender_id, payload)
        # Match questions and answers after assessment
        exam = ""
        for questions in lang["medical_assessment"]:
            exam += "{}: {}\n".format(lang["medical_assessment"][questions]["text"], USER_DATA[sender_id][MEDICAL][questions])

        #USER_DATA[sender_id][CURRENT_INTENT] = QA_FINISH
        USER_DATA[sender_id][CURRENT_INTENT] = MEDICAL_WAIT
        medical_case(sender_id, exam)

    return


def medical_case(sender_id, examination):
    lang = choose_language(USER_DATA[sender_id][LANGUAGE])
    payload = lang["medical_case"]
    send_message(sender_id, payload)

    # Use this section to Do API calls to push data wherever needed..
    PAR = {
        "chat_id": "-1001294324217",
        "text": examination}
    URL = "https://api.telegram.org/bot1135235037:AAGuIT9j1lK7VIBS2AyIycKNLTviOAm6wcY/sendMessage"
    r = requests.get(url=URL, params=PAR)

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
    app.run(port=5000, debug=False)
