import datetime
import json
import logging
import logging.config

import requests
from flask import request

from .logger import get_stdout_logger


class auditor:
    def __init__(self,
                 url='https://ingest.eu-west-1.dev.platform.pointsec.io/ingest/request',
                 api_key='5WqBxkOi3m6F1fDRryrR654xalAwz67815Rfe0ds',
                 debug=False,
                 backup_logs=True,
                 network_timeout=10.0,
                 number_of_retries=4,
                 retry_timeout=2,
                 logs_drain_timeout=5):
        self.api_key = api_key
        self.startThread = True
        self.requests_session = requests.Session()
        self.url = url
        self.token = None
        self.logs_drain_timeout = logs_drain_timeout
        self.stdout_logger = get_stdout_logger(debug)
        self.backup_logs = backup_logs
        self.network_timeout = network_timeout
        self.requests_session = requests.Session()
        self.number_of_retries = number_of_retries
        self.retry_timeout = retry_timeout
        self.logger = None
        # if not token:
        #     raise Exception('Token must be provided')
        self.LOGGING = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'pointsecFormat': {
                    'format': '{"additional_field": "value"}',
                    'validate': False
                }
            },
            'handlers': {
                'pointsec': {
                    'class': 'pointsecio.handlers.PointsecHandler',
                    'level': 'DEBUG',
                    'formatter': 'pointsecFormat',
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
                    'handlers': ['pointsec'],
                    'propagate': True
                }
            }
        }

    def set_token(self, token_secret):
        self.token = token_secret

    def create(self, response, token):

        self.token = token
        if not self.logger:
            self.LOGGING['handlers']['pointsec']['token'] = token
            logging.config.dictConfig(self.LOGGING)
            self.logger = logging.getLogger('pointsecLogger')

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
                self.logger.info(json.dumps(payload))
        except TypeError as e:
            print(str(e))
        print("created log")


request_auditor = auditor()
