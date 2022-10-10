"""
This module defines interfaces for requests and responses used in Firetail for authentication,
validation, serialization, etc.
"""
from starlette.requests import Request as StarletteRequest
from starlette.responses import StreamingResponse as StarletteStreamingResponse


class FiretailRequest:
    """Firetail interface for a request."""

    def __init__(
        self,
        url,
        method,
        path_params=None,
        query=None,
        headers=None,
        form=None,
        body=None,
        json_getter=None,
        files=None,
        context=None,
        cookies=None,
    ):
        self.url = url
        self.method = method
        self.path_params = path_params or {}
        self.query = query or {}
        self.headers = headers or {}
        self.form = form or {}
        self.body = body
        self.json_getter = json_getter
        self.files = files
        self.context = context if context is not None else {}
        self.cookies = cookies or {}

    @property
    def json(self):
        if not hasattr(self, "_json"):
            self._json = self.json_getter()
        return self._json


class FiretailResponse:
    """Firetail interface for a response."""

    def __init__(
        self,
        status_code=200,
        mimetype=None,
        content_type=None,
        body=None,
        headers=None,
        is_streamed=False,
    ):
        self.status_code = status_code
        self.mimetype = mimetype
        self.content_type = content_type
        self.body = body
        self.headers = headers or {}
        self.is_streamed = is_streamed


class MiddlewareRequest(StarletteRequest):
    """Wraps starlette Request so it can easily be extended."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._context = None

    @property
    def context(self):
        if self._context is None:
            extensions = self.scope.setdefault("extensions", {})
            self._context = extensions.setdefault("firetail_context", {})

        return self._context


class MiddlewareResponse(StarletteStreamingResponse):
    """Wraps starlette StreamingResponse so it can easily be extended."""
