# openhands.sdk.utils.json

## Classes

### OpenHandsJSONEncoder

Custom JSON encoder that handles datetime and other OH objects

#### Functions

##### default(self, o: object) -> Any

Implement this method in a subclass such that it returns
a serializable object for ``o``, or calls the base implementation
(to raise a ``TypeError``).

For example, to support arbitrary iterators, you could
implement default like this::

    def default(self, o):
        try:
            iterable = iter(o)
        except TypeError:
            pass
        else:
            return list(iterable)
        # Let the base class default method raise the TypeError
        return super().default(o)

##### encode(self, o)

Return a JSON string representation of a Python data structure.

>>> from json.encoder import JSONEncoder
>>> JSONEncoder().encode({"foo": ["bar", "baz"]})
'{"foo": ["bar", "baz"]}'

##### iterencode(self, o, _one_shot=False)

Encode the given object and yield each string
representation as available.

For example::

    for chunk in JSONEncoder().iterencode(bigobject):
        mysocket.write(chunk)

## Functions

### dumps(obj, **kwargs)

Serialize an object to str format

### loads(json_str, **kwargs)

Create a JSON object from str

