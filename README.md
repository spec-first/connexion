# Específico [![Build status](https://github.com/athenianco/especifico/actions/workflows/pipeline.yml/badge.svg)](https://github.com/athenianco/especifico/actions/workflows/pipeline.yml) [![Coveralls status](https://coveralls.io/repos/github/athenianco/especifico/badge.svg?branch=main)](https://coveralls.io/github/athenianco/especifico?branch=main) [![Latest Version](https://img.shields.io/pypi/v/especifico.svg)](https://pypi.python.org/pypi/especifico) [![Python Versions](https://img.shields.io/pypi/pyversions/especifico.svg)](https://pypi.python.org/pypi/especifico) [![License](https://img.shields.io/pypi/l/especifico.svg)](https://github.com/athenianco/especifico/blob/main/LICENSE)

Específico is a hard fork of [Connexion](https://github.com/spec-first/connexion),
the framework that automagically handles HTTP requests based on [OpenAPI Specification](https://www.openapis.org/)
(formerly known as Swagger Spec) of your API described in [YAML format](https://github.com/OAI/OpenAPI-Specification/blob/master/versions/2.0.md#format).
Específico allows you to write an OpenAPI specification, then maps the endpoints to your Python functions; this makes it
unique, as many tools generate the specification based on your Python code. You can describe your
REST API in as much detail as you want; then Específico guarantees that it will work as you
specified.

Específico tries to:

- simplify the development process
- confirm expectations about what your API will look like
- improve the security

## Específico features

- Validates requests and endpoint parameters automatically, based on
  your specification.
- Provides a Swagger UI so that the users of your API can
  have live documentation and even call your API's endpoints
  through it
- Handles OAuth2 and API Key token-based authentication
- Supports API versioning
- Supports automatic serialization of payloads. If your
  specification defines that an endpoint returns JSON, Específico will
  automatically serialize the return value for you and set the right
  content type in the HTTP header.

Why Específico
--------------

With Específico, [you write the spec first](https://opensource.zalando.com/restful-api-guidelines/#api-first).
Específico then calls your Python
code, handling the mapping from the specification to the code. This
encourages you to write the specification so that all of your
developers can understand what your API does, even before you write a
single line of code.

If multiple teams depend on your APIs, you can use Específico to easily send them the documentation of your API.
This guarantees that your API will follow the specification that you wrote.
This is a different process from that offered by frameworks such as [Hug](https://github.com/timothycrosley/hug),
which generates a specification *after* you've written the code.
Some disadvantages of generating specifications based on code is that they often end up
lacking details or mix your documentation with the code logic of your application.

Compared to the original project Específico, Específico keeps aiohttp support and includes many
opinionated patches from the fork's maintainer.

## How to Use

### Prerequisites

Python 3.8+

### Installing It

In your command line, type:

```
pip install especifico
```

### Running It

Place your API YAML inside a folder in the root
path of your application (e.g `swagger/`). Then run:

```python
import especifico

app = especifico.App(__name__, specification_dir='swagger/')
app.add_api('my_api.yaml')
app.run(port=8080)
```

See the [Connexion Pet Store Example Application](https://github.com/hjacobs/connexion-example) for a sample
specification.

Now you're able to run and use Específico!

## Details

### OAuth 2 Authentication and Authorization

Específico supports one of the three OAuth 2 handling methods. (See
"TODO" below.) With Específico, the API security definition **must**
include a 'x-tokenInfoUrl' or 'x-tokenInfoFunc (or set `TOKENINFO_URL`
or `TOKENINFO_FUNC` env var respectively). 'x-tokenInfoUrl' must contain an
URL to validate and get the [token information](https://tools.ietf.org/html/rfc6749) and 'x-tokenInfoFunc must
contain a reference to a function used to obtain the token info. When both 'x-tokenInfoUrl'
and 'x-tokenInfoFunc' are used, Específico will prioritize the function method. Específico expects to
receive the OAuth token in the `Authorization` header field in the
format described in [RFC 6750](https://tools.ietf.org/html/rfc6750) section 2.1. This aspect
represents a significant difference from the usual OAuth flow.

### Dynamic Rendering of Your Specification

Específico uses [Jinja2](http://jinja.pocoo.org/) to allow specification parameterization through the `arguments` parameter. You can define specification arguments for the application either globally (via the `especifico.App` constructor) or for each specific API (via the `especifico.App#add_api` method):

```python
app = especifico.App(__name__, specification_dir='swagger/',
                    arguments={'global': 'global_value'})
app.add_api('my_api.yaml', arguments={'api_local': 'local_value'})
app.run(port=8080)
```

When a value is provided both globally and on the API, the API value will take precedence.

### Endpoint Routing to Your Python Views

Específico uses the `operationId` from each [Operation Object](https://github.com/swagger-api/swagger-spec/blob/master/versions/2.0.md#operation-object)
to identify which Python function should handle each URL.

**Explicit Routing**:

```yaml
paths:
  /hello_world:
    post:
      operationId: myapp.api.hello_world
```

If you provide this path in your specification POST requests to
`http://MYHOST/hello_world`, it will be handled by the function
`hello_world` in the `myapp.api` module. Optionally, you can include
`x-swagger-router-controller` (or `x-openapi-router-controller`) in your
operation definition, making `operationId` relative:

```yaml
paths:
  /hello_world:
    post:
      x-swagger-router-controller: myapp.api
      operationId: hello_world
```

Keep in mind that Específico follows how `HTTP methods work in Flask`_ and therefore HEAD requests will be handled by the `operationId` specified under GET in the specification. If both methods are supported, `especifico.request.method` can be used to determine which request was made.

### Automatic Routing

To customize this behavior, Específico can use alternative
`Resolvers`--for example, `RestyResolver`. The `RestyResolver`
will compose an `operationId` based on the path and HTTP method of
the endpoints in your specification:

```python
from especifico.resolver import RestyResolver

app = especifico.App(__name__)
app.add_api('swagger.yaml', resolver=RestyResolver('api'))
```

```yaml
paths:
 /:
   get:
      # Implied operationId: api.get
 /foo:
   get:
      # Implied operationId: api.foo.search
   post:
      # Implied operationId: api.foo.post

 '/foo/{id}':
   get:
      # Implied operationId: api.foo.get
   put:
      # Implied operationId: api.foo.put
   copy:
      # Implied operationId: api.foo.copy
   delete:
      # Implied operationId: api.foo.delete
```

`RestyResolver` will give precedence to any `operationId` encountered in the specification. It will also respect
`x-router-controller`. You can import and extend `especifico.resolver.Resolver` to implement your own `operationId`
(and function) resolution algorithm.

### Automatic Parameter Handling

Específico automatically maps the parameters defined in your endpoint specification to arguments of your Python views as named parameters, and, whenever possible, with value casting. Simply define the endpoint's parameters with the same names as your views arguments.

As an example, say you have an endpoint specified as:

```yaml
paths:
  /foo:
    get:
      operationId: api.foo_get
      parameters:
        - name: message
          description: Some message.
          in: query
          type: string
          required: true
```

And the view function:

```python
# api.py file

def foo_get(message):
    # do something
    return 'You send the message: {}'.format(message), 200
```

In this example, Específico automatically recognizes that your view
function expects an argument named `message` and assigns the value
of the endpoint parameter `message` to your view function.

> In the OpenAPI 3.x.x spec, the requestBody does not have a name.
  By default it will be passed in as 'body'. You can optionally
  provide the x-body-name parameter in your requestBody
  (or legacy position within the requestBody schema)
  to override the name of the parameter that will be passed to your
  handler function.

```yaml
/path
  post:
    requestBody:
      x-body-name: body
      content:
        application/json:
          schema:
            # legacy location here should be ignored because the preferred location for x-body-name is at the requestBody level above
            x-body-name: this_should_be_ignored
            $ref: '#/components/schemas/someComponent'
```

> When you define a parameter at your endpoint as *not* required, and
  this argument does not have default value in your Python view, you will get
  a "missing positional argument" exception whenever you call this endpoint
  WITHOUT the parameter. Provide a default value for a named argument or use
  `**kwargs` dict.

### Type casting

Whenever possible, Específico will try to parse your argument values and
do type casting to related Python native values. The current
available type castings are:

+--------------+-------------+
| OpenAPI Type | Python Type |
+==============+=============+
| integer      | int         |
+--------------+-------------+
| string       | str         |
+--------------+-------------+
| number       | float       |
+--------------+-------------+
| boolean      | bool        |
+--------------+-------------+
| array        | list        |
+--------------+-------------+
| null         | None        |
+--------------+-------------+
| object       | dict        |
+--------------+-------------+

If you use the `array` type In the Swagger definition, you can define the
`collectionFormat` so that it won't be recognized. Específico currently
supports collection formats "pipes" and "csv". The default format is "csv".

Específico is opinionated about how the URI is parsed for `array` types.
The default behavior for query parameters that have been defined multiple
times is to use the right-most value. For example, if you provide a URI with
the the query string `?letters=a,b,c&letters=d,e,f`, especifico will set
`letters = ['d', 'e', 'f']`.

You can override this behavior by specifying the URI parser in the app or
api options.

```python
from especifico.decorators.uri_parsing import AlwaysMultiURIParser
options = {'uri_parser_class': AlwaysMultiURIParser}
app = especifico.App(__name__, specification_dir='swagger/', options=options)
```

You can implement your own URI parsing behavior by inheriting from
`especifico.decorators.uri_parsing.AbstractURIParser`.

There are a handful of URI parsers included with connection.

----------------------+---------------------------------------------------------------------------
 OpenAPIURIParser     | This parser adheres to the OpenAPI 3.x.x spec, and uses the `style`
 default: OpenAPI 3.0 | parameter. Query parameters are parsed from left to right, so if a query
                      | parameter is defined twice, then the right-most definition will take
                      | precedence. For example, if you provided a URI with the query string
                      | `?letters=a,b,c&letters=d,e,f`, and `style: simple`, then especifico
                      | will set `letters = ['d', 'e', 'f']`. For additional information see
                      | [OpenAPI 3.0 Style Values`](https://github.com/OAI/OpenAPI-Specification/blob/master/versions/3.0.2.md#style-values).
----------------------+---------------------------------------------------------------------------
 Swagger2URIParser    | This parser adheres to the Swagger 2.0 spec, and will only join together 
 default: OpenAPI 2.0 | multiple instance of the same query parameter if the `collectionFormat`
                      | is set to `multi`. Query parameters are parsed from left to right, so
                      | if a query parameter is defined twice, then the right-most definition 
                      | wins. For example, if you provided a URI with the query string
                      | `?letters=a,b,c&letters=d,e,f`, and `collectionFormat: csv`, then
                      | especifico will set `letters = ['d', 'e', 'f']`
----------------------+---------------------------------------------------------------------------
 FirstValueURIParser  | This parser behaves like the Swagger2URIParser, except that it prefers
                      | the first defined value. For example, if you provided a URI with the query
                      | string `?letters=a,b,c&letters=d,e,f` and `collectionFormat: csv`
                      | hen especifico will set `letters = ['a', 'b', 'c']`
----------------------+---------------------------------------------------------------------------
 AlwaysMultiURIParser | This parser is backwards compatible with Específico 1.x. It joins together
                      | multiple instances of the same query parameter.
----------------------+---------------------------------------------------------------------------


### Parameter validation

Específico can apply strict parameter validation for query and form data
parameters.  When this is enabled, requests that include parameters not defined
in the swagger spec return a 400 error.  You can enable it when adding the API
to your application:

```python
app.add_api('my_apy.yaml', strict_validation=True)
```

### API Versioning and basePath

Setting a base path is useful for versioned APIs. An example of
a base path would be the `1.0` in `http://MYHOST/1.0/hello_world`.

If you are using OpenAPI 3.x.x, you set your base URL path in the
servers block of the specification. You can either specify a full
URL, or just a relative path.

```yaml
servers:
  - url: https://MYHOST/1.0
    description: full url example
  - url: /1.0
    description: relative path example

paths:
  ...
```

If you are using OpenAPI 2.0, you can define a `basePath` on the top level
of your OpenAPI 2.0 specification.

```yaml
basePath: /1.0

paths:
  ...
```

If you don't want to include the base path in your specification, you
can provide it when adding the API to your application:

```python
app.add_api('my_api.yaml', base_path='/1.0')
```

### Swagger JSON

Específico makes the OpenAPI/Swagger specification in JSON format
available from either `swagger.json` (for OpenAPI 2.0) or
`openapi.json` (for OpenAPI 3.x.x) at the base path of the API.
For example, if your base path was `1.0`, then your spec would be
available at `/1.0/openapi.json`.

You can disable serving the spec JSON at the application level:

```python
options = {"serve_spec": False}
app = especifico.App(__name__, specification_dir='openapi/',
                    options=options)
app.add_api('my_api.yaml')
```

You can also disable it at the API level:

```python
options = {"serve_spec": False}
app = especifico.App(__name__, specification_dir='openapi/')
app.add_api('my_api.yaml', options=options)
```

### HTTPS Support

When specifying HTTPS as the scheme in the API YAML file, all the URIs
in the served Swagger UI are HTTPS endpoints. The problem: The default
server that runs is a "normal" HTTP server. This means that the
Swagger UI cannot be used to play with the API. What is the correct
way to start a HTTPS server when using Específico?

One way, [described by Flask](http://flask.pocoo.org/snippets/111/), looks like this:

```python
from OpenSSL import SSL
context = SSL.Context(SSL.SSLv23_METHOD)
context.use_privatekey_file('yourserver.key')
context.use_certificate_file('yourserver.crt')

app.run(host='127.0.0.1', port='12344',
       debug=False/True, ssl_context=context)
```

However, Específico doesn't provide an ssl_context parameter. This is
because Flask doesn't, either--but it uses `**kwargs` to send the
parameters to the underlying [werkzeug](http://werkzeug.pocoo.org/) server.

The Swagger UI Console
----------------------

The Swagger UI for an API is available through pip extras.
You can install it with `pip install especifico[swagger-ui]`.
It will be served up at `{base_path}/ui/` where `base_path` is the
base path of the API.

You can disable the Swagger UI at the application level:

```python
app = especifico.App(__name__, specification_dir='openapi/',
                    options={"swagger_ui": False})
app.add_api('my_api.yaml')
```

You can also disable it at the API level:

```python
app = especifico.App(__name__, specification_dir='openapi/')
app.add_api('my_api.yaml', options={"swagger_ui": False})
```

If necessary, you can explicitly specify the path to the directory with
swagger-ui to not use the especifico[swagger-ui] distro.
In order to do this, you should specify the following option:

```python
options = {'swagger_path': '/path/to/swagger_ui/'}
app = especifico.App(__name__, specification_dir='openapi/', options=options)
```

If you wish to provide your own swagger-ui distro, note that especifico
expects a jinja2 file called `swagger_ui/index.j2` in order to load the
correct `swagger.json` by default. Your `index.j2` file can use the
`openapi_spec_url` jinja variable for this purpose:

```js
const ui = SwaggerUIBundle({ url: "{{ openapi_spec_url }}"})
```

Additionally, if you wish to use swagger-ui-3.x.x, it is also provided by
installing especifico[swagger-ui], and can be enabled like this:

```python
from swagger_ui_bundle import swagger_ui_3_path
options = {'swagger_path': swagger_ui_3_path}
app = especifico.App(__name__, specification_dir='swagger/', options=options)
```

### Server Backend

By default Específico uses the [Flask](http://flask.pocoo.org/) server. For asynchronous
applications, you can also use [Tornado](http://www.tornadoweb.org/en/stable/) as the HTTP server. To do
this, set your server to `tornado`:

```python
import especifico

app = especifico.App(__name__, specification_dir='swagger/')
app.run(server='tornado', port=8080)
```

You can use the Flask WSGI app with any WSGI container, e.g.
[using Flask with uWSGI](http://flask.pocoo.org/docs/latest/deploying/uwsgi/) (this is common):

```python
app = especifico.App(__name__, specification_dir='swagger/')
application = app.app # expose global WSGI application object
```

You can use the `aiohttp` framework as server backend as well:

```python
import especifico

app = especifico.AioHttpApp(__name__, specification_dir='swagger/')
app.run(port=8080)
```

> Also check aiohttp handler [examples](https://docs.aiohttp.org/en/stable/web.html#handler).

Set up and run the installation code:

```bash
$ sudo pip3 install uwsgi
$ uwsgi --http :8080 -w app -p 16  # use 16 worker processes
```

See the [uWSGI documentation](https://uwsgi-docs.readthedocs.org/) for more information.

## Documentation
Additional information is available at [Específico's Documentation Page](docs/).

## Changes

A full changelog is maintained on the [GitHub releases page](https://github.com/athenianco/especifico/releases).

## Contributions

We welcome your ideas, issues, and pull requests. Just follow the
usual/standard GitHub practices.

You can find out more about how Específico works and where to apply your changes by having a look
at our [ARCHITECTURE.rst](ARCHITECTURE.rst).

Unless you explicitly state otherwise in advance, any non trivial
contribution intentionally submitted for inclusion in this project by you
to the steward of this repository (Zalando SE, Berlin) shall be under the
terms and conditions of Apache License 2.0 written below, without any
additional copyright information, terms or conditions.

If you'd like to become a more consistent contributor to Específico, we'd love your help working on
these we have a list of [issues where we are looking for contributions](https://github.com/athenianco/especifico/issues?q=is%3Aissue+is%3Aopen+label%3A%22help+wanted%22).

Thanks
===================

We'd like to thank all of Connexion's contributors for working on this
project, and to Swagger/OpenAPI for their support.

License
===================

Copyright 2015 Zalando SE, 2022 Athenian SAS

Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except in compliance with the License. You may obtain a copy of the License at http://www.apache.org/licenses/LICENSE-2.0.

Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific language governing permissions and limitations under the License.
