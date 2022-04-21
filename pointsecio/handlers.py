"""
This module defines error handlers, operations that produce proper response problems.
"""

# import datetime
import json
import logging
import logging.handlers
import sys
import traceback

from .exceptions import (AuthenticationProblem, PointsecException,
                         ResolverProblem)
from .logger import get_stdout_logger
from .operations.secure import SecureOperation
from .sender import PointsecSender

logger = logging.getLogger('pointsecio.handlers')

RESOLVER_ERROR_ENDPOINT_RANDOM_DIGITS = 6


class AuthErrorHandler(SecureOperation):
    """
    Wraps an error with authentication.
    """

    def __init__(self, api, exception, security, security_definitions):
        """
        This class uses the exception instance to produce the proper response problem in case the
        request is authenticated.

        :param exception: the exception to be wrapped with authentication
        :type exception: werkzeug.exceptions.HTTPException
        :param security: list of security rules the application uses by default
        :type security: list
        :param security_definitions: `Security Definitions Object
            <https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-definitions-object>`_
        :type security_definitions: dict
        """
        self.exception = exception
        super().__init__(api, security, security_definitions)

    @property
    def function(self):
        """
        Configured error auth handler.
        """
        security_decorator = self.security_decorator
        logger.debug('... Adding security decorator (%r)', security_decorator, extra=vars(self))
        function = self.handle
        function = security_decorator(function)
        function = self._request_response_decorator(function)
        return function

    def handle(self, *args, **kwargs):
        """
        Actual handler for the execution after authentication.
        """
        raise AuthenticationProblem(
            title=self.exception.name,
            detail=self.exception.description,
            status=self.exception.code
        )


class ResolverErrorHandler(SecureOperation):
    """
    Handler for responding to ResolverError.
    """

    def __init__(self, api, status_code, exception, security, security_definitions):
        self.status_code = status_code
        self.exception = exception
        super().__init__(api, security, security_definitions)

    @property
    def function(self):
        return self.handle

    def handle(self, *args, **kwargs):
        raise ResolverProblem(
            title='Not Implemented',
            detail=self.exception.reason,
            status=self.status_code
        )

    @property
    def operation_id(self):
        return "noop"

    @property
    def randomize_endpoint(self):
        return RESOLVER_ERROR_ENDPOINT_RANDOM_DIGITS

    def get_path_parameter_types(self):
        return {}


class PointsecHandler(logging.Handler):

    def __init__(self,
                 api_key,
                 token,
                 url,
                 pointsec_type="python",
                 logs_drain_timeout=3,
                 debug=False,
                 backup_logs=True,
                 network_timeout=10.0,
                 retries_no=4,
                 retry_timeout=2):

        if not token:
            raise PointsecException('pointsec.io Token must be provided')

        self.pointsec_type = pointsec_type

        self.pointsec_sender = PointsecSender(
            token=token,
            url=url,
            api_key=api_key,
            logs_drain_timeout=logs_drain_timeout,
            debug=debug,
            backup_logs=backup_logs,
            network_timeout=network_timeout,
            number_of_retries=retries_no,
            retry_timeout=retry_timeout)
        logging.Handler.__init__(self)

    def __del__(self):
        del self.pointsec_sender

    def extra_fields(self, message):

        not_allowed_keys = (
            'args', 'asctime', 'created', 'exc_info', 'stack_info', 'exc_text',
            'filename', 'funcName', 'levelname', 'levelno', 'lineno', 'module',
            'msecs', 'msecs', 'message', 'msg', 'name', 'pathname', 'process',
            'processName', 'relativeCreated', 'thread', 'threadName')

        if sys.version_info < (3, 0):
            # long and basestring don't exist in py3 so, NOQA
            var_type = (basestring, bool, dict, float,  # NOQA
                        int, long, list, type(None))  # NOQA
        else:
            var_type = (str, bool, dict, float, int, list, type(None))

        extra_fields = {}

        for key, value in message.__dict__.items():
            if key not in not_allowed_keys:
                if isinstance(value, var_type):
                    extra_fields[key] = value
                else:
                    extra_fields[key] = repr(value)

        return extra_fields

    def flush(self):
        self.pointsec_sender.flush()

    def format(self, record):
        message = super(PointsecHandler, self).format(record)
        try:
            return json.loads(message)
        except (TypeError, ValueError):
            return message

    def format_exception(self, exc_info):
        return '\n'.join(traceback.format_exception(*exc_info))

    def format_message(self, message):
        # now = datetime.datetime.utcnow()
        # timestamp = now.strftime('%Y-%m-%dT%H:%M:%S') + \
        #     '.%03d' % (now.microsecond / 1000) + 'Z'

        # return_json = {
        #     'logger': message.name,
        #     'line_number': message.lineno,
        #     'path_name': message.pathname,
        #     'log_level': message.levelname,
        #     'type': self.pointsec_type,
        #     'message': message.getMessage(),
        #     '@timestamp': timestamp
        # }
        try:
            payload = json.loads(message.getMessage())
        except json.decoder.JSONDecodeError:
            return {'ignore': True}

        # requiredInBody = ['req', 'res']
        # for item in requiredInBody:
        #     if item not in payload:
        #         return {'ignore': True}

        # return_json = payload
        return payload

    def emit(self, record):
        message = self.format_message(record)
        self.stdout_logger = get_stdout_logger(False)
        # self.stdout_logger.info(record.getMessage())
        if 'ignore' not in message:
            self.pointsec_sender.append(message)
