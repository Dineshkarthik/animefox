"""Script to keep me posted on new anime episodes."""
import os
import hashlib
from typing import List
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


import jinja2
import smtplib
import requests
from bs4 import BeautifulSoup
from optparse import OptionParser
from sqlalchemy import create_engine
from flask import Flask, json, request, jsonify
from flask_basicauth import BasicAuth
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base


app = Flask(__name__)
app.secret_key = hashlib.sha1(os.urandom(128)).hexdigest()

THIS_DIR: str = os.path.dirname(os.path.abspath(__file__))
app.config.from_pyfile(os.path.join(THIS_DIR, "config.py"))
basic_auth = BasicAuth(app)

db = create_engine(app.config["DATABASE_URI"])

Base = declarative_base()
Base.metadata.reflect(db)
Session = sessionmaker(bind=db)
session = Session()


class Anime(Base):
    """Class for translation table."""

    __table__ = Base.metadata.tables[app.config["TABLE_NAME"]]


def get_anime(is_active: bool, is_all: bool = True) -> List:
    """Function to get list of all active anime."""
    active_list = []
    archive_list = []
    all_list = []
    for anime in session.query(Anime).all():
        _dict = anime.__dict__
        _dict.pop("_sa_instance_state")
        if _dict["site"] == "gogoanime":
            _dict[
                "url"
            ] = f"{anime.base_url}/{anime.anime_url}-episode-{anime.episode}"
            _dict["genre"] = _dict["genre"].split(",")
        elif _dict["site"] == "1movies":
            _dict["url"] = f"{anime.base_url}{anime.anime_url}"
        if _dict["active"]:
            active_list.append(_dict)
        else:
            if _dict["site"] == "gogoanime":
                archive_list.append(_dict)
        if _dict["site"] == "gogoanime":
            all_list.append(_dict)
    if is_active:
        anime_list = active_list
    else:
        if is_all:
            anime_list = all_list
        else:
            anime_list = archive_list
    return anime_list


def scrap_url(_url: str):
    """Function to scrap the web page."""
    r = requests.get(_url, headers=app.config["HEADERS"])
    if r.status_code == 200:
        data = r.text
        return BeautifulSoup(data, features="html.parser")
    else:
        return False


def send_mail(updated_list: list):
    """Function to generate email template and send it."""
    template_loader = jinja2.FileSystemLoader(searchpath="./templates")
    template_env = jinja2.Environment(loader=template_loader)
    template_file = "email.html"
    template = template_env.get_template(template_file)
    html_template = template.render(updated_list=updated_list)

    msg = MIMEMultipart("related")
    msg["Subject"] = "New Anime Episodes..!!!"
    msg["From"] = f"Anime Fox<{app.config['FROMADDR']}>"
    msg.preamble = "This is a multi-part message in MIME format."
    msg_alternative = MIMEMultipart("alternative")
    msg.attach(msg_alternative)
    msg_text = MIMEText(
        html_template.encode("utf-8"), "html", _charset="utf-8"
    )
    msg_alternative.attach(msg_text)

    server = smtplib.SMTP_SSL(app.config["SMTP_HOST"], 465)
    server.login(app.config["FROMADDR"], app.config["PASSWORD"])
    server.sendmail(
        app.config["FROMADDR"], app.config["BCCADDR"], msg.as_string()
    )
    server.quit()


def update_json(data: dict, json_url: str):
    headers = {"Security-key": app.config["SECURITY_KEY"]}
    requests.put(json_url, headers=headers, data=data)


@app.route("/crawler", methods=["GET"])
def crawler():
    """Function to crawl and update anime schedule."""
    updated = []
    _datetime = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    for anime in session.query(Anime).all():
        if anime.site == "gogoanime":
            if anime.active:
                _url = f"{anime.base_url}/{anime.anime_url}-episode-{anime.episode + 1}"
                soup = scrap_url(_url)
                if soup:
                    anime.last_refreshed_at = _datetime
                    if soup.find_all(
                        "div", {"class": "anime_video_body_watch"}
                    ):
                        anime.episode = anime.episode + 1
                        anime.updated_at = _datetime
                        updated.append(
                            dict(
                                name=anime.name,
                                image=anime.image,
                                url=_url,
                                episode=f"{anime.name} Episode {anime.episode}",
                            )
                        )
        elif anime.site == "1movies":
            if anime.active:
                _url = f"{anime.base_url}{anime.anime_url}"
                soup = scrap_url(_url)
                if soup:
                    anime.last_refreshed_at = _datetime
                    episode_div = soup.find_all(
                        "div", {"id": "scroll_block_episodes"}
                    )[0]
                    ahrefs = episode_div.find_all("a")
                    dict_episode_name = {}
                    dict_episode_url = {}
                    for ahref in ahrefs:
                        dict_episode_name[
                            int(ahref.get("data-number"))
                        ] = ahref.find_all("div", {"class": "episodes_name"})[
                            0
                        ].text
                        dict_episode_url[
                            int(ahref.get("data-number"))
                        ] = ahref.get("href")
                    current_episode = max(dict_episode_name)
                    new_url = (
                        f"{anime.base_url}{dict_episode_url[current_episode]}"
                    )
                    if anime.episode < current_episode:
                        anime.episode = current_episode
                        anime.updated_at = _datetime
                        anime.anime_url = dict_episode_url[current_episode]
                        updated.append(
                            dict(
                                name=anime.name,
                                image=anime.image,
                                url=new_url,
                                episode=dict_episode_name[current_episode],
                            )
                        )

    if updated:
        send_mail(updated)
        update_json(
            json.dumps(get_anime(is_active=True)), app.config["ACTIVE_URL"]
        )
        _list = get_anime(is_active=False)
        for anime in _list:
            anime["url"] = f"{anime['base_url']}/category/{anime['anime_url']}"
        update_json(json.dumps(_list), app.config["LIST_URL"])

    session.commit()
    return jsonify({"success": True})


@app.route("/add", methods=["POST"])
@basic_auth.required
def add_anime():
    """Add new anime to list."""
    _datetime = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    anime = Anime()
    anime.name = request.form["name"]
    anime.base_url = request.form["base_url"]
    anime.anime_url = request.form["anime_url"]
    anime.active = bool(request.form["active"].lower() == "true")
    anime.episode = request.form["episode"]
    anime.last_refreshed_at = _datetime
    anime.updated_at = _datetime
    anime.site = request.form["site"]
    anime.image = request.form["image"]
    anime.genre = request.form["genre"]
    anime.other_name = request.form["other_name"]
    anime.status = request.form["status"]
    anime.released_year = request.form["released_year"]
    session.add(anime)
    session.commit()
    return jsonify(request.form)


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option(
        "-p",
        "--port",
        dest="port",
        help="Port on which the app will run",
        default=5000,
    )
    (options, args) = parser.parse_args()
    app.run(host="0.0.0.0", debug=True, port=int(options.port))
