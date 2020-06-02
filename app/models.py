from datetime import datetime as dt

from flask_appbuilder import Model
from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship


class Anime(Model):
    id = Column(Integer, primary_key=True)
    name = Column(String(100))
    base_url = Column(String(50))
    anime_url = Column(String(100))
    active = Column(Boolean)
    episode = Column(Integer)
    last_refreshed_at = Column(
        String(50), default=dt.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    )
    updated_at = Column(
        String(50), default=dt.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    )
    site = Column(String(20))
    image = Column(String(256))
    genre = Column(String(256))
    other_name = Column(String(100))
    status = Column(String(50))
    released_year = Column(Integer)

    def __repr__(self):
        return self.name
