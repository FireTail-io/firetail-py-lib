#!/usr/bin/env python
import logging

import firetail
from firetail.resolver import MethodViewResolver

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    app = firetail.FlaskApp(__name__, specification_dir="openapi/", debug=True)

    options = {"swagger_ui": True}
    app.add_api(
        "pets-api.yaml",
        options=options,
        arguments={"title": "MethodViewResolver Example"},
        resolver=MethodViewResolver("api"),
        strict_validation=True,
        validate_responses=True,
    )
    app.run(port=9090)
