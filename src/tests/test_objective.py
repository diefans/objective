# coding: utf-8
# this is the test section
import pytest


def test_validate():
    import objective

    v = objective.Validator()

    assert v(None, 'foo') == 'foo'


def test_validator_inheritance():
    import objective

    class Foo(objective.Int):
        def _validator(self, node, value, environment=None):
            return "foo"

    class Bar(Foo):
        pass

    class Baz(Bar):
        def _validator(self, node, value, environment=None):
            return "baz"

    foo = Foo()
    assert foo.deserialize("123") == "foo"

    bar = Bar()
    assert bar.deserialize("123") == "foo"

    baz = Baz()
    assert baz.deserialize("123") == "baz"

    baz2 = Baz(validator=lambda _, x, e=None: "bam")
    assert baz2.deserialize("123") == "bam"


def test_optional():
    import objective

    class M(objective.Mapping):
        missing = objective.Item(objective.Field, optional=True)

    assert M().deserialize({}) == {}


def test_invalid_generator():
    import objective
    import six

    class M(objective.Mapping):
        foo = objective.Item(objective.Field)
        bam = objective.Item(objective.Field, missing=objective.Ignore)
        fom = objective.Item(objective.Field, missing='default')

        @objective.Item(missing=objective.Ignore)
        class biz(objective.Mapping):
            baz = objective.Item(objective.Field)
            xyz = objective.Item(objective.Field)

        @objective.Item()
        class bar(objective.Mapping):
            baz = objective.Item(objective.Field)
            xyz = objective.Item(objective.Field)

            @objective.Item()
            class bar2(objective.Mapping):
                baz2 = objective.Item(objective.Field)
                xyz2 = objective.Item(objective.Field)

    with pytest.raises(objective.Invalid) as err:
        M().deserialize({'bar': {'bar2': {}}})

    errors = {path: invalid.message
              for path, invalid in six.iteritems(err.value.error_dict())}

    assert errors == {
        ('foo',): 'Value for `foo` is missing!',
        ('bar',): 'Invalid value for `bar`: <Undefined>',
        ('bar', 'baz'): 'Value for `baz` is missing!',
        ('bar', 'xyz'): 'Value for `xyz` is missing!',
        ('bar', 'bar2'): 'Invalid value for `bar2`: <Undefined>',
        ('bar', 'bar2', 'baz2'): 'Value for `baz2` is missing!',
        ('bar', 'bar2', 'xyz2'): 'Value for `xyz2` is missing!'
    }


class TestFields(object):

    def test_schema(self):
        import objective

        class S(objective.core.Node):
            foo = objective.Item(objective.Field)

        assert issubclass(S.foo, objective.core.Node)

        s = S()

        assert isinstance(s.foo, objective.core.Node)
        assert isinstance(s.foo, objective.Field)

    def test_mapping(self):
        import objective

        class M(objective.Mapping):
            foo = objective.Item(objective.Field)
            bar = objective.Item(objective.Field)
            bam = objective.Item(objective.Field, missing=objective.Ignore)
            fom = objective.Item(objective.Field, missing='default')

        m = M()

        result = m.deserialize({
            'foo': 'foo',
            'bar': 'bar',
            'baz': 'baz'    # this should be ignored
        })

        assert result == {
            'foo': 'foo',
            'bar': 'bar',
            'fom': 'default'
        }

    def test_nested_mapping(self):
        import objective

        class M(objective.Mapping):
            foo = objective.Item(objective.Field)
            bam = objective.Item(objective.Field, missing=objective.Ignore)

            @objective.Item()
            class baz(objective.Mapping):
                foo = objective.Item(objective.Field)
                bam = objective.Item(objective.Field, missing="bar")

        m = M()

        result = m.deserialize({
            'foo': 123,
            'baz': {
                'foo': 'bar'
            }
        })

        assert result == {
            'foo': 123,
            'baz': {
                'foo': 'bar',
                'bam': 'bar'
            }
        }

    def test_mapping_missing(self):
        import objective
        import objective.exc

        class M(objective.Mapping):
            foo = objective.Item(objective.Field, missing='1')
            bar = objective.Item(objective.Field)

            @objective.Item()
            class bam(objective.Mapping):

                foo = objective.Item(objective.Field)
                fom = objective.Item(objective.Field, missing='default')

        m = M(name='m')

        with pytest.raises(objective.Invalid) as ex:
            m.deserialize({'bam': {}})

        # order is not sure
        assert isinstance(ex.value, objective.exc.InvalidChildren)

        ex_nodes = {c.node for c in ex.value.children}

        assert m.bam in ex_nodes
        assert m.bar in ex_nodes
        # assert ex.value.children[0].children[0].node == m.bam.foo


