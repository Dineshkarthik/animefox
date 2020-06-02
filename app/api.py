from flask_appbuilder import ModelRestApi
from flask_appbuilder.api import BaseApi, expose
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_appbuilder.models.filters import BaseFilter
from flask_appbuilder.security.decorators import protect

from . import appbuilder, db

from .models import Anime
from .kyuubi import crawler

anime_schema = {"type": "object", "properties": {"name": {"type": "string"}}}


class AnimeApi(BaseApi):
    resource_name = "anime"
    openapi_spec_methods = {
        "refresh": {"get": {"description": "Updates anime schedule",}}
    }
    apispec_parameter_schemas = {"greeting_schema": anime_schema}

    @expose("/refresh")
    # @protect()
    def private(self):
        """Say it's private
        ---
        get:
          responses:
            200:
              description: Say it's private
              content:
                application/json:
                  schema:
                    type: object
            401:
              $ref: '#/components/responses/401'
        """
        crawler()
        return self.response(200, success=True)


appbuilder.add_api(AnimeApi)
