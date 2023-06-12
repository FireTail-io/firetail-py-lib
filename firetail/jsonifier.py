"""
This module centralizes all functionality related to json encoding and decoding in Firetail.
"""

import datetime
import json
import uuid


class JSONEncoder(json.JSONEncoder):
    """The default Firetail JSON encoder. Handles extra types compared to the
    built-in :class:`json.JSONEncoder`. # noqa RST304

    -   :class:`datetime.datetime` and :class:`datetime.date` are   # noqa RST304
        serialized to :rfc:`822` strings. This is the same as the HTTP
        date format.
    -   :class:`uuid.UUID` is serialized to a string.  # noqa RST304
    """

    def default(self, o):
        if isinstance(o, datetime.datetime):
            if o.tzinfo:
                # eg: '2015-09-25T23:14:42.588601+00:00'
                return o.isoformat("T")
            else:
                # No timezone present - assume UTC.
                # eg: '2015-09-25T23:14:42.588601Z'
                return o.isoformat("T") + "Z"

        if isinstance(o, datetime.date):
            return o.isoformat()

        if isinstance(o, uuid.UUID):
            return str(o)

        return json.JSONEncoder.default(self, o)


class Jsonifier:
    """
    Central point to serialize and deserialize to/from JSon in Firetail.
    """

    def __init__(self, json_=json, **kwargs):
        """
        :param json_: json library to use. Must have loads() and dumps() method  # NOQA
        :param kwargs: default arguments to pass to json.dumps()
        """
        self.json = json_
        self.dumps_args = kwargs

    def dumps(self, data, **kwargs):
        """Central point where JSON serialization happens inside
        Firetail.
        """
        for k, v in self.dumps_args.items():
            kwargs.setdefault(k, v)
        return self.json.dumps(data, **kwargs) + "\n"

    def loads(self, data):
        """Central point where JSON deserialization happens inside
        Firetail.
        """
        if isinstance(data, bytes):
            data = data.decode()

        try:
            return self.json.loads(data)
        except Exception:
            if isinstance(data, str):
                return data
