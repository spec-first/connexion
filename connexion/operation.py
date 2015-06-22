"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""

import functools
import logging
import types

from connexion.decorators.produces import BaseSerializer, Produces, Jsonifier
from connexion.decorators.security import security_passthrough, verify_oauth
from connexion.utils import flaskify_endpoint, get_function_from_name, produces_json

logger = logging.getLogger('connexion.operation')


class Operation:
    """
    A single API operation on a path.
    """

    def __init__(self, method: str, path: str, operation: dict,
                 app_produces: list, app_security: list, security_definitions: dict):
        """
        This class uses the OperationID identify the module and function that will handle the operation

        From Swagger Specification:

        **OperationID**

        A friendly name for the operation. The id MUST be unique among all operations described in the API.
        Tools and libraries MAY use the operation id to uniquely identify an operation.

        :param method: HTTP method
        :param path:
        :param operation: swagger operation object
        :return:
        """

        self.method = method
        self.path = path
        self.app_produces = app_produces  # app level mimetypes
        self.app_security = app_security  # app level security
        self.security_definitions = security_definitions

        self.operation = operation
        self.operation_id = operation['operationId']
        self.produces = operation.get('produces')
        self.endpoint_name = flaskify_endpoint(self.operation_id)
        self.security = operation.get('security')
        self.__undecorated_function = get_function_from_name(self.operation_id)

    @property
    def function(self):
        produces_decorator = self.__content_type_decorator
        logger.debug('... Adding produces decorator (%r)', produces_decorator)
        function = produces_decorator(self.__undecorated_function)

        security_decorator = self.__security_decorator
        logger.debug('... Adding security decorator (%r)', security_decorator)
        function = security_decorator(function)
        return function

    @property
    def __content_type_decorator(self) -> types.FunctionType:
        """
        Get produces decorator.

        If the operation mimetype format is json then the function return value is jsonified

        From Swagger Specfication:

        **Produces**

        A list of MIME types the operation can produce. This overrides the produces definition at the Swagger Object.
        An empty value MAY be used to clear the global definition.
        """

        produces = self.produces if self.produces is not None else self.app_produces
        logger.debug('... Produces: %s', produces)

        if produces_json(produces):  # endpoint will return json
            mimetype = produces[0]
            logger.debug('... Produces json')
            jsonify = Jsonifier(mimetype)
            return jsonify
        elif len(produces) == 1:
            mimetype = produces[0]
            logger.debug('... Produces {}'.format(mimetype))
            decorator = Produces(mimetype)
            return decorator
        else:
            return BaseSerializer()

    @property
    def __security_decorator(self) -> types.FunctionType:
        """
        Gets the security decorator for operation

        From Swagger Specification:

        **Security Definitions Object**

        A declaration of the security schemes available to be used in the specification.

        This does not enforce the security schemes on the operations and only serves to provide the relevant details
        for each scheme.


        **Security Requirement Object**

        Lists the required security schemes to execute this operation. The object can have multiple security schemes
        declared in it which are all required (that is, there is a logical AND between the schemes).

        The name used for each property **MUST** correspond to a security scheme declared in the Security Definitions.
        """
        security = self.security if self.security is not None else self.security
        logger.debug('... Security: %s', security)
        if security:
            if len(security) > 1:
                logger.warning("... More than security requirement defined. **IGNORING SECURITY REQUIREMENTS**")
                return security_passthrough

            security = security[0]  # type: dict
            # the following line gets the first (and because of the previous condition only) scheme and scopes
            # from the operation's security requirements

            scheme_name, scopes = next(iter(security.items()))  # type: str, list
            security_definition = self.security_definitions[scheme_name]
            if security_definition['type'] == 'oauth2':
                token_info_url = security_definition['x-tokenInfoUrl']
                scopes = set(scopes)  # convert scopes to set because this is needed for verify_oauth
                return functools.partial(verify_oauth, token_info_url, scopes)
            else:
                logger.warning("... Security type '%s' unknown. **IGNORING SECURITY REQUIREMENTS**",
                               security_definition['type'])

        # if we don't know how to handle the security or it's not defined we will usa a passthrough decorator
        return security_passthrough
