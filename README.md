# HumanBios facebook frontend
This repo creates a facebook messenger bot using the [Sanic](https://sanic.readthedocs.io/en/latest/) framework. The messenger bot interacts with a [Telegram](https://telegram.org/) bot using webhooks. These webhooks ultimately acts as a gateway between facebook messenger and telegram. 

#### Specification

https://hackmd.io/p0vKHdtAR4C1ygXadeTncA?view

Once the user follows a specific conversation path by the use of **intents**, user gets connected to a corresponding telegram channel.

- medical-room
- pyschologist
- room for new members

## Getting started
Here is how to get a test platform running:

We assume you already have a facebook page created under your facebook account. Here's [how](https://www.facebook.com/help/135275340210354) if you're not sure.

1. Create a [facebook developer account](https://developers.facebook.com)
2. Once you're up, create new app. Here is a [guide](https://developers.facebook.com/docs/apps/).
3. Go to **Add a Product** and **Set Up** Messenger.
4. Go to Messenger **Settings** and then to **Access Tokens**. Add the fb page you manage and **Generate Token** for the page. This should generate a Page Access Token to be set in the **.env** file. (See step 11 below)
5. Clone this repo on your computer. 
6. Setup a [ngrok](https://ngrok.com/) account for testing purposes.
7. Install **ngrok** and run the following:
	`./ngrok http -bind-tls=true 5000`
8. Copy the **.env.example** to a **.env** file.
9. Edit the **.env** file. 
10. From the **ngrok** terminal, copy the "forwarding" url to WEBHOOK variable in **.env**.
11.  Copy the Page Access Token created in facebook developer to PAT variable.
12. Write any verification string of your choice in the VERIFY_TOKEN variable. Like VERIFY_TOKEN=thisisateststringtoverify
13. Run the app with `python3 app.py`
14. Back to facebook developer. Go to messenger settings and navigate to **Webhooks**. 
15. Create a webhook callback url. Copy the same tunneling url created by **ngrok** to "Callback URL" in facebook dev. 
16. Copy the same VERIFY_TOKEN string in **.env** to "Verify Token" in facebook dev.
17. First run the messenger bot
18. Click "Verify and Save". If you've setup all the above successfully the app should function correctly, provided the **app.py** is running and your **ngrok** tunneling is forwarding to the correct ports. 

### Telegram back-end
At the moment the telegram back-end of app.py runs through the same webhook url you've setup in **ngrok**. These the steps to get the telegram bot backend going for the facebook messenger bot:

1. Create a test [bot](https://core.telegram.org/bots) using @Botfather in telegram.
2. Copy the bot token to **.env** file. 
3. Setup a test telegram channel and add the channel_id to the specific room's in the **.env** file. A single channel id will serve all the rooms, please do not leave the _ROOM_ variables empty.
4. Restart app.py

### Dependencies

`pip install python-dotenv`

`pip install django-environ`

`pip install sanic`

## Docker
This repo is also using a docker container (with a poetry-environment inside)

1. Build the container with `docker-compose build`
2. Set the environment variables in the `.env` file (see: `.env.example`) 
3. Start with `docker-compose up`

