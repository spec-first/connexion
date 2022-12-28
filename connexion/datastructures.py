from fnmatch import fnmatch

# special marker object to return empty content for any status code
# e.g. in app method do "return NoContent, 201"
NoContent = object()


class MediaTypeDict(dict):
    """
    A dictionary where keys can be either media types or media type ranges. When fetching a
    value from the dictionary, the provided key is checked against the ranges. The most specific
    key is chosen as prescribed by the OpenAPI spec, with `type/*` being preferred above
    `*/subtype`.
    """

    def __getitem__(self, item):
        # Sort keys in order of specificity
        for key in sorted(self, key=lambda k: ("*" not in k, k), reverse=True):
            if fnmatch(item, key):
                return super().__getitem__(key)
        raise super().__getitem__(item)

    def get(self, item, default=None):
        try:
            return self[item]
        except KeyError:
            return default

    def __contains__(self, item):
        try:
            self[item]
        except KeyError:
            return False
        else:
            return True
