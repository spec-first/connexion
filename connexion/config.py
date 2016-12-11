from derpconf.config import Config


BASE_API_SECTION = 'Basic API configurations'

Config.define('SPECIFICATION_FILE', None,
              'OpenAPI specification file path.',
              BASE_API_SECTION)

Config.define('SPECIFICATION_DIR', '',
              'Directory to use as bases to look for OpenAPI specification files.',
              BASE_API_SECTION)


SERVER_CONFIG_SECTION = 'Application Server configurations'

Config.define('HOST', '0.0.0.0',
              'The host interface to bind on when server is running.',
              SERVER_CONFIG_SECTION)

Config.define('PORT', 5000,
              'The port to listen to when server is running.',
              SERVER_CONFIG_SECTION)

Config.define('DEBUG', False,
              'Whether to execute the application in debug mode.',
              SERVER_CONFIG_SECTION)


API_CONFIG_SECTION = 'API configurations'

Config.define('AUTHENTICATE_NOT_FOUND_URLS', False,
              'Whether to authenticate paths not defined in the API specification.',
              API_CONFIG_SECTION)

Config.define('VALIDATE_RESPONSES', False,
              'Whether to validate the operation handler responses against '
              'the API specification or not.',
              API_CONFIG_SECTION)

Config.define('STRICT_PARAMETERS_VALIDATION', False,
              'Whether to allow or not additional parameters in querystring '
              'and formData than the defineds in the API specification.',
              API_CONFIG_SECTION)

Config.define('MAKE_SPEC_AVAILABLE', True,
              'Whether to make available the OpenAPI sepecification under '
              'CONSOLE_UI_PATH/swagger.json path.',
              API_CONFIG_SECTION)

CONSOLE_UI_SECTION = 'API Console UI configurations'

Config.define('CONSOLE_UI_AVAILABLE', True,
              'Whether to make the OpenAPI console available under '
              'CONSOLE_UI_PATH config path. Notice that this '
              'overrides the MAKE_SPEC_AVAILABLE configuration since '
              'the specification is required to be available to show '
              'the console UI.',
              CONSOLE_UI_SECTION)

Config.define('CONSOLE_UI_PATH', '/ui',
              'Path to mount the OpenAPI console.',
              CONSOLE_UI_SECTION)


if __name__ == '__main__':
    from textwrap import fill
    config = Config()
    column_width = 41
    header = '=' * column_width
    header = '{} {}'.format(header, header)
    newline_spacing = '\n' + (' ' * (column_width + 1))
    print(header)
    for group in config.class_groups:
        keys = config.class_group_items[group]
        for key in keys:
            desc = '{} Defaults to: {}'.format(
                config.class_descriptions[key], config.class_defaults[key])
            print('``{}``{}{}'.format(key, ' ' * (column_width - len(key) - 3),
                                      fill(desc, width=column_width).replace('\n', newline_spacing)))
    print(header)
