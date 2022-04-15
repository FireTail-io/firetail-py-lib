"""
This module defines a BaseDecorator to wrap a user view function and a RequestResponseDecorator
which manages the lifecycle of a request internally in PointSecIO.
"""

import asyncio
import functools
import logging

from ..utils import has_coroutine

logger = logging.getLogger('pointsecio.decorators.decorator')


class BaseDecorator:

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """
        return function

    def __repr__(self):  # pragma: no cover
        """
        :rtype: str
        """
        return '<BaseDecorator>'


class RequestResponseDecorator(BaseDecorator):
    """Manages the lifecycle of the request internally in PointSecIO.
    Filter the PointSecIORequest instance to return the corresponding
    framework specific object.
    """

    def __init__(self, api, mimetype):
        self.api = api
        self.mimetype = mimetype

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """
        if has_coroutine(function, self.api):
            @functools.wraps(function)
            async def wrapper(*args, **kwargs):
                pointsecio_request = self.api.get_request(*args, **kwargs)
                while asyncio.iscoroutine(pointsecio_request):
                    pointsecio_request = await pointsecio_request

                pointsecio_response = function(pointsecio_request)
                while asyncio.iscoroutine(pointsecio_response):
                    pointsecio_response = await pointsecio_response

                framework_response = self.api.get_response(pointsecio_response, self.mimetype,
                                                           pointsecio_request)
                while asyncio.iscoroutine(framework_response):
                    framework_response = await framework_response

                return framework_response

        else:  # pragma: no cover
            @functools.wraps(function)
            def wrapper(*args, **kwargs):
                request = self.api.get_request(*args, **kwargs)
                response = function(request)
                return self.api.get_response(response, self.mimetype, request)

        return wrapper