class TestNumber(object):
    def test_number_int(self):
        import objective

        n = objective.Number().deserialize("123")
        assert n == 123

    def test_number_float(self):
        import objective

        n = objective.Number().deserialize("123.456")
        assert n == 123.456

    def test_number_mapping(self):
        import objective

        class M(objective.Mapping):
            n = objective.Item(objective.Number)
            m = objective.Item(objective.Number, missing="456")

        m = M()

        assert m.deserialize({'n': "123"}) == {'n': 123, 'm': 456}
        assert m.deserialize({'n': "123", 'm': "123.456"}) == {'n': 123, 'm': 123.456}

    def test_number_mapping_invalid(self):
        import objective
        import objective.exc

        class M(objective.Mapping):
            n = objective.Item(objective.Number)
            m = objective.Item(objective.Number, missing="456")

        m = M()

        with pytest.raises(objective.Invalid) as ex:
            m.deserialize({'n': "foo"})

        assert isinstance(ex.value, objective.exc.InvalidChildren)
        assert ex.value.children[0].node == m.n

    def test_number_invalid(self):
        import objective
        import objective.exc

        with pytest.raises(objective.exc.InvalidValue):
            objective.Number().deserialize("foo")


class TestList(object):
    def test_list(self):
        import objective

        result = objective.List().deserialize([1, 2, 3])

        assert result == [1, 2, 3]

    def test_set_pure(self):
        import objective

        result = objective.Set().deserialize([1, 2, 3])

        assert result == {1, 2, 3}

    def test_set_unicode(self):
        import objective

        class C(objective.Set):
            items = objective.Item(objective.Unicode)

        result = C().deserialize([1, "ä", 3])
        assert result == {u'1', u'\xe4', u'3'}

        result = objective.Set(items=objective.Item(objective.Unicode)).deserialize([1, "ä", 3])
        assert result == {u'1', u'\xe4', u'3'}

    def test_list_in_mapping1(self):
        import objective

        class M(objective.Mapping):
            @objective.Item()
            class tags(objective.List):
                items = objective.Item(objective.Unicode)

        m = M()

        result = m.deserialize({"tags": [1, 2, 3]})

        assert result == {"tags": [u"1", u"2", u"3"]}

    def test_list_in_mapping2(self):
        import objective

        class M(objective.Mapping):
            tags = objective.Item(objective.List, items=objective.Item(objective.Unicode))

        m = M()

        result = m.deserialize({"tags": [1, 2, 3]})

        assert result == {"tags": [u"1", u"2", u"3"]}


def test_serialize():
    import objective

    dct = {
        'foo': {
            'bar': {1, 2, 3},
            'baz': [{'x': 1}, {'x': 2}],
            'omit': "foobar"
        }
    }

    class M(objective.Mapping):
        @objective.Item()
        class foo(objective.Mapping):
            @objective.Item()
            class bar(objective.List):
                items = objective.Item(objective.Unicode)

            @objective.Item()
            class baz(objective.Set):
                @objective.Item()
                class items(objective.Mapping):
                    x = objective.Item(objective.Number)

    m = M()

    assert m.serialize(dct) == {'foo': {'bar': ['1', '2', '3'], 'baz': [{'x': 1}, {'x': 2}]}}


def test_serialize_missing_ignore():
    import objective
    import objective.values
    import objective.exc

    dct = {"foo": 123}

    class M(objective.Mapping):
        foo = objective.Item(objective.Field)
        bar = objective.Item(objective.Field)
        baz = objective.Item(objective.Field, missing=objective.Ignore)

    m = M()
    with pytest.raises(objective.exc.InvalidChildren) as e:
        m.serialize(dct)

    assert e.value.children[0].node.__name__ == 'bar'
    assert e.value.children[0].value == objective.values.Undefined


class TestDateTime(object):

    @pytest.mark.parametrize("ds", [
        "2014-05-07T14:19:09.522Z",
        "2014-05-07 14:19:09.522000+00:00",
        1399472349.522,
    ])
    def test_deserialize(self, ds):
        import objective.fields

        result = objective.fields.dateutil_parse("2014-05-07T14:19:09.522Z")
        f = objective.fields.UtcDateTime()

        assert f.deserialize(ds) == result


