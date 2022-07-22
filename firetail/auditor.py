import datetime
import hashlib
import json
import logging
import logging.config

import jwt
import requests
from flask import request

from .logger import get_stdout_logger

DEFAULT_OPTIONS = dict(origins='*',
                       methods=['GET', 'HEAD', 'POST', 'OPTIONS', 'PUT', 'PATCH', 'DELETE'],
                       allow_headers='*',
                       expose_headers=None,
                       supports_credentials=False,
                       max_age=None,
                       send_wildcard=False,
                       automatic_options=True,
                       vary_header=True,
                       resources=r'/*',
                       intercept_exceptions=True,
                       always_send=True)

class cloud_logger(object):
    def __init__(self,
                 app,
                 url='https://ingest.eu-west-1.dev.platform.pointsec.io/ingest/request',
                 api_key='5WqBxkOi3m6F1fDRryrR654xalAwz67815Rfe0ds',
                 debug=False,
                 token=None,
                 backup_logs=True,
                 network_timeout=10.0,
                 number_of_retries=4,
                 retry_timeout=2,
                 logs_drain_timeout=5,
                 scrub_headers=['set-cookie', 'cookie', 'authorization', 'x-api-key', 'token', 'api-token', 'api-key'],
                 enrich_oauth=True
                 ):
        self.api_key = api_key
        self.startThread = True
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
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'firetailFormat': {
                    'format': '{"additional_field": "value"}',
                    'validate': False
                }
            },
            'handlers': {
                'firetail': {
                    'class': 'firetail.handlers.FiretailHandler',
                    'level': 'DEBUG',
                    'formatter': 'firetailFormat',
                    'token': self.token,
                    'logs_drain_timeout': 5,
                    'url': self.url,
                    'api_key': self.api_key,
                    'retries_no': 4,
                    'retry_timeout': 2,
                }
            },
            'loggers': {
                '': {
                    'level': 'DEBUG',
                    'handlers': ['firetail'],
                    'propagate': True
                }
            }
        }
        if app:
            self.init_app(app, token)
    
    def init_app(self, app, token):
        create_after_request = make_after_request_function(self,token)
        app.after_request(create_after_request)


    def set_token(self, token_secret):
        self.token = token_secret

    def sha1_hash(self, value):
        hash_object = hashlib.sha1(value.encode('utf-8'))
        return "sha1:" + hash_object.hexdigest()

    def clean_pii(self, payload):
        clean_headers = self.scrub_headers
        if 'req' in payload and 'headers' in payload['req']:
            for k, v in payload['req']['headers'].items():
                if k.lower() in clean_headers:
                    if k.lower() == 'authorization' and 'bearer ' in v.lower():
                        self.oauth = True
                        v = v.split(" ")[1]
                        self.auth_token = v
                    payload['req']['headers'][k] = self.sha1_hash(v)
        if 'res' in payload and 'headers' in payload['res']:
            for k, v in payload['res']['headers'].items():
                if k.lower() in clean_headers:
                    payload['req']['headers'][k] = self.sha1_hash(v)

        if self.oauth and self.enrich_oauth:
            try:
                jwt_decoded = jwt.decode(self.auth_token, options={"verify_signature": False})
            except jwt.exceptions.DecodeError:
                self.oauth = False
            if self.oauth:
                payload['oauth'] = {'sub': jwt_decoded['sub']}
                if 'email' in jwt_decoded:
                    payload['oauth']['email'] = jwt_decoded['email']
        return payload

    def create(self, response, token, scrub_headers=None, debug=False):
        if debug:
            self.stdout_logger = get_stdout_logger(True)
        if scrub_headers and isinstance(scrub_headers, list):
            self.scrub_headers = scrub_headers
        self.token = token
        if not self.logger:
            self.LOGGING['handlers']['firetail']['token'] = token
            logging.config.dictConfig(self.LOGGING)
            self.logger = logging.getLogger('firetailLogger')

        payload = {
            "version": "1.1",
            "dateCreated": int((datetime.datetime.utcnow()).timestamp() * 1000),
            "req": {
                "url": request.base_url,
                "headers": dict(request.headers),
                "path": request.path,
                "method": request.method,
                "oPath": request.url_rule.rule if request.url_rule is not None else "",
                "fPath": request.full_path,
                "args": dict(request.args),
                "ip": request.remote_addr,
                'pathParams': request.view_args

            },
            "resp": {
                "status_code": response.status_code,
                "content_len": response.content_length,
                "content_enc": response.content_encoding,
                "body": response.get_json() if response.is_json else response.response,
                "headers": dict(response.headers),
                "content_type": response.content_type
            }
        }

        try:
            if self.token:
                print(json.dumps(self.clean_pii(payload)))
                self.logger.info(json.dumps(self.clean_pii(payload)))
        except TypeError:
            pass
        return payload

def make_after_request_function(cl,token):
    def logs_after_request(resp):
        cl.create(resp, token)
        return resp
    return logs_after_request

