import datetime
import json
import logging
import logging.config

import requests
from flask import request

from .logger import get_stdout_logger


class auditor:
    def __init__(self,
                 url='https://ingest.eu-west-1.dev.platform.pointsec.io',
                 debug=False,
                 backup_logs=True,
                 network_timeout=10.0,
                 number_of_retries=4,
                 retry_timeout=2,
                 logs_drain_timeout=5):
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
                    'token': '<<pointsec-TOKEN>>',
                    'logs_drain_timeout': 5,
                    'url': 'https://ingest.eu-west-1.dev.platform.pointsec.io/ingest/request',
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

    def create(self, response, token):

        self.token = token
        if not self.logger:
            self.LOGGING['handlers']['pointsec']['token'] = token
            logging.config.dictConfig(self.LOGGING)
            self.logger = logging.getLogger('pointsecLogger')

        jsonResponse = ['application/problem+json', 'application/json']
        if response.content_type.lower() in jsonResponse:
            body = response.get_json()
        else:
            body = response.response
        payload = {
            'status_code': response.status_code,
            'body': str(body),
            'dateAdded': int((datetime.datetime.utcnow()).timestamp()),
            'method': request.method,
            'content_length': response.content_length,
            'request_headers': dict(request.headers),
            'response_headers': dict(response.headers),
            'content_type': response.content_type,
            'path': request.path,
            'args': dict(request.args),
            'full_path': request.full_path,
            'url': request.url,
            'pathParameters': request.view_args
        }
        print(request.__dir__())
        try:
            self.logger.info(json.dumps(payload))
        except Exception as e:
            print(payload)
            print(str(e))
        print("created log")


request_auditor = auditor()
