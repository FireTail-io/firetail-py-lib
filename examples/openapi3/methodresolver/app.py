#!/usr/bin/env python
import logging

import firetail
from firetail.resolver import MethodViewResolver

logging.basicConfig(level=logging.INFO)

zoo = {
    1: {
        "id": 1,
        "name": "giraffe",
        "tags": ["africa", "yellow", "hoofs", "herbivore", "long neck"],
    },
    2: {
        "id": 2,
        "name": "lion",
        "tags": ["africa", "yellow", "paws", "carnivore", "mane"],
    },
}

if __name__ == "__main__":
    app = firetail.FlaskApp(__name__, specification_dir="openapi/", debug=True)

    options = {"swagger_ui": True}
    app.add_api(
        "pets-api.yaml",
        options=options,
        arguments={"title": "MethodViewResolver Example"},
        resolver=MethodViewResolver(
            "api",
            # class params are entirely optional
            # they allow to inject dependencies top down
            # so that the app can be wired, in the entrypoint
            class_arguments={"PetsView": {"kwargs": {"pets": zoo}}},
        ),
        strict_validation=True,
        validate_responses=True,
    )
    app.run(port=9090, debug=True)
