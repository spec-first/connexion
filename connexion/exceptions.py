"""
Copyright 2015 Zalando SE

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the
License. You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
 language governing permissions and limitations under the License.
"""


class ConnexionException(Exception):
    pass


class ResolverError(LookupError):
    def __init__(self, reason='Unknown reason', exc_info=None):
        """
        :param reason: Reason why the resolver failed.
        :type reason: str
        :param exc_info: If specified, gives details of the original exception
            as returned by sys.exc_info()
        :type exc_info: tuple | None
        """
        self.reason = reason
        self.exc_info = exc_info

    def __str__(self):  # pragma: no cover
        return '<ResolverError: {}>'.format(self.reason)

    def __repr__(self):  # pragma: no cover
        return '<ResolverError: {}>'.format(self.reason)


class InvalidSpecification(ConnexionException):
    def __init__(self, reason='Unknown Reason'):
        """
        :param reason: Reason why the specification is invalid
        :type reason: str
        """
        self.reason = reason

    def __str__(self):  # pragma: no cover
        return '<InvalidSpecification: {}>'.format(self.reason)

    def __repr__(self):  # pragma: no cover
        return '<InvalidSpecification: {}>'.format(self.reason)


class NonConformingResponse(ConnexionException):
    def __init__(self, reason='Unknown Reason', message=None):
        """
        :param reason: Reason why the response did not conform to the specification
        :type reason: str
        """
        self.reason = reason
        self.message = message

    def __str__(self):  # pragma: no cover
        return '<NonConformingResponse: {}>'.format(self.reason)

    def __repr__(self):  # pragma: no cover
        return '<NonConformingResponse: {}>'.format(self.reason)


class NonConformingResponseBody(NonConformingResponse):
    def __init__(self, message, reason="Response body does not conform to specification"):
        super(NonConformingResponseBody, self).__init__(reason=reason, message=message)


class NonConformingResponseHeaders(NonConformingResponse):
    def __init__(self, message, reason="Response headers do not conform to specification"):
        super(NonConformingResponseHeaders, self).__init__(reason=reason, message=message)
