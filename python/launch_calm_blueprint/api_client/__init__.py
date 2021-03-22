#!/usr/bin/env python

'''
ApiClient to manage the GET/POST of API requests
Specifically for use with the Nutanix v3 REST APIs
'''

import sys

try:
    import urllib3
    import requests
    from requests.auth import HTTPBasicAuth
except ModuleNotFoundError as error:
    # Output expected ImportErrors.
    print(f'''
    {error.__class__.__name__} exception has been caught.
    This typically indicates a required module is not installed.
    Please ensure you are running this script within a
    virtual development environment and that you have run the
    setup script as per the readme. Detailed exception info follows:

    {error}
    ''')
    sys.exit()


class ApiClient():
    '''
    the most important class in our script
    here we carry out the actual API request and process the
    responses, as well as any errors that returned from the
    response
    '''

    def __init__(self, cluster_ip, request, body,
                 username, password, timeout=10, method='get'):
        self.cluster_ip = cluster_ip
        self.username = username
        self.password = password
        self.base_url = f'https://{self.cluster_ip}:9440/api/nutanix/v3'
        self.entity_type = request
        self.request_url = f'{self.base_url}/{request}'
        self.timeout = timeout
        self.body = body
        self.method = method
        '''
        disable insecure connection warnings
        please be advised and aware of the implications of doing this
        in a production environment!
        '''
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    def __repr__(self):
        '''
        decent __repr__ for debuggability
        this is something recommended by Raymond Hettinger
        '''
        return (f'{self.__class__.__name__}(cluster_ip={self.cluster_ip},'
                f'username={self.username},password=<hidden>,'
                f'base_url={self.base_url},entity_type={self.entity_type},'
                f'request_url={self.request_url},'
                f'body (payload)={self.body},'
                f'method={self.method})')

    def send_request(self):
        '''
        send the API request based on the parameters we
        have already collected
        '''

        headers = {'Content-Type': 'application/json; charset=utf-8'}
        try:
            if self.method == 'post':
                api_request = requests.post(
                    self.request_url,
                    data=self.body,
                    verify=False,
                    headers=headers,
                    auth=HTTPBasicAuth(self.username, self.password),
                    timeout=self.timeout,
                )
            else:
                api_request = requests.get(
                    self.request_url,
                    verify=False,
                    headers=headers,
                    auth=HTTPBasicAuth(self.username, self.password),
                    timeout=self.timeout,
                )
        except requests.ConnectTimeout:
            print('Connection timed out while connecting to '
                  f'{self.cluster_ip}. Please check your connection, '
                  'then try again.')
            sys.exit()
        except requests.ConnectionError:
            print('An error occurred while connecting to '
                  f'{self.cluster_ip}. Please check your connection, '
                  'then try again.')
            sys.exit()
        except requests.HTTPError:
            print('An HTTP error occurred while connecting to '
                  f'{self.cluster_ip}. Please check your connection, '
                  'then try again.')
            sys.exit()
        except Exception as error:
            '''
            catching generic Exception will throw warnings if you
            are running the script through something like flake8
            or pylint
            that's fine for what we're doing here, though :)
            '''
            print(f'An unhandled exception has occurred: {error}')
            print(f'Exception: {error.__class__.__name__}')
            print('Exiting ...')
            sys.exit()

        if api_request.status_code >= 500:
            print('An HTTP server error has occurred ('
                  f'{api_request.status_code})')
        elif api_request.status_code == 404:
            print('An HTTP server error has occurred ('
                  f'{api_request.status_code})')
            print('404 typically indicates requesting an API or request '
                  'parameter that does not exist.  Examples of this could '
                  'be launching a blueprint with an app profile that does '
                  'not exist or a spelling error in the API name.')
        else:
            if api_request.status_code == 401:
                print('An authentication error occurred while connecting to '
                      f'{self.cluster_ip}. Please check your credentials, '
                      'then try again.')
                sys.exit()
            if api_request.status_code >= 401:
                print('An HTTP client error has occurred ('
                      f'{api_request.status_code})')
                if api_request.status_code == 422:
                    if 'message_list' in api_request.json():
                        for message in api_request.json()['message_list']:
                            print(f'Details: {message["details"]}')
                            print(f'Message: {message["message"]}')
                            print(f'Reason: {message["reason"]}')
                sys.exit()
            else:
                print("Connected and authenticated successfully.")

        return api_request.json()
