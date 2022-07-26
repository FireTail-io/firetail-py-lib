#!/usr/bin/env python3
"""
Basic example of a resource server
"""

import firetail


def get_secret(user) -> str:
    return f"You are: {user}"


if __name__ == "__main__":
    app = firetail.FlaskApp(__name__)
    app.add_api("app.yaml")
    app.run(port=8080)
