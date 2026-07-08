import asyncio
from flask import Flask, request
from flask import session, redirect

from app import dp, bot
from aiogram.types import Update
from admin import init_admin
from os import getenv


application = Flask(__name__)
application.secret_key = getenv("ADMIN_SECRET_KEY")

init_admin(application)

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

USERNAME = getenv("ADMIN_USERNAME")
PASSWORD = getenv("ADMIN_PASSWORD")

@application.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if (
            request.form["username"] == USERNAME
            and request.form["password"] == PASSWORD
        ):
            session["logged_in"] = True
            return redirect("/admin")

        return "Invalid username or password", 401

    return """
    <h2>Admin Login</h2>
    <form method="post">
        <input name="username" placeholder="Username"><br><br>
        <input name="password" type="password" placeholder="Password"><br><br>
        <button type="submit">Login</button>
    </form>
    """

@application.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

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
    