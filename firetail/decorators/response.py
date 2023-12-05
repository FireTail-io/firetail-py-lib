"""
This module defines a view function decorator to validate its responses.
"""

import asyncio
import functools
import logging

from flask import request
from jsonschema import ValidationError

from ..exceptions import NonConformingResponseBody, NonConformingResponseHeaders, AuthzNotPopulated, AuthzFailed
from ..utils import all_json, has_coroutine
from .decorator import BaseDecorator
from .validation import ResponseBodyValidator

logger = logging.getLogger("firetail.decorators.response")


class ResponseValidator(BaseDecorator):
    def __init__(self, operation, mimetype, validator=None):
        """
        :type operation: Operation
        :type mimetype: str
        :param validator: Validator class that should be used to validate passed data
                          against API schema.
        :type validator: jsonschema.IValidator
        """
        self.operation = operation
        self.mimetype = mimetype
        self.validator = validator

    def validate_response(self, data, status_code, headers, url):
        """
        Validates the Response object based on what has been declared in the specification.
        Ensures the response body matches the declared schema.
        :type data: dict
        :type status_code: int
        :type headers: dict
        :rtype bool | None
        """
        # check against returned header, fall back to expected mimetype
        content_type = headers.get("Content-Type", self.mimetype)
        content_type = content_type.rsplit(";", 1)[0]  # remove things like utf8 metadata

        response_definition = self.operation.response_definition(str(status_code), content_type)
        response_schema = self.operation.response_schema(str(status_code), content_type)

        if self.is_json_schema_compatible(response_schema):
            v = ResponseBodyValidator(response_schema, validator=self.validator)
            try:
                data = self.operation.json_loads(data)
                v.validate_schema(data, url)
            except ValidationError as e:
                raise NonConformingResponseBody(message=str(e))

        if response_definition and response_definition.get("headers"):
            required_header_keys = {
                k for (k, v) in response_definition.get("headers").items() if v.get("required", False)
            }
            header_keys = set(headers.keys())
            missing_keys = required_header_keys - header_keys
            if missing_keys:
                pretty_list = ", ".join(missing_keys)
                msg = ("Keys in header don't match response specification. " "Difference: {}").format(pretty_list)
                raise NonConformingResponseHeaders(message=msg)
        # Now we know the response is in the correct format, we can check authz
        self.validate_response_authz(response_definition, data)
        return True

    def validate_response_authz(self, response_definition, data):
        try:
            authz_items = response_definition["x-ft-security"]
            request_data_lookup = authz_items["authenticated-principal-path"]
            response_data_lookup = authz_items["resource-authorized-principal-path"]
            lookup_type = authz_items.get("resource-content-format", "object")
            custom_resolver = authz_items.get("access-resolver")
        except KeyError:
            # no authz on this resp def.
            return True
        try:
            request_authz_data = request.firetail_authz[request_data_lookup]
        except AttributeError:
            # we have authz in our specification, but the authz params are not being auth set in the app layer.
            raise AuthzNotPopulated(
                "No Authz data returned from our app layer - flask must populate IDs to compare in Authz"
            )
        except KeyError:
            # we have incorrect authz being set in the app
            raise AuthzNotPopulated("Authz data does not contain expected key for authz to be evaluated")

        # use spec data to get from the request data.from and compare to the data returned.
        if lookup_type == "object":
            # we just check the single structure returned.
            if request_authz_data != self.extract_item(data, response_data_lookup):
                raise AuthzFailed()
        elif lookup_type == "list":
            # we must check many items.
            for item in data:
                if request_authz_data != self.extract_item(item, response_data_lookup):
                    raise AuthzFailed()
        if custom_resolver:
            # we must get custom_resolver from the request object.
            try:
                res_func = getattr(request, custom_resolver)
                res_func(data, request_data_lookup, response_data_lookup, lookup_type)
            except Exception:
                # just fail on any users exception here.
                raise AuthzFailed()
        return True

    def extract_item(self, data, response_data_lookup):
        items = response_data_lookup.split(".")
        dc = data.copy()
        for i in items:
            dc = dc[i]
        return dc

    def is_json_schema_compatible(self, response_schema: dict) -> bool:
        """
        Verify if the specified operation responses are JSON schema
        compatible.

        All operations that specify a JSON schema and have content
        type "application/json" or "text/plain" can be validated using
        json_schema package.
        """
        if not response_schema:
            return False
        return all_json([self.mimetype]) or self.mimetype == "text/plain"

    def __call__(self, function):
        """
        :type function: types.FunctionType
        :rtype: types.FunctionType
        """

        def _wrapper(request, response):
            firetail_response = self.operation.api.get_firetail_response(response, self.mimetype)
            if not firetail_response.is_streamed:
                self.validate_response(
                    firetail_response.body, firetail_response.status_code, firetail_response.headers, request.url
                )
            else:
                logger.warning("Skipping response validation for streamed response.")

            return response

        if has_coroutine(function):

            @functools.wraps(function)
            async def wrapper(request):
                response = function(request)
                while asyncio.iscoroutine(response):
                    response = await response

                return _wrapper(request, response)

        else:  # pragma: no cover

            @functools.wraps(function)
            def wrapper(request):
                response = function(request)
                return _wrapper(request, response)

        return wrapper

    def __repr__(self):
        """
        :rtype: str
        """
        return "<ResponseValidator>"  # pragma: no cover
