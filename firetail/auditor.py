import hashlib
import json
import logging
import logging.config
import time

import jwt
import requests
from flask import g, request

from .logger import get_stdout_logger

DEFAULT_LOG_ENDPOINT = "https://api.logging.eu-west-1.prod.firetail.app/logs/bulk"


class cloud_logger(object):
    def __init__(
        self,
        app,
        url=DEFAULT_LOG_ENDPOINT,
        debug=False,
        custom_backend=False,
        token=None,
        backup_logs=False,
        network_timeout=10.0,
        number_of_retries=4,
        retry_timeout=2,
        logs_drain_timeout=5,
        scrub_headers=["set-cookie", "cookie", "authorization", "x-api-key", "token", "api-token", "api-key"],
        enrich_oauth=True,
    ):
        self.startThread = True
        self.custom_backend = custom_backend
        self.requests_session = requests.Session()
        self.url = url
        self.token = token
        self.auth_token = None
        self.logs_drain_timeout = logs_drain_timeout
        self.stdout_logger = get_stdout_logger(debug)
        self.backup_logs = backup_logs
        self.network_timeout = network_timeout
        self.requests_session = requests.Session()
        self.number_of_retries = number_of_retries
        self.retry_timeout = retry_timeout
        self.oauth = False
        self.logger = None
        self.enrich_oauth = enrich_oauth
        self.scrub_headers = scrub_headers
        self.LOGGING = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"firetailFormat": {"format": '{"additional_field": "value"}', "validate": False}},
            "handlers": {
                "firetail": {
                    "class": "firetail.handlers.FiretailHandler",
                    "level": "DEBUG",
                    "formatter": "firetailFormat",
                    "token": self.token,
                    "custom_backend": self.custom_backend,
                    "logs_drain_timeout": 5,
                    "url": self.url,
                    "retries_no": 4,
                    "retry_timeout": 2,
                }
            },
            "loggers": {"": {"level": "DEBUG", "handlers": ["firetail"], "propagate": True}},
        }
        if app:
            self.init_app(app, token)

    def init_app(self, app, token):
        create_before_request = make_before_request_function()
        app.before_request(create_before_request)
        create_after_request = make_after_request_function(self, token)
        app.after_request(create_after_request)

    def set_token(self, token_secret):
        self.token = token_secret

    def sha1_hash(self, value):
        hash_object = hashlib.sha1(value.encode("utf-8"))
        return "sha1:" + hash_object.hexdigest()

    def clean_pii(self, payload):
        clean_headers = self.scrub_headers
        if "req" in payload and "headers" in payload["req"]:
            for k, v in payload["req"]["headers"].items():
                if k.lower() in clean_headers:
                    if k.lower() == "authorization" and "bearer " in v.lower():
                        self.oauth = True
                        v = v.split(" ")[1]
                        self.auth_token = v
                    payload["req"]["headers"][k] = self.sha1_hash(v)
        if "res" in payload and "headers" in payload["res"]:
            for k, v in payload["res"]["headers"].items():
                if k.lower() in clean_headers:
                    payload["req"]["headers"][k] = self.sha1_hash(v)

        if self.oauth and self.enrich_oauth:
            try:
                jwt_decoded = jwt.decode(self.auth_token, options={"verify_signature": False, "verify_exp": False})
            except jwt.exceptions.DecodeError:
                self.oauth = False
            if self.oauth:
                payload["oauth"] = {"sub": jwt_decoded["sub"]}
                if "email" in jwt_decoded:
                    payload["oauth"]["email"] = jwt_decoded["email"]
        return payload

    def format_headers(self, req_headers):
        result = {}
        for x, y in req_headers.items():
            result[x] = [y]
        return result

    def create(self, response, token, diff=-1, scrub_headers=None, debug=False):
        if debug:
            self.stdout_logger = get_stdout_logger(True)
        if scrub_headers and isinstance(scrub_headers, list):
            self.scrub_headers = scrub_headers
        self.token = token
        if not self.logger:
            self.LOGGING["handlers"]["firetail"]["token"] = token
            logging.config.dictConfig(self.LOGGING)
            self.logger = logging.getLogger("firetailLogger")
        try:
            response_data = response.get_json() if response.is_json else str(response.response[0].decode("utf-8"))
        except Exception:
            response_data = ""
        payload = {
            "version": "1.0.0-alpha",
            "dateCreated": int(time.time() * 1000),
            "executionTime": diff,
            "request": {
                "httpProtocol": request.environ.get("SERVER_PROTOCOL", "HTTP/1.1"),
                "uri": request.url,
                "headers": self.format_headers(dict(request.headers)),
                "resource": request.url_rule.rule if request.url_rule is not None else request.path,
                "method": request.method,
                "body": str(request.data),
                "ip": request.remote_addr,
            },
            "response": {
                "statusCode": response.status_code,
                "body": str(response_data),
                "headers": self.format_headers(dict(response.headers)),
            },
        }
        try:
            if self.token or self.custom_backend:
                self.logger.info(json.dumps(self.clean_pii(payload)))
        except TypeError:
            pass
        return payload


def make_after_request_function(cl, token):
    def logs_after_request(resp):
        diff = time.time() - g.start
        time_diff = diff * 1000
        cl.create(resp, token, round(time_diff, 2))
        return resp

    return logs_after_request


def make_before_request_function():
    def logs_before_request():
        g.start = time.time()

    return logs_before_request
