import asyncio
from flask import Flask, request

from app import dp, bot
from aiogram.types import Update


application = Flask(__name__)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)


@application.route("/webhook", methods=["POST"])
def webhook():

    update = Update.model_validate(
        request.json,
        context={"bot": bot}
    )

    loop.run_until_complete(
        dp.feed_update(
            bot,
            update
        )
    )

    return "OK"
    
@application.route("/")
def home():
    return "Bot is running"
    