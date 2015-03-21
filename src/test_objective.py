# coding: utf-8
# this is the test section
import pytest


class TestValidator(object):

    def test_validate(self):
        import objective

        v = objective.Validator()

        assert v('foo') == 'foo'


def test_optional():
    import objective

    class M(objective.Mapping):
        missing = objective.Item(objective.Field, optional=True)

    assert M().deserialize({}) == {}


def test_invalid_generator():
    import objective

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

    errors = err.value.error_dict()

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

        class S(objective.Node):
            foo = objective.Item(objective.Field)

        assert isinstance(S.foo, objective.Item)

        s = S()

        assert isinstance(s.foo, objective.Node)
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

        assert isinstance(ex.value, objective.InvalidChildren)
        assert ex.value.children[0].node == m.bam
        assert ex.value.children[0].children[0].node == m.bam.foo
        assert ex.value.children[1].node == m.bar


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

        class M(objective.Mapping):
            n = objective.Item(objective.Number)
            m = objective.Item(objective.Number, missing="456")

        m = M()

        with pytest.raises(objective.Invalid) as ex:
            m.deserialize({'n': "foo"})

        assert isinstance(ex.value, objective.InvalidChildren)
        assert ex.value.children[0].node == m.n

    def test_number_invalid(self):
        import objective

        with pytest.raises(objective.InvalidValue):
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

    assert m.serialize(dct) == {'foo': {'bar': set([1, 2, 3]), 'baz': [{'x': 1}, {'x': 2}]}}


def test_serialize_missing():
    import objective

    dct = {"foo": 123}

    class M(objective.Mapping):
        foo = objective.Item(objective.Field)
        bar = objective.Item(objective.Field)

    m = M()
    with pytest.raises(objective.InvalidChildren) as e:
        m.serialize(dct)

    assert e.value.children[0].node._name == 'bar'
    assert isinstance(e.value.children[0].value, objective.Undefined)


class TestDateTime(object):

    @pytest.mark.parametrize("ds", [
        "2014-05-07T14:19:09.522Z",
        "2014-05-07 14:19:09.522000+00:00",
        1399472349.522,
    ])
    def test_deserialize(self, ds):
        import objective

        result = objective.dateutil_parse("2014-05-07T14:19:09.522Z")
        f = objective.UtcDateTime()

        assert f.deserialize(ds) == result


class TestNode(object):

    def test_schema(self):
        import objective

        class Schema(objective.Node):

            foo = objective.Item(objective.Node)
            _bar = objective.Item(objective.Node, name='bar')

            @objective.Item(name='sub')
            class _sub(objective.Node):
                fom = objective.Item(objective.Node)

        s = Schema()

        assert isinstance(s, objective.Node)
        assert isinstance(s.foo, objective.Node)
        assert isinstance(s._bar, objective.Node)
        assert isinstance(s._sub, objective.Node)
        assert isinstance(s._sub.fom, objective.Node)
        assert isinstance(Schema.foo, objective.Item)

    def test_name(self):
        import objective

        class S(objective.Node):

            foo = objective.Item(objective.Node)
            bar = objective.Item(objective.Node, name='BAR')

        s = S()

        assert s.foo._name == 'foo'
        assert s.bar._name == 'BAR'

    def test_iter(self):
        import objective

        class S(objective.Node):
            foo = objective.Item(objective.Node)
            bar = objective.Item(objective.Node)

        s = S()

        items = list(s)

        assert ('foo', s.foo) in items
        assert ('bar', s.bar) in items

    def test_inheritance(self):
        import objective

        class S1(objective.Node):
            foo = objective.Item(objective.Node)

        class S2(S1):
            bar = objective.Item(objective.Node)

        class S3(objective.Node):
            bam = objective.Item(objective.Node)

        class S4(S2, S3):
            bar = objective.Item(objective.Node)

        assert 'foo' in S4._children
        assert 'bar' in S4._children
        assert 'bam' in S4._children

    def test_getitem(self):
        import objective

        class S1(objective.Node):
            foo = objective.Item(objective.Node)

            @objective.Item(name='bam')
            class bar(objective.Node):
                baz = objective.Item(objective.Node)
                bim = objective.Item(objective.Node)

        s = S1()

        assert isinstance(s['foo'], objective.Node)
        assert isinstance(s['bam'], objective.Node)
        assert isinstance(s['bam']['baz'], objective.Node)

        # test id
        assert id(s['foo']) == id(s['foo'])

        with pytest.raises(KeyError) as ex:
            s['bam']['missing']         # pylint: disable=W0104

        assert ex.value.message == '`missing` not in <bar: baz, bim>'
