"""
This module defines a FlaskApp, a Firetail application to wrap a Flask application.
"""
import logging
import pathlib
from json import JSONEncoder
from types import FunctionType  # NOQA

import flask
import werkzeug.exceptions
from flask import signals

from ..apis.flask_api import FlaskApi
from ..exceptions import ProblemException
from ..problem import problem
from .abstract import AbstractApp

logger = logging.getLogger("firetail.app")


class FlaskApp(AbstractApp):
    def __init__(self, import_name, server="flask", extra_files=None, **kwargs):
        """
        :param extra_files: additional files to be watched by the reloader, defaults to the swagger specs of added apis
        :type extra_files: list[str | pathlib.Path], optional

        See :class:`~firetail.AbstractApp` for additional parameters.  # noqa RST304
        """
        super().__init__(import_name, FlaskApi, server=server, **kwargs)
        self.extra_files = extra_files or []

    def create_app(self):
        app = flask.Flask(self.import_name, **self.server_args)
        app.url_map.converters["float"] = NumberConverter
        app.url_map.converters["int"] = IntegerConverter
        return app

    def get_root_path(self):
        return pathlib.Path(self.app.root_path)

    def set_errors_handlers(self):
        for error_code in werkzeug.exceptions.default_exceptions:
            self.add_error_handler(error_code, self.common_error_handler)

        self.add_error_handler(ProblemException, self.common_error_handler)

    def common_error_handler(self, exception):
        """
        :type exception: Exception
        """
        signals.got_request_exception.send(self.app, exception=exception)
        if isinstance(exception, ProblemException):
            response = problem(
                status=exception.status,
                title=exception.title,
                detail=exception.detail,
                type=exception.type,
                instance=exception.instance,
                headers=exception.headers,
                ext=exception.ext,
            )
        else:
            if not isinstance(exception, werkzeug.exceptions.HTTPException):
                exception = werkzeug.exceptions.InternalServerError()

            response = problem(
                title=exception.name,
                detail=exception.description,
                status=exception.code,
                headers=exception.get_headers(),
            )

        return FlaskApi.get_response(response)

    def add_api(self, specification, **kwargs):
        api = super().add_api(specification, **kwargs)
        self.app.register_blueprint(api.blueprint)
        if isinstance(specification, (str, pathlib.Path)):
            self.extra_files.append(self.specification_dir / specification)
        return api

    def add_error_handler(self, error_code, function):
        # type: (int, FunctionType) -> None
        self.app.register_error_handler(error_code, function)

    def run(self, port=None, server=None, debug=None, host=None, extra_files=None, **options):  # pragma: no cover
        """
        Runs the application on a local development server.

        :param host: the host interface to bind on.
        :type host: str
        :param port: port to listen to
        :type port: int
        :param server: which wsgi server to use
        :type server: str | None
        :param debug: include debugging information
        :type debug: bool
        :param extra_files: additional files to be watched by the reloader.
        :type extra_files: Iterable[str | pathlib.Path]
        :param options: options to be forwarded to the underlying server
        """
        # this functions is not covered in unit tests because we would effectively testing the mocks

        # overwrite constructor parameter
        if port is not None:
            self.port = port
        elif self.port is None:
            self.port = 5000

        self.host = host or self.host or "0.0.0.0"

        if server is not None:
            self.server = server

        if debug is not None:
            self.debug = debug

        if extra_files is not None:
            self.extra_files.extend(extra_files)

        logger.debug("Starting %s HTTP server..", self.server, extra=vars(self))
        if self.server == "flask":
            self.app.run(self.host, port=self.port, debug=self.debug, extra_files=self.extra_files, **options)
        elif self.server == "tornado":
            try:
                import tornado.httpserver
                import tornado.ioloop
                import tornado.wsgi
            except ImportError:
                raise Exception("tornado library not installed")
            wsgi_container = tornado.wsgi.WSGIContainer(self.app)
            http_server = tornado.httpserver.HTTPServer(wsgi_container, **options)
            http_server.listen(self.port, address=self.host)
            logger.info("Listening on %s:%s..", self.host, self.port)
            tornado.ioloop.IOLoop.instance().start()
        elif self.server == "gevent":
            try:
                import gevent.pywsgi
            except ImportError:
                raise Exception("gevent library not installed")
            http_server = gevent.pywsgi.WSGIServer((self.host, self.port), self.app, **options)
            logger.info("Listening on %s:%s..", self.host, self.port)
            http_server.serve_forever()
        else:
            raise Exception(f"Server {self.server} not recognized")


class NumberConverter(werkzeug.routing.BaseConverter):
    """Flask converter for OpenAPI number type"""

    regex = r"[+-]?[0-9]*(\.[0-9]*)?"

    def to_python(self, value):
        return float(value)


class IntegerConverter(werkzeug.routing.BaseConverter):
    """Flask converter for OpenAPI integer type"""

    regex = r"[+-]?[0-9]+"

    def to_python(self, value):
        return int(value)
