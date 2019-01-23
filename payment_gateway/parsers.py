import json

import six
from django.conf import settings as django_settings
from rest_framework.exceptions import ParseError
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer


class CustomJSONParser(JSONParser):
    """
    Simple custom JSONParser parser that returns a raw body of the request in the request.data['raw_body'] item.
    """

    media_type = 'application/json'
    renderer_class = JSONRenderer

    def parse(self, stream, media_type=None, parser_context=None):
        """
        The method should return the data that will be used to populate the request.data property.
        """

        parser_context = parser_context or {}
        encoding = parser_context.get('encoding', django_settings.DEFAULT_CHARSET)

        try:
            raw_body = stream.read()
            data = raw_body.decode(encoding)
            result = json.loads(data)

            # Here we simply inject a raw body of the request.
            result['raw_body'] = raw_body

            return result

        except ValueError as exc:
            raise ParseError('JSON parse error - %s' % six.text_type(exc))
def parse(self, stream, media_type=None, parser_context=None):
        """
        The method should return the data that will be used to populate the request.data property.
        """

        parser_context = parser_context or {}
        encoding = parser_context.get('encoding', django_settings.DEFAULT_CHARSET)

        try:
            raw_body = stream.read()
            data = raw_body.decode(encoding)
            result = json.loads(data)

            # Here we simply inject a raw body of the request.
            result['raw_body'] = raw_body

            return result

        except ValueError as exc:
            raise ParseError('JSON parse error - %s' % six.text_type(exc))