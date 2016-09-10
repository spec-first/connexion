import connexion.swagger as swagger
import yaml
from connexion.exceptions import InvalidSpecification

import pytest


def test_pointer():
    ref = swagger.Pointer({'$ref': 'document#/key1/key2/~1key3/~01key4'}, 'directory/name.yaml', None)
    assert ref.path == 'directory/document'
    assert ref.keys == ['key1', 'key2', '/key3', '~1key4']


def test_pointer_no_document():
    ref = swagger.Pointer({'$ref': '#/key1'}, 'parent', None)
    assert ref.path == 'parent'
    assert ref.keys == ['key1']


def test_pointer_no_keys():
    ref = swagger.Pointer({'$ref': 'document'}, 'parent', None)
    assert ref.path == 'document'
    assert ref.keys == []


def test_pointers_equal():
    obj = {'$ref': 'document'}
    parent = 'parent'
    assert swagger.Pointer(obj, parent, None) == swagger.Pointer(obj, parent, None)


def test_resolve_not_in_cache(tmpdir):
    data = {'key': 'value'}
    schema_file = tmpdir.mkdir('resolve').join('definitions.yaml')
    schema_file.write(yaml.dump(data))
    resolver = swagger.Resolver({})
    value = resolver.get(str(schema_file), ['key'])
    assert value == data['key']
    assert resolver.cache == {str(schema_file): data}


def test_resolver_get_from_cache():
    resolver = swagger.Resolver({})
    resolver.cache = {'root.yaml': {'key': 'value'}}
    assert resolver.get('root.yaml', ['key']) is resolver.cache['root.yaml']['key']


def test_resolve_nested():
    resolver = swagger.Resolver({})
    resolver.cache = {'root.yaml': {'key': {'key': 'nested_value'}}}
    value = resolver.get('root.yaml', ['key', 'key'])
    assert value is resolver.cache['root.yaml']['key']['key']


def test_resolve_array():
    resolver = swagger.Resolver({})
    resolver.cache = {'root.yaml': {'key': ['', {'key2': 'in array'}]}}
    value = resolver.get('root.yaml', ['key', '1', 'key2'])
    assert value is resolver.cache['root.yaml']['key'][1]['key2']


def test_inventory_nested():
    resolver = swagger.Resolver({})
    resolver.cache['file.yaml'] = {'key_1': {'$ref': '#/key_2'},
                                   'key_2': 'value_2'}

    expected = [swagger.Pointer(resolver.cache['file.yaml']['key_1'], None, ['key_1'])]
    actual = swagger.inventory('file.yaml', resolver)

    assert actual == expected


def test_inventory_list():
    data = {'key_1': 'value',
            'key_2': [{'$ref': '#/key_1'}]}

    resolver = swagger.Resolver({})
    resolver.cache['file.yaml'] = data

    expected = [swagger.Pointer(resolver.cache['file.yaml']['key_2'][0], None, ['key_2', 0])]
    actual = swagger.inventory('file.yaml', resolver)

    assert actual == expected


def test_inventory_external():
    data_1 = {'key_1': 'value_1',
              'key_2': {'$ref': 'file_2.yaml'}}

    data_2 = {'key_3': 'value_3',
              'key_4': {'$ref': '#/key_3'}}

    resolver = swagger.Resolver({})
    resolver.cache['file_1.yaml'] = data_1
    resolver.cache['file_2.yaml'] = data_2

    expected = [swagger.Pointer(resolver.cache['file_1.yaml']['key_2'], '', ['key_2']),
                swagger.Pointer(resolver.cache['file_2.yaml']['key_4'], '', ['key_2', 'key_4'])]
    actual = swagger.inventory('file_1.yaml', resolver)

    assert actual == expected


def test_inventory_circular():
    data_1 = {'key': {'$ref': 'file_2.yaml'}}
    data_2 = {'key': {'$ref': 'file_1.yaml'}}

    resolver = swagger.Resolver({})
    resolver.cache['file_1.yaml'] = data_1
    resolver.cache['file_2.yaml'] = data_2

    expected = [swagger.Pointer(resolver.cache['file_1.yaml']['key'], '', ['key']),
                swagger.Pointer(resolver.cache['file_2.yaml']['key'], '', ['key', 'key'])]
    actual = swagger.inventory('file_1.yaml', resolver)

    assert actual == expected


def test_inventory_bad_file():
    data = {'key_1': {'key_2': {'$ref': 'badfile'}}}

    resolver = swagger.Resolver({})
    resolver.cache['file'] = data

    with pytest.raises(InvalidSpecification):
        swagger.inventory('file', resolver)


def test_inventory_bad_pointer():
    file_1 = {'key_1': {'key_2': {'$ref': 'file_2.yaml#/badkey'}}}
    file_2 = {'key_3': 'value'}

    resolver = swagger.Resolver({})
    resolver.cache = {'file_1.yaml': file_1,
                      'file_2.yaml': file_2}

    with pytest.raises(InvalidSpecification):
        swagger.inventory('file_1.yaml', resolver)


def test_load_circular(tmpdir):
    test_dir = tmpdir.mkdir('external')
    file_1 = test_dir.join('file_1.yaml')
    file_2 = test_dir.join('file_2.yaml')

    data_1 = {'key': {'$ref': str(file_2)}}
    data_2 = {'key': {'$ref': str(file_1)}}

    file_1.write(yaml.dump(data_1))
    file_2.write(yaml.dump(data_2))

    resolved = swagger.load(str(file_1), {})
    assert resolved == {'key': {'key': {'$ref': '#/'}}}


def test_load_external(tmpdir):
    test_dir = tmpdir.mkdir('external')
    file_1 = test_dir.join('file_1.yaml')
    file_2 = test_dir.join('file_2.yaml')

    data_1 = {'key_1': 'value_1',
              'key_2': {'$ref': str(file_2)}}
    data_2 = {'key_3': 'value_3',
              'key_4': {'$ref': '#/key_3'}}

    file_1.write(yaml.dump(data_1))
    file_2.write(yaml.dump(data_2))

    resolved = swagger.load(str(file_1), {})

    expected = {'key_1': 'value_1',
                'key_2': {'key_3': 'value_3',
                          'key_4': 'value_3'}}

    assert resolved == expected


def test_load_relative_ref(tmpdir):
    test_dir = tmpdir.mkdir('bundle')
    file_1 = test_dir.join('file_1.yaml')
    file_2 = test_dir.join('file_2.yaml')

    data_1 = {'key_1': {'$ref': 'file_2.yaml'}}
    data_2 = {'key_2': 'value_2'}

    file_1.write(yaml.dump(data_1))
    file_2.write(yaml.dump(data_2))

    expected = {'key_1': {'key_2': 'value_2'}}
    actual = swagger.load(str(file_1), {})

    assert actual == expected
