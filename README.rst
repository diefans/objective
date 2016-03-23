objective
=========

As a result of frustration working with colander, I decided to create something similar...

Objective is a de/serialization tool with following features:

- declarative definition of objectives.
- no confusion about how to define something, it is always the same.
- reuse definitions by inheritance.
- optional validation.
- make it simple to override certain parts.



Usage
-----



Simple mapping and validation
"""""""""""""""""""""""""""""

.. code-block:: python

    import objective
    import datetime


    now = datetime.datetime(2001, 9, 11)


    class UserObjective(objective.Mapping):

        name = objective.Item(objective.Unicode, missing=objective.Ignore)
        email = objective.Item(objective.Unicode, validator=objective.Email())
        password = objective.Item(objective.Unicode)
        since = objective.Item(objective.UtcDateTime, missing=now)


    serialized = {
        'email': 'foo@example.com',
        'password': 'foobar'
    }


    deserialized = UserObjective.deserialize(serialized)


    assert deserialized == {
        'password': u'foobar',
        'email': u'foo@example.com',
        'since': datetime.datetime(2001, 9, 11, 0, 0)
    }


    bad_serialized = {
        'name': 'foobar'
    }


    try:
        deserialized = UserObjective().deserialize(bad_serialized)

    except objective.Invalid as e:

        assert isinstance(e, objective.exc.InvalidChildren)
        assert {(x.node.__name__, x.__class__, x.value) for x in e.children} == {
            ('password', objective.exc.MissingValue, objective.values.Undefined),
            ('email', objective.exc.InvalidValue, 'baz')
        }


Mapping complex structures
""""""""""""""""""""""""""

.. code-block:: python

    import objective


    class ProductRequestObjective(objective.BunchMapping):
        @objective.Item()
        class body(objective.Mapping):
            name = objective.Item(objective.Unicode)
            root = objective.Item(objective.Unicode)

            @objective.Item()
            class semantics(objective.List):
                items = objective.Item(objective.Unicode)

        @objective.Item()
        class match(objective.Mapping):
            _id = objective.Item(objective.Field)


Issues, thoughts, ideas
-----------------------

objective is far from complete. There are tons of possible validators I can imagine.

I tried my best (mostly in terms of time) to test.

If you find bugs or you have a great idea, I am totally open to implement it.
