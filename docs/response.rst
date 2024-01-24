Response Handling
=================

Response Serialization
----------------------
If the endpoint returns a `Response` object this response will be used as is.

Otherwise, by default and if the specification defines that an endpoint
produces only JSON, FireTail automatically serializes the return value
for you and sets the right content type in the HTTP header.

If the endpoint produces a single non-JSON mimetype then FireTail
automatically sets the right content type in the HTTP header.

Customizing JSON encoder
^^^^^^^^^^^^^^^^^^^^^^^^

FireTail allows you to customize the `JSONEncoder` class in the Flask app
instance `json_encoder` (`firetail.App:app`). If you want to reuse the
FireTail's date-time serialization, inherit your custom encoder from
`firetail.apps.flask_app.FlaskJSONProvider`.

For more information on the `JSONEncoder`, see the `Flask documentation`_.

.. _Flask Documentation: https://flask.palletsprojects.com/en/2.0.x/api/#flask.json.JSONEncoder

Returning status codes
----------------------
There are two ways of returning a specific status code.

One way is to return a `Response` object that will be used unchanged.

The other is returning it as a second return value in the response. 

For example:

.. code-block:: python

    def my_endpoint():
        return 'Not Found', 404

Returning Headers
-----------------
There are two ways to return headers from your endpoints.

One way is to return a `Response` object that will be used unchanged.

The other is returning a dict with the header values as the third return value
in the response.

For example:

.. code-block:: python

    def my_endpoint():
        return 'Not Found', 404, {'x-error': 'not found'}


Response Validation
-------------------
By default FireTail doesn't validate the responses it's possible to
do so by opting in when adding the API:

.. code-block:: python

    import firetail

    app = firetail.FlaskApp(__name__, specification_dir='swagger/')
    app.add_api('my_api.yaml', validate_responses=True)
    app.run(port=8080)

This validates all the responses using `jsonschema` and is specially useful
during development.


Custom Validator
-----------------

By default, response body contents are validated against OpenAPI schema
via ``firetail.decorators.response.ResponseValidator``, if you want to change
the validation, you can override the default class with:

.. code-block:: python

    validator_map = {
        'response': CustomResponseValidator
    }
    app = firetail.FlaskApp(__name__)
    app.add_api('api.yaml', ..., validator_map=validator_map)


Error Handling
--------------
By default FireTail error messages are JSON serialized according to
`Problem Details for HTTP APIs`_

Application can return errors using ``firetail.problem``.

.. _Problem Details for HTTP APIs: https://tools.ietf.org/html/draft-ietf-appsawg-http-problem-00
