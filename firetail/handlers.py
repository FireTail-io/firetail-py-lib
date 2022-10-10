"""
This module defines error handlers, operations that produce proper response problems.
"""
import json
import logging
import logging.handlers
import traceback

from .exceptions import FiretailException, ResolverProblem
from .logger import get_stdout_logger
from .sender import FiretailSender

logger = logging.getLogger("firetail.handlers")

RESOLVER_ERROR_ENDPOINT_RANDOM_DIGITS = 6


class ResolverErrorHandler:
    """
    Handler for responding to ResolverError.
    """

    def __init__(self, status_code, exception):
        self.status_code = status_code
        self.exception = exception

    @property
    def function(self):
        return self.handle

    def handle(self, *args, **kwargs):
        raise ResolverProblem(
            title="Not Implemented",
            detail=self.exception.reason,
            status=self.status_code,
        )

    @property
    def operation_id(self):
        return "noop"

    @property
    def randomize_endpoint(self):
        return RESOLVER_ERROR_ENDPOINT_RANDOM_DIGITS

    def get_path_parameter_types(self):
        return {}

    async def __call__(self, *args, **kwargs):
        raise ResolverProblem(
            title="Not Implemented",
            detail=self.exception.reason,
            status=self.status_code,
        )


class FiretailHandler(logging.Handler):
    def __init__(
        self,
        api_key,
        token,
        url,
        custom_backend=False,
        firetail_type="python",
        logs_drain_timeout=3,
        debug=False,
        backup_logs=True,
        network_timeout=10.0,
        retries_no=4,
        retry_timeout=2,
    ):

        if not token and not custom_backend:
            raise FiretailException("firetail Token must be provided")

        self.firetail_type = firetail_type

        self.firetail_sender = FiretailSender(
            token=token,
            url=url,
            api_key=api_key,
            logs_drain_timeout=logs_drain_timeout,
            debug=debug,
            backup_logs=backup_logs,
            network_timeout=network_timeout,
            number_of_retries=retries_no,
            retry_timeout=retry_timeout,
        )
        logging.Handler.__init__(self)

    def __del__(self):
        del self.firetail_sender

    def extra_fields(self, message):

        not_allowed_keys = (
            "args",
            "asctime",
            "created",
            "exc_info",
            "stack_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "msecs",
            "message",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "thread",
            "threadName",
        )

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
        self.firetail_sender.flush()

    def format(self, record):
        message = super(FiretailHandler, self).format(record)
        try:
            return json.loads(message)
        except (TypeError, ValueError):
            return message

    def format_exception(self, exc_info):
        return "\n".join(traceback.format_exception(*exc_info))

    def format_message(self, message):
        # now = datetime.datetime.utcnow()
        # timestamp = now.strftime('%Y-%m-%dT%H:%M:%S') + \
        #     '.%03d' % (now.microsecond / 1000) + 'Z'

        # return_json = {
        #     'logger': message.name,
        #     'line_number': message.lineno,
        #     'path_name': message.pathname,
        #     'log_level': message.levelname,
        #     'type': self.firetail_type,
        #     'message': message.getMessage(),
        #     '@timestamp': timestamp
        # }
        try:
            payload = json.loads(message.getMessage())
        except json.decoder.JSONDecodeError:
            return {"ignore": True}

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
        if "ignore" not in message:
            self.firetail_sender.append(message)