class TestNode(object):

    def test_schema(self):
        import objective.core

        class Schema(objective.core.Node):

            foo = objective.Item(objective.core.Node)
            _bar = objective.Item(objective.core.Node, name='bar')

            @objective.Item(name='sub')
            class _sub(objective.core.Node):
                fom = objective.Item(objective.core.Node)

        s = Schema()

        assert isinstance(s, objective.core.Node)
        assert isinstance(s.foo, objective.core.Node)
        assert isinstance(s._bar, objective.core.Node)
        assert isinstance(s._sub, objective.core.Node)
        assert isinstance(s._sub.fom, objective.core.Node)
        assert issubclass(Schema.foo, objective.core.Node)

    def test__name__(self):
        import objective.core

        class S(objective.core.Node):

            foo = objective.Item(objective.core.Node)
            bar = objective.Item(objective.core.Node, name='BAR')

        s = S()

        assert s.foo.__name__ == 'foo'
        assert s.bar.__name__ == 'BAR'

    def test_iter(self):
        import objective.core

        class S(objective.core.Node):
            foo = objective.Item(objective.core.Node)
            bar = objective.Item(objective.core.Node)

        s = S()

        items = list(s)

        assert ('foo', s.foo) in items
        assert ('bar', s.bar) in items

    def test_inheritance(self):
        import objective.core

        class S1(objective.core.Node):
            foo = objective.Item(objective.core.Node)

        class S2(S1):
            bar = objective.Item(objective.core.Node)

        class S3(objective.core.Node):
            bam = objective.Item(objective.core.Node)

        class S4(S2, S3):
            bar = objective.Item(objective.core.Node)

        assert 'foo' in S4.__names__
        assert 'bar' in S4.__names__
        assert 'bam' in S4.__names__

    def test_getitem(self):
        import objective.core

        class S1(objective.core.Node):
            foo = objective.Item(objective.core.Node)

            @objective.Item(name='bam')
            class bar(objective.core.Node):
                baz = objective.Item(objective.core.Node)
                bim = objective.Item(objective.core.Node)

        s = S1()

        assert isinstance(s['foo'], objective.core.Node)
        assert isinstance(s['bam'], objective.core.Node)
        assert isinstance(s['bam']['baz'], objective.core.Node)

        # test id
        assert id(s['foo']) == id(s['foo'])

        with pytest.raises(KeyError) as ex:
            s['bam']['missing']         # pylint: disable=W0104

        assert ex.value.args == ('`missing` not in <bar:bam [baz, bim]>',)


def test_body_missing_bug():
    import objective

    class M(objective.Mapping):
        @objective.Item(missing={})
        class body(objective.Mapping):
            foo = objective.Item(objective.Field, optional=True)

    m = M()

    result = m.deserialize({})
    assert result == {'body': {}}


def test_multiple_inheritance():
    import objective

    class A(objective.Mapping):
        foo = objective.Item(objective.Field)

    class B(objective.Mapping):
        bar = objective.Item(objective.Field)

    class C(A, B):
        baz = objective.Item(objective.Field)

    assert [name for name, _ in C] == ["foo", "bar", "baz"]
    assert [name for name, _ in C()] == ["foo", "bar", "baz"]


def test_steal_class():
    import objective

    class A(objective.Mapping):

        @objective.Item()
        class foo(objective.Mapping):
            bar = objective.Item(objective.Unicode)

    class B(objective.Mapping):

        @objective.Item()
        class foo(A.foo):
            bar = objective.Item(objective.Unicode, missing=objective.Ignore)

    assert issubclass(A().foo.bar._missing, objective.core.Missing)
    assert issubclass(B().foo.bar._missing, objective.Ignore)


def test_bunch():
    import objective

    class A(objective.BunchMapping):
        foo = objective.Item(objective.Unicode)

    assert A().deserialize({'foo': "bar"}).foo == 'bar'


def test_unicode():
    import objective
    import six

    u = objective.Unicode()

    assert type(u.deserialize("abc")) == six.text_type
    assert type(u.deserialize(123)) == six.text_type

    v = u.serialize(six.text_type("123"))

    assert v == "123"


def test_utc():
    import objective
    import datetime

    utc = objective.UtcDateTime()

    assert utc.deserialize("2001-09-11 10:42:03") == datetime.datetime(2001, 9, 11, 10, 42, 3)
    assert utc.serialize(datetime.datetime(2001, 9, 11, 10, 42, 3)) == '2001-09-11 10:42:03'


