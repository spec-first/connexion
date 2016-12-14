from werkzeug.exceptions import BadRequest, Forbidden, HTTPException,
                                Unauthorized


class ConnexionException(Exception):
    pass


class ProblemException(ConnexionException, HTTPException):
    def __init__(self, title=None, description=None, response=None):
        """
        :param title: Title of the problem.
        :type title: str
        """
        ConnexionException.__init__(self)
        HTTPException.__init__(self, description, response)

        self.title = title or self.name


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


class OAuthProblem(ProblemException, Unauthorized):
    def __init__(self, title=None, **kwargs):
        super(OAuthProblem, self).__init__(title=title, **kwargs)


class OAuthResponseProblem(ProblemException, Unauthorized):
    def __init__(self, token_response, title=None, **kwargs):
        self.token_response = token_response
        super(OAuthResponseProblem, self).__init__(title=title, **kwargs)


class OAuthScopeProblem(ProblemException, Forbidden):
    def __init__(self, token_scopes, required_scopes, title=None, **kwargs):
        self.required_scopes = required_scopes
        self.token_scopes = token_scopes
        self.missing_scopes = required_scopes - token_scopes

        super(OAuthScopeProblem, self).__init__(title=title, **kwargs)


class ExtraParameterProblem(ProblemException, BadRequest):
    def __init__(self, formdata_parameters, query_parameters, title=None, description=None, **kwargs):
        self.extra_formdata = formdata_parameters
        self.extra_query = query_parameters

        # This keep backwards compatibility with the old returns
        if description is None:
            if self.extra_query:
                description = "Extra {parameter_type} parameter(s) {extra_params} not in spec"\
                    .format(parameter_type='query', extra_params=', '.join(self.extra_query))
            elif self.extra_formdata:
                description = "Extra {parameter_type} parameter(s) {extra_params} not in spec"\
                    .format(parameter_type='formData', extra_params=', '.join(self.extra_formdata))

        super(ExtraParameterProblem, self).__init__(title=title, description=description, **kwargs)
