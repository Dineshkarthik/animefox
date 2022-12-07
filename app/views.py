from flask import render_template
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder import ModelView, ModelRestApi

from . import appbuilder, db
from .models import Anime


@appbuilder.app.errorhandler(404)
def page_not_found(e):
    return (
        render_template(
            "404.html",
            base_template=appbuilder.base_template,
            appbuilder=appbuilder,
        ),
        404,
    )


class AnimeView(ModelView):
    datamodel = SQLAInterface(Anime)

    list_columns = ["name", "site", "episode", "released_year"]

    show_template = "appbuilder/general/model/show_cascade.html"


db.create_all()

appbuilder.add_view(AnimeView, "Animes", icon="fa-folder-open-o")
