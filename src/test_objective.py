# coding: utf-8
# this is the test section
import pytest


class TestValidator(object):

    def test_validate(self):
        import objective

        v = objective.Validator()

        assert v('foo') == 'foo'


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


class TestCollection(object):
    def test_list(self):
        import objective

        result = objective.Collection().deserialize([1, 2, 3])

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

    def test_list_in_mapping(self):
        import objective

        class M(objective.Mapping):
            tags = objective.Item(objective.Collection, items=objective.Field)

        m = M()

        result = m.deserialize({"tags": [1, 2, 3]})

        assert result == {"tags": [1, 2, 3]}


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