def test_schema():
    import objective

    class RegisterUserObjective(objective.BunchMapping):
        @objective.Item()
        class body(objective.BunchMapping):
            email = objective.Item(objective.Unicode, validator=objective.Email())
            # TODO make password min length and some uppercase and digits
            password = objective.Item(objective.Unicode, missing=objective.Ignore)

    class LoginUserObjective(objective.BunchMapping):
        @objective.Item()
        class body(RegisterUserObjective.body):
            # just enforce password
            password = objective.Item(objective.Unicode)

    o = LoginUserObjective()

    s = o.deserialize({
        'body': {
            'password': "foo",
            "email": "foo@example.com"
        }
    })

    assert s == {
        'body': {
            'password': "foo",
            "email": "foo@example.com"
        }
    }


def test_order():
    import objective

    class Foo(objective.Mapping):
        _1 = objective.Item(objective.Field)
        _2 = objective.Item(objective.Field)
        _3 = objective.Item(objective.Field)

    class Bar(Foo):
        _4 = objective.Item(objective.Field)
        _1 = objective.Item(objective.Field)

    bar = Bar()
    assert [name for name, node in bar] == ['_1', '_2', '_3', '_4']


@pytest.mark.parametrize('value,result', [
    ('y', True),
    ('n', False),
    ('yes', True),
    ('true', True),
    (True, True),
    (False, False),
    ('Enabled', True),
    ('1', True),
    ('0', False),
    (1, True),
    (0, False),
    ('t', True),
    ('On', True),
    ('foo', False)

])
def test_bool(value, result):
    import objective

    o = objective.Bool()
    s = o.deserialize(value)

    assert s == result


@pytest.mark.parametrize('value,result', [
    (True, '0'),
    (False, '1'),
    (None, '2'),
])
def test_value_map(value, result):
    import objective

    v = objective.ValueMap({True: '0', False: '1'}, default='2')

    assert v(None, value) == result


@pytest.mark.parametrize('value,result', [
    (True, False),
    (False, True),
    (None, False),
])
def test_chain(value, result):
    import objective

    v = objective.Chain(
        objective.ValueMap({True: 'False', False: 'On'}, default='2'),
        objective.FieldValue(objective.Bool)
    )

    assert v(None, value) == result


def test_list_items_error():
    import objective
    import six

    class Bar(objective.Mapping):
        x = objective.Item(objective.Unicode)
        y = objective.Item(objective.Unicode)

    class Foo(objective.Mapping):

        @objective.Item(missing=objective.Ignore)
        class bar(objective.List):
            items = objective.Item(Bar)

        @objective.Item(missing=objective.Ignore)
        class baz(objective.List):
            @objective.Item()
            class items(objective.Mapping):
                x = objective.Item(objective.Unicode)
                y = objective.Item(objective.Unicode)

    value = {
        'body': {
            'bar': [{'x': 'a', 'y': 'b'}, {}],
            'baz': [{}],
        }
    }

    class Request(objective.BunchMapping):
        body = objective.Item(Foo)

    request = Request()

    with pytest.raises(objective.Invalid) as err:
        request.deserialize(value)

    errors = {path: invalid.message
              for path, invalid in six.iteritems(err.value.error_dict())}

    assert errors == {
        ('body',): 'Invalid value for `body`: <Undefined>',
        ('body', 'bar'): 'Invalid value for `bar`: <Undefined>',
        ('body', 'bar', 1): 'Invalid value for `1`: <Undefined>',
        ('body', 'bar', 1, 'x'): 'Value for `x` is missing!',
        ('body', 'bar', 1, 'y'): 'Value for `y` is missing!',
        ('body', 'baz'): 'Invalid value for `baz`: <Undefined>',
        ('body', 'baz', 0): 'Invalid value for `0`: <Undefined>',
        ('body', 'baz', 0, 'x'): 'Value for `x` is missing!',
        ('body', 'baz', 0, 'y'): 'Value for `y` is missing!'
    }


class TestContainer:
    def test_int_is_no_list(self):
        import objective

        class Foo(objective.List):
            items = objective.Item(objective.Field)

        foo = Foo()
        with pytest.raises(objective.Invalid) as e:
            d = foo.deserialize(1)

    def test_list_is_no_dict(self):
        import objective

        class Foo(objective.Mapping):
            bar = objective.Item(objective.Field)

        foo = Foo()
        with pytest.raises(objective.Invalid) as e:
            d = foo.deserialize([])
