"""Script to keep me posted on new anime episodes."""
import os
import json
import logging
from typing import List
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


import jinja2
import smtplib
import requests
from bs4 import BeautifulSoup
from github import Github

from . import app, db
from .models import Anime

THIS_DIR: str = os.path.dirname(os.path.abspath(__file__))


session = db.session


def get_anime(is_active: bool, is_all: bool = True) -> List:
    """Function to get list of all active anime."""
    active_list = []
    archive_list = []
    all_list = []
    for anime in session.query(Anime).all():
        _dict = anime.__dict__.copy()
        _dict.pop("_sa_instance_state", None)
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
    template_loader = jinja2.FileSystemLoader(
        searchpath=os.path.join(THIS_DIR, "templates")
    )
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


def update_json(data: dict, path_: str):
    g = Github(app.config["ACCESS_TOKEN"])
    repo = g.get_repo(app.config["REPO_NAME"])
    json_file = repo.get_contents(path_)
    now: str = datetime.now().isoformat(" ", "seconds")
    commit_message = f"update {json_file.name} @ {now}"
    repo.update_file(json_file.path, commit_message, data, json_file.sha)
    logging.info("updated %s @ %s", json_file.name, now)


def update_anime_list():
    anime_list = get_anime(is_active=False)
    trimmed_list: list = []
    required_keys: list = [
        "name",
        "genre",
        "released_year",
        "status",
        "other_name",
        "url",
        "image",
    ]
    for anime in anime_list:
        anime["url"] = f"{anime['base_url']}/category/{anime['anime_url']}"
        trimmed_list.append({key: anime[key] for key in required_keys})

    update_json(json.dumps(trimmed_list), "data/list.json")


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
    session.commit()

    if updated:
        send_mail(updated)
        update_json(json.dumps(get_anime(is_active=True)), "data/active.json")
        update_anime_list()
    return True
