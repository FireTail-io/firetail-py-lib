"""
This module defines a SecureOperation class, which implements the security handler for an operation.
"""

import functools
import logging

from ..decorators.decorator import RequestResponseDecorator

logger = logging.getLogger("firetail.operations.secure")

DEFAULT_MIMETYPE = 'application/json'


class SecureOperation:

    def __init__(self, api, security, security_schemes):
        """
        :param security: list of security rules the application uses by default
        :type security: list
        :param security_definitions: `Security Definitions Object
            <https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#security-definitions-object>`_
        :type security_definitions: dict
        """
        self._api = api
        self._security = security
        self._security_schemes = security_schemes

    @property
    def api(self):
        return self._api

    @property
    def security(self):
        return self._security

    @property
    def security_schemes(self):
        return self._security_schemes

    @property
    def security_decorator(self):
        """
        Gets the security decorator for operation

        From Swagger Specification:

        **Security Definitions Object**

        A declaration of the security schemes available to be used in the specification.

        This does not enforce the security schemes on the operations and only serves to provide the relevant details
        for each scheme.


        **Operation Object -> security**

        A declaration of which security schemes are applied for this operation. The list of values describes alternative
        security schemes that can be used (that is, there is a logical OR between the security requirements).
        This definition overrides any declared top-level security. To remove a top-level security declaration,
        an empty array can be used.


        **Security Requirement Object**

        Lists the required security schemes to execute this operation. The object can have multiple security schemes
        declared in it which are all required (that is, there is a logical AND between the schemes).

        The name used for each property **MUST** correspond to a security scheme declared in the Security Definitions.

        :rtype: types.FunctionType
        """
        logger.debug('... Security: %s', self.security, extra=vars(self))
        if not self.security:
            return self._api.security_handler_factory.security_passthrough

        auth_funcs = []
        for security_req in self.security:
            if not security_req:
                auth_funcs.append(self._api.security_handler_factory.verify_none())
                continue

            sec_req_funcs = {}
            oauth = False
            for scheme_name, required_scopes in security_req.items():
                security_scheme = self.security_schemes[scheme_name]

                if security_scheme['type'] == 'oauth2':
                    if oauth:
                        logger.warning(
                            "... multiple OAuth2 security schemes in AND fashion not supported", extra=vars(self)
                        )
                        break
                    oauth = True
                    token_info_func = self._api.security_handler_factory.get_tokeninfo_func(security_scheme)
                    scope_validate_func = self._api.security_handler_factory.get_scope_validate_func(security_scheme)
                    if not token_info_func:
                        logger.warning("... x-tokenInfoFunc missing", extra=vars(self))
                        break

                    sec_req_funcs[scheme_name] = self._api.security_handler_factory.verify_oauth(
                        token_info_func, scope_validate_func, required_scopes)

                # Swagger 2.0
                elif security_scheme['type'] == 'basic':
                    basic_info_func = self._api.security_handler_factory.get_basicinfo_func(security_scheme)
                    if not basic_info_func:
                        logger.warning("... x-basicInfoFunc missing", extra=vars(self))
                        break

                    sec_req_funcs[scheme_name] = self._api.security_handler_factory.verify_basic(basic_info_func)

                # OpenAPI 3.0.0
                elif security_scheme['type'] == 'http':
                    scheme = security_scheme['scheme'].lower()
                    if scheme == 'basic':
                        basic_info_func = self._api.security_handler_factory.get_basicinfo_func(security_scheme)
                        if not basic_info_func:
                            logger.warning("... x-basicInfoFunc missing", extra=vars(self))
                            break

                        sec_req_funcs[scheme_name] = self._api.security_handler_factory.verify_basic(basic_info_func)
                    elif scheme == 'bearer':
                        bearer_info_func = self._api.security_handler_factory.get_bearerinfo_func(security_scheme)
                        if not bearer_info_func:
                            logger.warning("... x-bearerInfoFunc missing", extra=vars(self))
                            break
                        sec_req_funcs[scheme_name] = self._api.security_handler_factory.verify_bearer(bearer_info_func)
                    else:
                        logger.warning("... Unsupported http authorization scheme %s" % scheme, extra=vars(self))
                        break

                elif security_scheme['type'] == 'apiKey':
                    scheme = security_scheme.get('x-authentication-scheme', '').lower()
                    if scheme == 'bearer':
                        bearer_info_func = self._api.security_handler_factory.get_bearerinfo_func(security_scheme)
                        if not bearer_info_func:
                            logger.warning("... x-bearerInfoFunc missing", extra=vars(self))
                            break
                        sec_req_funcs[scheme_name] = self._api.security_handler_factory.verify_bearer(bearer_info_func)
                    else:
                        apikey_info_func = self._api.security_handler_factory.get_apikeyinfo_func(security_scheme)
                        if not apikey_info_func:
                            logger.warning("... x-apikeyInfoFunc missing", extra=vars(self))
                            break

                        sec_req_funcs[scheme_name] = self._api.security_handler_factory.verify_api_key(
                            apikey_info_func, security_scheme['in'], security_scheme['name']
                        )

                else:
                    logger.warning(
                        "... Unsupported security scheme type %s" % security_scheme['type'], extra=vars(self)
                    )
                    break
            else:
                # No break encountered: no missing funcs
                if len(sec_req_funcs) == 1:
                    (func,) = sec_req_funcs.values()
                    auth_funcs.append(func)
                else:
                    auth_funcs.append(self._api.security_handler_factory.verify_multiple_schemes(sec_req_funcs))

        return functools.partial(self._api.security_handler_factory.verify_security, auth_funcs)

    def get_mimetype(self):
        return DEFAULT_MIMETYPE

    @property
    def _request_response_decorator(self):
        """
        Guarantees that instead of the internal representation of the
        operation handler response
        (firetail.lifecycle.FiretailRequest) a framework specific
        object is returned.
        :rtype: types.FunctionType
        """
        return RequestResponseDecorator(self.api, self.get_mimetype())
