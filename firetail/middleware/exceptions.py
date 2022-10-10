import json

from starlette.exceptions import ExceptionMiddleware as StarletteExceptionMiddleware
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from firetail.exceptions import ProblemException, problem


class ExceptionMiddleware(StarletteExceptionMiddleware):
    """Subclass of starlette ExceptionMiddleware to change handling of HTTP exceptions to
    existing firetail behavior."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_exception_handler(ProblemException, self.problem_handler)

    def problem_handler(self, _, exception: ProblemException):
        """
        :type exception: Exception
        """
        firetail_response = problem(
            status=exception.status,
            title=exception.title,
            detail=exception.detail,
            type=exception.type,
            instance=exception.instance,
            headers=exception.headers,
            ext=exception.ext,
        )

        return Response(
            content=json.dumps(firetail_response.body),
            status_code=firetail_response.status_code,
            media_type=firetail_response.mimetype,
            headers=firetail_response.headers,
        )

    def http_exception(self, request: Request, exc: HTTPException) -> Response:
        try:
            headers = exc.headers  # type: ignore
        except AttributeError:
            # Starlette < 0.19
            headers = {}

        firetail_response = problem(
            title=exc.detail, detail=exc.detail, status=exc.status_code, headers=headers
        )

        return Response(
            content=json.dumps(firetail_response.body),
            status_code=firetail_response.status_code,
            media_type=firetail_response.mimetype,
            headers=firetail_response.headers,
        )
