QUERY_STRING_DELIMITERS = {
    'spaceDelimited': ' ',
    'pipeDelimited': '|',
    'simple': ',',
    'form': ','
}


def resolve_query_duplicates(values, param_defn):
    """ Resolve cases where query parameters are provided multiple times.
        The default behavior is to use the last-defined value.
        For example, if the query string is '?a=1,2,3&a=4,5,6' the value of
        `a` would be "4,5,6".
        However, if 'explode' is true, or the 'collectionFormat' is 'multi'
        (swagger2) then the duplicate values are concatenated together and
        `a` would be "1,2,3,4,5,6".
    """
    try:
        # oas3
        style = param_defn['style']
        delimiter = QUERY_STRING_DELIMITERS.get(style, ',')
        is_form = (style == 'form')
        explode = param_defn.get('explode', is_form)
        if explode:
            return delimiter.join(values)
    except KeyError:
        # swagger2
        if param_defn.get('collectionFormat') == 'multi':
            return ','.join(values)
    # default to last defined value
    return values[-1]


def query_split(value, param_defn):
    """ Split query parameters based on the parameter definition.
    """
    try:
        # oas3
        style = param_defn['style']
        delimiter = QUERY_STRING_DELIMITERS.get(style, ',')
        return value.split(delimiter)
    except KeyError:
        # swagger2
        if param_defn.get('collectionFormat') == 'pipes':
            return value.split('|')
    # default: csv
    return value.split(',')
