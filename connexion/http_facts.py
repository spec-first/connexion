FORM_CONTENT_TYPES = [
    'application/x-www-form-urlencoded',
    'multipart/form-data'
]

HTTP_ERRORS = {
    404: {
        "title": "Not Found",
        "detail": 'The requested URL was not found on the server.  '
                  'If you entered the URL manually please check your spelling and try again.'
    },
    405: {
        "title": "Method Not Allowed",
        "detail": "The method is not allowed for the requested URL."
    },
    500: {
        "title": "Internal Server Error",
        "detail": 'The server encountered an internal error and was unable to complete your request.  '
                  'Either the server is overloaded or there is an error in the application.'
    },
    400: {
        "title": "Bad Request",
        "detail": "The browser (or proxy) sent a request that this server could not understand."
    },
    403: {
        "title": "Forbidden",
        "detail": "You don't have the permission to access the requested resource. "
                  "It is either read-protected or not readable by the server."
    }
}
