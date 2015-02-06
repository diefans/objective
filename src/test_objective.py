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
            s['bam']['missing']

        assert ex.value.message == '`missing` not in <bar: baz, bim>'
