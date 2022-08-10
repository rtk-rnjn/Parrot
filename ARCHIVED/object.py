#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Object is a subclass of dict with attribute-style access.
    >>> b = Object()
    >>> b.hello = 'world'
    >>> b.hello
    'world'
    >>> b['hello'] += "!"
    >>> b.hello
    'world!'
    >>> b.foo = Object(lol=True)
    >>> b.foo.lol
    True
    >>> b.foo is b['foo']
    True
    It is safe to import * from this module:
        __all__ = ('Object', 'objectify','unobjectify')
    un/objectify provide dictionary conversion; Munches can also be
    converted via Object.to/from_dict().
"""

import sys

__version__ = "2.0.2"
VERSION = tuple(map(int, __version__.split(".")))

__all__ = (
    "Object",
    "objectify",
    "unobjectify",
)

_PY2 = sys.version_info < (3, 0)

identity = lambda x: x

# u('string') replaces the forwards-incompatible u'string'
if _PY2:
    import codecs

    def u(string):
        return codecs.unicode_escape_decode(string)[0]

else:
    u = identity

# dict.iteritems(), dict.iterkeys() is also incompatible
if _PY2:
    iteritems = dict.iteritems  # type: ignore
    iterkeys = dict.iterkeys  # type: ignore
else:
    iteritems = dict.items
    iterkeys = dict.keys


class Object(dict):
    """A dictionary that provides attribute-style access.
    >>> b = Object()
    >>> b.hello = 'world'
    >>> b.hello
    'world'
    >>> b['hello'] += "!"
    >>> b.hello
    'world!'
    >>> b.foo = Object(lol=True)
    >>> b.foo.lol
    True
    >>> b.foo is b['foo']
    True
    A Object is a subclass of dict; it supports all the methods a dict does...
    >>> sorted(b.keys())
    ['foo', 'hello']
    Including update()...
    >>> b.update({ 'ponies': 'are pretty!' }, hello=42)
    >>> print (repr(b))
    Object(foo=Object(lol=True), hello=42, ponies='are pretty!')
    As well as iteration...
    >>> [ (k,b[k]) for k in b ]
    [('ponies', 'are pretty!'), ('foo', Object(lol=True)), ('hello', 42)]
    And "splats".
    >>> "The {knights} who say {ni}!".format(**Object(knights='lolcats', ni='can haz'))
    'The lolcats who say can haz!'
    See unobjectify/Object.to_dict, objectify/Object.from_dict for notes about conversion.
    """

    def __contains__(self, k):
        """>>> b = Object(ponies='are pretty!')
        >>> 'ponies' in b
        True
        >>> 'foo' in b
        False
        >>> b['foo'] = 42
        >>> 'foo' in b
        True
        >>> b.hello = 'hai'
        >>> 'hello' in b
        True
        >>> b[None] = 123
        >>> None in b
        True
        >>> b[False] = 456
        >>> False in b
        True
        """
        try:
            return dict.__contains__(self, k) or hasattr(self, k)
        except Exception:
            return False

    # only called if k not found in normal places
    def __getattr__(self, k):
        """Gets key if it exists, otherwise throws AttributeError.
        nb. __getattr__ is only called if key is not found in normal places.
        >>> b = Object(bar='baz', lol={})
        >>> b.foo
        Traceback (most recent call last):
            ...
        AttributeError: foo
        >>> b.bar
        'baz'
        >>> getattr(b, 'bar')
        'baz'
        >>> b['bar']
        'baz'
        >>> b.lol is b['lol']
        True
        >>> b.lol is getattr(b, 'lol')
        True
        """
        try:
            return object.__getattribute__(self, k)
        except AttributeError:
            try:
                return self[k]
            except KeyError as e:
                raise AttributeError(k) from e

    def __setattr__(self, k, v):
        """Sets attribute k if it exists, otherwise sets key k. A KeyError
        raised by set-item (only likely if you subclass Object) will
        propagate as an AttributeError instead.
        >>> b = Object(foo='bar', this_is='useful when subclassing')
        >>> b.values                            #doctest: +ELLIPSIS
        <built-in method values of Object object at 0x...>
        >>> b.values = 'uh oh'
        >>> b.values
        'uh oh'
        >>> b['values']
        Traceback (most recent call last):
            ...
        KeyError: 'values'
        """
        try:
            # Throws exception if not in prototype chain
            object.__getattribute__(self, k)
        except AttributeError:
            try:
                self[k] = v
            except Exception as e:
                raise AttributeError(k) from e
        else:
            object.__setattr__(self, k, v)

    def __delattr__(self, k):
        """Deletes attribute k if it exists, otherwise deletes key k. A KeyError
        raised by deleting the key--such as when the key is missing--will
        propagate as an AttributeError instead.
        >>> b = Object(lol=42)
        >>> del b.values
        Traceback (most recent call last):
            ...
        AttributeError: 'Object' object attribute 'values' is read-only
        >>> del b.lol
        >>> b.lol
        Traceback (most recent call last):
            ...
        AttributeError: lol
        """
        try:
            object.__getattribute__(self, k)
        except AttributeError:
            try:
                del self[k]
            except KeyError as e:
                raise AttributeError(k) from e
        else:
            object.__delattr__(self, k)

    def to_dict(self):
        """Recursively converts a Object back into a dictionary.
        >>> b = Object(foo=Object(lol=True), hello=42, ponies='are pretty!')
        >>> b.to_dict()
        {'ponies': 'are pretty!', 'foo': {'lol': True}, 'hello': 42}
        See unobjectify for more info.
        """
        return unobjectify(self)

    def __repr__(self):
        """Invertible* string-form of a Object.
        >>> b = Object(foo=Object(lol=True), hello=42, ponies='are pretty!')
        >>> print (repr(b))
        Object(foo=Object(lol=True), hello=42, ponies='are pretty!')
        >>> eval(repr(b))
        Object(foo=Object(lol=True), hello=42, ponies='are pretty!')
        (*) Invertible so long as collection contents are each repr-invertible.
        """
        keys = sorted(iterkeys(self))
        args = ", ".join(["%s=%r" % (key, self[key]) for key in keys])
        return f"{self.__class__.__name__}({args})"

    def __dir__(self):
        return list(iterkeys(self))

    __members__ = __dir__  # for python2.x compatibility

    @staticmethod
    def from_dict(d):
        """Recursively transforms a dictionary into a Object via copy.
        >>> b = Object.from_dict({'urmom': {'sez': {'what': 'what'}}})
        >>> b.urmom.sez.what
        'what'
        See objectify for more info.
        """
        return objectify(d)


# While we could convert abstract types like Mapping or Iterable, I think
# objectify is more likely to "do what you mean" if it is conservative about
# casting (ex: isinstance(str,Iterable) == True ).
#
# Should you disagree, it is not difficult to duplicate this function with
# more aggressive coercion to suit your own purposes.


def objectify(x):
    """Recursively transforms a dictionary into a Object via copy.
    >>> b = objectify({'urmom': {'sez': {'what': 'what'}}})
    >>> b.urmom.sez.what
    'what'
    objectify can handle intermediary dicts, lists and tuples (as well as
    their subclasses), but ymmv on custom datatypes.
    >>> b = objectify({ 'lol': ('cats', {'hah':'i win again'}),
    ...         'hello': [{'french':'salut', 'german':'hallo'}] })
    >>> b.hello[0].french
    'salut'
    >>> b.lol[1].hah
    'i win again'
    nb. As dicts are not hashable, they cannot be nested in sets/frozensets.
    """
    if isinstance(x, dict):
        return Object((k, objectify(v)) for k, v in iteritems(x))
    return type(x)(objectify(v) for v in x) if isinstance(x, (list, tuple)) else x


def unobjectify(x):
    """Recursively converts a Object into a dictionary.
    >>> b = Object(foo=Object(lol=True), hello=42, ponies='are pretty!')
    >>> unobjectify(b)
    {'ponies': 'are pretty!', 'foo': {'lol': True}, 'hello': 42}
    unobjectify will handle intermediary dicts, lists and tuples (as well as
    their subclasses), but ymmv on custom datatypes.
    >>> b = Object(foo=['bar', Object(lol=True)], hello=42,
    ...         ponies=('are pretty!', Object(lies='are trouble!')))
    >>> unobjectify(b) #doctest: +NORMALIZE_WHITESPACE
    {'ponies': ('are pretty!', {'lies': 'are trouble!'}),
     'foo': ['bar', {'lol': True}], 'hello': 42}
    nb. As dicts are not hashable, they cannot be nested in sets/frozensets.
    """
    if isinstance(x, dict):
        return {(k, unobjectify(v)) for k, v in iteritems(x)}
    if isinstance(x, (list, tuple)):
        return type(x)(unobjectify(v) for v in x)
    return x


# Serialization

try:
    import orjson as json  # type: ignore
except ImportError:
    import json  # type: ignore


def to_json(self, **options):
    """Serializes this Object to JSON. Accepts the same keyword options as `json.dumps()`.
    >>> b = Object(foo=Object(lol=True), hello=42, ponies='are pretty!')
    >>> json.dumps(b)
    '{"ponies": "are pretty!", "foo": {"lol": true}, "hello": 42}'
    >>> b.to_json()
    '{"ponies": "are pretty!", "foo": {"lol": true}, "hello": 42}'
    """
    return (json.dumps(self, **options)).decode()


Object.to_json = to_json  # type: ignore

try:
    # Attempt to register ourself with PyYAML as a representer
    import yaml  # type: ignore
    from yaml.representer import Representer, SafeRepresenter  # type: ignore

    def from_yaml(loader, node):
        """PyYAML support for Munches using the tag `!object` and `!object.Object`.
        >>> import yaml
        >>> yaml.load('''
        ... Flow style: !object.Object { Clark: Evans, Brian: Ingerson, Oren: Ben-Kiki }
        ... Block style: !object
        ...   Clark : Evans
        ...   Brian : Ingerson
        ...   Oren  : Ben-Kiki
        ... ''') #doctest: +NORMALIZE_WHITESPACE
        {'Flow style': Object(Brian='Ingerson', Clark='Evans', Oren='Ben-Kiki'),
         'Block style': Object(Brian='Ingerson', Clark='Evans', Oren='Ben-Kiki')}
        This module registers itself automatically to cover both Object and any
        subclasses. Should you want to customize the representation of a subclass,
        simply register it with PyYAML yourself.
        """
        data = Object()
        yield data
        value = loader.construct_mapping(node)
        data.update(value)

    def to_yaml_safe(dumper, data):
        """Converts Object to a normal mapping node, making it appear as a
        dict in the YAML output.
        >>> b = Object(foo=['bar', Object(lol=True)], hello=42)
        >>> import yaml
        >>> yaml.safe_dump(b, default_flow_style=True)
        '{foo: [bar, {lol: true}], hello: 42}\\n'
        """
        return dumper.represent_dict(data)

    def to_yaml(dumper, data):
        """Converts Object to a representation node.
        >>> b = Object(foo=['bar', Object(lol=True)], hello=42)
        >>> import yaml
        >>> yaml.dump(b, default_flow_style=True)
        '!object.Object {foo: [bar, !object.Object {lol: true}], hello: 42}\\n'
        """
        return dumper.represent_mapping(u("!object.Object"), data)

    yaml.add_constructor(u("!object"), from_yaml)
    yaml.add_constructor(u("!object.Object"), from_yaml)

    SafeRepresenter.add_representer(Object, to_yaml_safe)
    SafeRepresenter.add_multi_representer(Object, to_yaml_safe)

    Representer.add_representer(Object, to_yaml)
    Representer.add_multi_representer(Object, to_yaml)

    # Instance methods for YAML conversion
    def toYAML(self, **options):
        """Serializes this Object to YAML, using `yaml.safe_dump()` if
        no `Dumper` is provided. See the PyYAML documentation for more info.
        >>> b = Object(foo=['bar', Object(lol=True)], hello=42)
        >>> import yaml
        >>> yaml.safe_dump(b, default_flow_style=True)
        '{foo: [bar, {lol: true}], hello: 42}\\n'
        >>> b.toYAML(default_flow_style=True)
        '{foo: [bar, {lol: true}], hello: 42}\\n'
        >>> yaml.dump(b, default_flow_style=True)
        '!object.Object {foo: [bar, !object.Object {lol: true}], hello: 42}\\n'
        >>> b.toYAML(Dumper=yaml.Dumper, default_flow_style=True)
        '!object.Object {foo: [bar, !object.Object {lol: true}], hello: 42}\\n'
        """
        opts = dict(indent=4, default_flow_style=False) | options
        if "Dumper" not in opts:
            return yaml.safe_dump(self, **opts)
        return yaml.dump(self, **opts)

    def fromYAML(*args, **kwargs):
        return objectify(yaml.safe_load(*args, **kwargs))

    Object.toYAML = toYAML  # type: ignore
    Object.fromYAML = staticmethod(fromYAML)  # type: ignore

except ImportError:
    pass

if __name__ == "__main__":
    import doctest

    doctest.testmod()
