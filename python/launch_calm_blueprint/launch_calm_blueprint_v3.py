#!/usr/bin/env python

'''
Python >=3.7 script to launch a Nutanix Calm blueprint
via the v3 REST API
'''

import sys
from api_client import ApiClient
from exceptions import DetailsMissingException
from environment_options import EnvironmentOptions


def show_intro():
    '''
    function to simply show an extended help intro when the script
    is run - definitely not required but useful for development
    scripts like this one
    '''
    print(
        f'''
{sys.argv[0]}:

Connect to a Nutanix Prism Central instance and attempt to launch
a Nutanix Calm blueprint.

Intended to provide a way to launch a Nutanix Calm blueprint as
part of an external or third-party workflow/script.

This script is GPL and there is *NO WARRANTY* provided with this script ...
AT ALL.  You can use and modify this script as you wish, but please make
sure the changes are appropriate for the intended environment.
'''
    )


def main():
    '''
    main entry point into the 'app'
    every function needs a Docstring in order to follow best
    practices
    '''

    # show_intro()

    '''
    collect the environment options from the command line
    this is packaged and managed via the EnvironmentOptions
    module in the environment_options directory
    '''
    environment_options = EnvironmentOptions()
    environment_options.get_options()

    if environment_options.debug:
        print(f'{environment_options}\n')

    '''
    check to make sure all required options have been specified
    if the username and password have not been provided on the
    command line, we'll prompt for them here
    '''
    if not environment_options.cluster_ip:
        raise DetailsMissingException('Cluster IP is required.')
    elif not environment_options.username:
        raise DetailsMissingException('Username is required.')
    elif not environment_options.password:
        raise DetailsMissingException('Password is required.')
    else:
        if environment_options.debug:
            print('All parameters OK.\n')

        if environment_options.debug:
            print('Creating instance of ApiClient class ...')
        client_blueprint = ApiClient(
            environment_options.cluster_ip,
            (f'blueprints/{environment_options.blueprint_uuid}'
             '/runtime_editables'),
            '',
            environment_options.username,
            environment_options.password,
            environment_options.read_timeout
        )
        if environment_options.debug:
            print(f'Client info: {client_blueprint}\n')
        if environment_options.debug:
            print('Requesting blueprint details ...\n')
        results_blueprint = client_blueprint.send_request()

        '''
        check to see if there are app profile references
        in the JSON response
        this is ONLY required if --app_profile was not
        specified as a command-line parameter

        if no app_profile has been specified, we can get it
        from the API request we just made
        if no app_profile has been specified but it is also
        missing from the JSON response, it likely indicates
        a failed request or a request that wasn't a call to
        a blueprint's runtime_editables api

        ***Important note:
        This demo script only looks for
        an app profile named 'Default'; if no matching app
        profile reference exists in your environment, please
        edit the 'Default' name below, and/or manually construct
        the value of app_profile_reference

        '''

        if environment_options.app_profile_reference == '':
            if environment_options.debug:
                print('No app profile specified; grabbing it from '
                      'the blueprint spec ...')
            if 'resources' in results_blueprint:
                if len(results_blueprint['resources']) > 0:
                    if 'app_profile_reference' in results_blueprint['resources'][0]:
                        if len(results_blueprint['resources'][0]) > 0:
                            if environment_options.debug:
                                print('App profile reference found.')
                            for reference in results_blueprint['resources']:
                                if (reference['app_profile_reference']['name']
                                        == 'Default'):
                                    environment_options.app_profile_reference = (reference['app_profile_reference']['uuid'])
                                    if environment_options.debug:
                                        print('Default app profile reference UUID extracted.')
                        else:
                            print('no app profile references found; exiting.')
                            sys.exit()
                    else:
                        print('no app profile references found; exiting.')
                        sys.exit()
                else:
                    print('no app profile references found; exiting.')
                    sys.exit()
            else:
                print('no app profile references found; exiting.')
                sys.exit()
        else:
            if environment_options.debug:
                print('App profile already specified; using command line parameter ...')
            pass

        '''
        at this point we do have our app profile reference
        we can continue with the next part of the script, i.e.
        creating the payload/request body that will be sent
        with the actual launch request
        '''
        if environment_options.debug:
            print('Building blueprint launch payload ...\n')
        payload = ('{ '
                   '"spec":{ '
                   f'"app_name":"{environment_options.app_name}", '
                   f'"app_description":"{environment_options.app_desc}", '
                   '"app_profile_reference":{ '
                   '"kind":"app_profile", '
                   '"name":"Default", '
                   f'"uuid":"{environment_options.app_profile_reference}" '
                   '} '
                   '} '
                   '}')

        if environment_options.debug:
            print(f'Payload: \n{payload}\n')

        if environment_options.debug:
            print('Creating instance of ApiClient class ...')
        client_launch = ApiClient(
            environment_options.cluster_ip,
            (f'blueprints/{environment_options.blueprint_uuid}'
                '/simple_launch'),
            payload,
            environment_options.username,
            environment_options.password,
            environment_options.read_timeout,
            method='post'
        )

        if environment_options.debug:
            print(f'Client info: {client_launch}\n')
        if environment_options.debug:
            print('Sending request ...\n')
        results_launch = client_launch.send_request()
        if environment_options.debug:
            print(f'Results: \n{results_launch}')


if __name__ == '__main__':
    main()
