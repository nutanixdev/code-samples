#!/usr/bin/env python

'''
Python >=3.7 script to generate a human-readable HTML
report on a specified Nutanix Prism Central instance
'''

import os
import os.path
import sys
import socket
import getpass
import argparse
from time import localtime, strftime
from string import Template

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


class DetailsMissingException(Exception):
    '''
    basic custom exception for when things "don't work"
    this is something that has been added simply to make extending
    the script much easier later
    '''
    pass


class EnvironmentOptions():
    '''
    this class is provided as an easy way to package the settings
    the script will use
    this isn't strictly necessary but does clean things up and removes
    the need for a bunch of individual global variables
    '''

    def __init__(self):
        self.cluster_ip = ""
        self.username = ""
        self.password = ""
        self.debug = False
        self.read_timeout = 10
        self.entity_response_length = 20
        # these are the supported entities for this environment
        # self.supported_entities = ['vm', 'subnet', 'cluster', 'project',
        #                            'network_security_rule', 'image',
        #                            'host', 'blueprint', 'app']
        self.supported_entities = ['vm', 'subnet', 'cluster', 'project',
                                   'image',
                                   'host', 'blueprint', 'app']

    def __repr__(self):
        '''
        decent __repr__ for debuggability
        this is something recommended by Raymond Hettinger
        '''
        return (f'{self.__class__.__name__}(cluster_ip={self.cluster_ip},'
                f'username={self.username},password=<hidden>,'
                f'entity_response_length={self.entity_response_length},'
                f'read_timeout={self.read_timeout},debug={self.debug})')

    def get_options(self):
        '''
        method to make sure our environment options class holds the
        settings provided by the user
        '''

        parser = argparse.ArgumentParser()
        '''
        pc_ip is the only mandatory command-line parameter for this script
        username and password have been left as optional so that we have
        the opportunity to prompt for them later - this is better for
        security and avoids the need to hard-code anything
        '''
        parser.add_argument(
            'pc_ip',
            help='Prism Central IP address'
        )
        parser.add_argument(
            '-u',
            '--username',
            help='Prism Central username'
        )
        parser.add_argument(
            '-p',
            '--password',
            help='Prism Central password'
        )
        parser.add_argument(
            '-d',
            '--debug',
            help='Enable/disable debug mode'
        )

        args = parser.parse_args()

        '''
        do some checking to see which parameters we still need to prompt for
        conditional statements make sense here because a) we're doing a few of
        them and b) they're more 'Pythonic'
        '''
        self.username = (args.username if args.username else
                         input('Please enter your Prism Central username: '))
        self.password = args.password if args.password else getpass.getpass()

        '''
        conditional statement isn't required for the Prism Central IP since
        it is a required parameter managed by argparse
        '''
        self.cluster_ip = args.pc_ip

        self.debug = True if args.debug == 'enable' else False


class ApiClient():
    '''
    the most important class in our script
    here we carry out the actual API request and process the
    responses, as well as any errors that returned from the
    response
    '''

    def __init__(self, cluster_ip, request, body,
                 username, password, timeout=10):
        self.cluster_ip = cluster_ip
        self.username = username
        self.password = password
        self.base_url = f'https://{self.cluster_ip}:9440/api/nutanix/v3'
        self.entity_type = request
        self.request_url = f'{self.base_url}/{request}'
        self.timeout = timeout
        self.body = body

    def __repr__(self):
        '''
        decent __repr__ for debuggability
        this is something recommended by Raymond Hettinger
        '''
        return (f'{self.__class__.__name__}(cluster_ip={self.cluster_ip},'
                f'username={self.username},password=<hidden>,'
                f'base_url={self.base_url},entity_type={self.entity_type},'
                f'request_url={self.request_url},'
                f'body (payload)={self.body})')

    def send_request(self):
        '''
        send the API request based on the parameters we
        have already collected
        '''

        headers = {'Content-Type': 'application/json; charset=utf-8'}
        try:
            api_request = requests.post(
                self.request_url,
                data=self.body,
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
        else:
            if api_request.status_code == 401:
                print('An authentication error occurred while connecting to '
                      f'{self.cluster_ip}. Please check your credentials, '
                      'then try again.')
                sys.exit()
            if api_request.status_code >= 401:
                print('An HTTP client error has occurred ('
                      f'{api_request.status_code})')
                sys.exit()
            else:
                print("Connected and authenticated successfully.")
        return api_request.json()


HTML_ROWS = {}
ENTITY_TOTALS = {}


def generate_template(json_results):
    '''
    generate the HTML
    '''
    day = strftime('%d-%b-%Y', localtime())
    time = strftime('%H%M%S', localtime())
    now = f'{day}_{time}'
    html_filename = f'{now}_prism_central.html'

    '''
    the next block parses some of the Prism Central info that
    currently exists as individual lists
    '''

    '''
    these are entity types the script currently supports
    if new features or entity types become available in future,
    it should be a relatively simple task to update this list
    to support those entities
    '''
    # supported_entities = [
    #     'vm', 'subnet', 'cluster', 'project', 'network_security_rule',
    #     'image', 'host', 'blueprint', 'app']
    supported_entities = [
        'vm', 'subnet', 'cluster', 'project',
        'image', 'host', 'blueprint', 'app']
    for row_label in supported_entities:
        HTML_ROWS[row_label] = ''
        ENTITY_TOTALS[row_label] = 0

    print('\n')

    for json_result in json_results:
        # collect info that is common to all entity types
        for entity in json_result:
            if entity in supported_entities:
                ENTITY_TOTALS[f'{entity}'] = (json_result[1]["metadata"]
                                              ["total_matches"])
                print(f'Count of entity type {entity}: '
                      f'{json_result[1]["metadata"]["total_matches"]}')

        '''
        note that the next long section seems a little repetitive, but the
        string formatting for each entity is different enough to do it this way
        if each entity's info 'block' was the same, we could setup an iterator
        or use common formatting, but then the generated HTML wouldn't be very
        useful
        '''

        ##########
        #   VM   #
        ##########
        if json_result[0] == 'vm':
            print("Processing VMs ...")
            try:
                for vm in json_result[1]['entities']:
                    entity_name = vm["spec"]["cluster_reference"]["name"]
                    description = (vm['spec']['description']
                                   if 'description' in vm['spec']
                                   else 'None provided')
                    HTML_ROWS['vm'] += ('<tr><td>'
                                        f'{entity_name}'
                                        f':{vm["spec"]["name"]}</td><td>'
                                        f'{description}'
                                        '</td></tr>')
            except KeyError:
                HTML_ROWS['vm'] += ('<tr><td colspan="2">'
                                    'Expected VM data is missing or malformed.'
                                    'Please check the JSON response.'
                                    '</td></tr>')

        ##########
        # SUBNET #
        ##########
        elif json_result[0] == 'subnet':
            print("Processing subnets ...")
            try:
                for subnet in json_result[1]['entities']:
                    entity_name = subnet["spec"]["cluster_reference"]["name"]
                    HTML_ROWS["subnet"] += ('<tr><td>'
                                            f'{subnet["spec"]["name"]}</td>'
                                            f'<td>{entity_name}'
                                            '</td></tr>')
            except KeyError:
                HTML_ROWS['vm'] += ('<tr><td colspan="2">'
                                    'Expected subnet data is missing or'
                                    'malformed.  Please check the JSON '
                                    'response.</td></tr>')
        ###########
        # PROJECT #
        ###########
        elif json_result[0] == 'project':
            print("Processing projects ...")
            vm_total = 0
            cpu_total = 0
            storage_total = 0
            memory_total = 0
            HTML_ROWS['project'] = ''
            try:
                for project in json_result[1]['entities']:
                    entity_name = project['spec']['name']
                    HTML_ROWS['project'] += ('<tr><td>'
                                             f'{entity_name}</td>')

                    '''
                    check to see if the project is consuming any resources
                    an empty project will show 0 for CPU/RAM/storage/VM count
                    '''
                    if ('resources' in
                            project['status']['resources']['resource_domain']):
                        if (project['status']['resources']['resource_domain']
                                ['resources']):
                            for resource in project['status']['resources'][
                                    'resource_domain']['resources']:
                                if resource['resource_type'] == 'VMS':
                                    vm_total = resource['value']
                                elif resource['resource_type'] == 'VPUS':
                                    cpu_total = resource['value']
                                elif resource['resource_type'] == 'STORAGE':
                                    storage_total = (resource['value']
                                                     / 1024 / 1024 / 1024)
                                elif resource['resource_type'] == 'MEMORY':
                                    memory_total = (resource['value']
                                                    / 1024 / 1024 / 1024)
                            HTML_ROWS['project'] += (f'<td>{vm_total}</td><td>'
                                                     f'{cpu_total}</td><td>'
                                                     f'{storage_total}</td>'
                                                     f'<td>{memory_total}'
                                                     '</td>')
                        else:
                            HTML_ROWS['project'] += ('<td>0</td><td>0</td><td>'
                                                     '0</td><td>0</td>')
                    else:
                        HTML_ROWS['project'] += ('<td>0</td><td>0</td>'
                                                 '<td>0</td><td>0</td>')

                    HTML_ROWS['project'] += '</tr>'
            except KeyError:
                HTML_ROWS['vm'] += ('<tr><td colspan="2">'
                                    'Expected project data is missing or'
                                    'malformed.  Please check the JSON '
                                    'response.</td></tr>')

        #########################
        # NETWORK_SECURITY_RULE #
        # NO LONGER SUPPORTED   #
        #########################
        # elif json_result[0] == 'network_security_rule':
        #     print("Processing network security rules ...")
        #     for network_security_rule in json_result[1]['entities']:
        #         entity_name = network_security_rule['spec']['name']
        #         HTML_ROWS['network_security_rule'] += (f'<tr><td>{entity_name}'
        #                                                '</td></tr>')

        #########
        # IMAGE #
        #########
        elif json_result[0] == 'image':
            print("Processing images ...")
            try:
                for image in json_result[1]['entities']:
                    entity_name = image["status"]["name"]
                    image_type = image["status"]["resources"]["image_type"]
                    HTML_ROWS['image'] += (f'<tr><td>{entity_name}</td><td>'
                                           f'{image_type}'
                                           '</td></tr>')
            except KeyError:
                HTML_ROWS['vm'] += ('<tr><td colspan="2">'
                                    'Expected subnet data is missing or'
                                    'malformed.  Please check the JSON '
                                    'response.</td></tr>')
        ########
        # HOST #
        ########
        elif json_result[0] == 'host':
            print("Processing hosts ...")
            try:
                for host in json_result[1]['entities']:
                    if 'name' in host['status']:
                        host_serial = (host["status"]["resources"]
                                       ["serial_number"])
                        host_ip = (host["status"]["resources"]
                                   ["hypervisor"]["ip"])
                        cvm_ip = (host["status"]["resources"]
                                  ["controller_vm"]["ip"])
                        num_vms = (host["status"]["resources"]
                                   ["hypervisor"]["num_vms"])
                        HTML_ROWS['host'] += ('<tr><td>'
                                              f'{host["status"]["name"]}'
                                              '</td><td>'
                                              f'{host_serial}'
                                              '</td><td>'
                                              f'{host_ip}'
                                              '</td><td>'
                                              f'{cvm_ip}'
                                              '</td><td>'
                                              f'{num_vms}'
                                              '</td></tr>')
                    else:
                        host_serial = (host["status"]
                                       ["resources"]["serial_number"])
                        cvm_ip = (host["status"]["resources"]
                                  ["controller_vm"]["ip"])
                        HTML_ROWS['host'] += ('<tr><td>N/A</td><td>'
                                              f'{host_serial}'
                                              '</td><td>N/A</td>'
                                              f'<td>{cvm_ip}</td>'
                                              '<td>N/A</td></tr>')
            except KeyError:
                HTML_ROWS['vm'] += ('<tr><td colspan="2">'
                                    'Expected host data is missing or'
                                    'malformed.  Please check the JSON '
                                    'response.</td></tr>')
        ###########
        # CLUSTER #
        ###########
        elif json_result[0] == 'cluster':
            print("Processing clusters ...")
            for cluster in json_result[1]['entities']:
                try:
                    cluster_ip = ((cluster['spec']['resources']['network']
                                   ['external_ip'])
                                  if ('external_ip' in
                                      cluster['spec']['resources']['network'])
                                  else 'N/A')

                    html_prefix = ('AOS' if (cluster["status"]["resources"]
                                             ["config"]["service_list"][0]
                                             == 'AOS')
                                   else 'Prism Central')

                    cluster_version = (cluster['status']['resources']
                                       ['config']['build']['version'])

                    is_ce = ('Yes' if ('-ce-' in (cluster['status']
                                                  ['resources']['config']
                                                  ['build']['full_version']))
                             else 'No')

                    HTML_ROWS["cluster"] += (f'<tr><td>{html_prefix}</td><td>'
                                             f'{cluster["spec"]["name"]}</td>'
                                             f'<td>{cluster_ip}</td><td>'
                                             f'{cluster_version}'
                                             f'</td><td>{is_ce}</td>')
                except KeyError:
                    HTML_ROWS['vm'] += ('<tr><td colspan="2">'
                                        'Expected cluster data is missing or'
                                        'malformed.  Please check the JSON '
                                        'response.</td></tr>')

        #############
        # BLUEPRINT #
        #############
        elif json_result[0] == 'blueprint':
            print("Processing blueprints ...")
            try:
                for blueprint in json_result[1]['entities']:
                    entity_name = blueprint["status"]["name"]
                    if not bool(blueprint['status']['deleted']):
                        status = blueprint["status"]["state"]

                        bp_project = ((blueprint["metadata"]
                                       ["project_reference"]["name"])
                                      if 'project_reference' in (
                                        blueprint['metadata']
                                      ) else 'N/A')

                        HTML_ROWS["blueprint"] += (f'<tr><td>{entity_name}'
                                                   f'</td><td>{bp_project}'
                                                   f'</td><td>{status}</td>'
                                                   '</tr>')
            except KeyError:
                HTML_ROWS['vm'] += ('<tr><td colspan="2">'
                                    'Expected blueprint data is missing or'
                                    'malformed.  Please check the JSON '
                                    'response.</td></tr>')
        #######
        # APP #
        #######
        elif json_result[0] == 'app':
            print("Processing apps ...")
            for app in json_result[1]['entities']:
                try:
                    entity_name = app['status']['name']
                    app_project = app['metadata']['project_reference']['name']
                    app_state = app['status']['state'].upper()
                    if app["status"]["state"].upper() != 'DELETED':
                        HTML_ROWS["app"] += (f'<tr><td>{entity_name}</td><td>'
                                             f'{app_project}</td><td>'
                                             f'{app_state}'
                                             '</td></tr>')
                except KeyError:
                    HTML_ROWS['vm'] += ('<tr><td colspan="2">'
                                        'Expected subnet data is missing or'
                                        'malformed.  Please check the JSON '
                                        'response.</td></tr>')

    print('\n')

    '''
    specify the HTML page template
    '''

    current_path = os.path.dirname(os.path.realpath(__file__))
    
    if os.path.isfile(f'{current_path}/templates/nutanixv3.html'):
        template_name = f'{current_path}/templates/nutanixv3.html'
    else:
        print('Template not found')
        sys.exit()

    # load the HTML content from the template
    with open(template_name, 'r') as data_file:
        source_html = Template(data_file.read())

    # substitute the template variables for actual cluster data
    template = source_html.safe_substitute(
        day=day,
        now=time,
        username=getpass.getuser(),
        clusters=str(HTML_ROWS['cluster']),
        vms=str(HTML_ROWS['vm']),
        subnets=str(HTML_ROWS['subnet']),
        projects=str(HTML_ROWS['project']),
        # network_security_rules=str(HTML_ROWS['network_security_rule']),
        images=str(HTML_ROWS['image']),
        hosts=str(HTML_ROWS['host']),
        blueprints=str(HTML_ROWS['blueprint']),
        apps=str(HTML_ROWS['app']),
        # totals
        cluster_total=str(ENTITY_TOTALS['cluster']),
        vm_total=str(ENTITY_TOTALS['vm']),
        subnet_total=str(ENTITY_TOTALS['subnet']),
        project_total=str(ENTITY_TOTALS['project']),
        # network_security_rule_total=str(
        #     ENTITY_TOTALS['network_security_rule']),
        image_total=str(ENTITY_TOTALS['image']),
        host_total=str(ENTITY_TOTALS['host']),
        blueprint_total=str(ENTITY_TOTALS['blueprint']),
        app_total=str(ENTITY_TOTALS['app']),
        computer_name=socket.gethostname(),
    )

    # generate the final HTML file
    export_html_report(template, html_filename)

    print(f'Finished generating HTML file: {html_filename}')
    print('\n')


def export_html_report(source_html, output_filename):
    '''
    utility function for exporting our HTML report
    this could be done "in-line" but has been made a function
    in case it needs to be repeated later
    '''

    # open output file for writing and export the HTML
    with open(output_filename, 'w') as f:
        f.write(source_html)


def show_intro():
    '''
    function to simply show an extended help intro when the script
    is run - definitely not required but useful for development
    scripts like this one
    '''
    print(
        f'''
{sys.argv[0]}:

Connect to a Nutanix Prism Central instance, grab some high-level details then
generate an HTML file from it

Intended to generate a very high-level and *unofficial* as-built document for
an existing Prism Central instance.

This script is GPL and there is *NO WARRANTY* provided with this script ...
AT ALL.  You can use and modify this script as you wish, but please make
sure the changes are appropriate for the intended environment.

Formal documentation should always be generated using best-practice methods
that suit your environment.
'''
    )


def main():
    '''
    main entry point into the 'app'
    every function needs a Docstring in order to follow best
    practices
    '''

    current_path = os.path.dirname(os.path.realpath(__file__))

    '''
    make sure our template exists
    this html template dicates how the generated HTML report will look
    '''
    if os.path.isfile(f'{current_path}/templates/nutanixv3.html'):
        show_intro()

        environment_options = EnvironmentOptions()
        environment_options.get_options()

        if environment_options.debug:
            print(f'{environment_options}\n')

        '''
        disable insecure connection warnings
        please be advised and aware of the implications of doing this
        in a production environment!
        '''
        if environment_options.debug:
            print('Disabling urllib3 insecure request warnings ...\n')
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # make sure all required info has been provided
        if not environment_options.cluster_ip:
            raise DetailsMissingException('Cluster IP is required.')
        elif not environment_options.username:
            raise DetailsMissingException('Username is required.')
        elif not environment_options.password:
            raise DetailsMissingException('Password is required.')
        else:
            if environment_options.debug:
                print('All parameters OK.\n')

            '''
            'length' in Nutanix v3 API requests dictates how many entities
            will be returned in each request
            '''
            length = environment_options.entity_response_length
            if environment_options.debug:
                print(f'{length} entities will be returned for each request.')

            json_results = []
            endpoints = []

            for entity in environment_options.supported_entities:
                entity_plural = f'{entity}s'
                endpoints.append({'name': f'{entity}',
                                  'name_plural': f'{entity_plural}',
                                  'length': length})

            if environment_options.debug:
                print('Iterating over all supported endpoints ...\n')

            for endpoint in endpoints:
                print(f"Processing {endpoint['name_plural']} ...")
                client = ApiClient(
                    environment_options.cluster_ip,
                    f'{endpoint["name_plural"]}/list',
                    (f'{{ "kind": "{endpoint["""name"""]}",'
                     f'"length": {endpoint["""length"""]}}}'),
                    environment_options.username,
                    environment_options.password,
                    environment_options.read_timeout
                )
                if environment_options.debug:
                    print(f'Client info: {client}\n')
                    print(f'Requesting "{client.entity_type}" ...\n')
                results = client.send_request()
                json_results.append([endpoint['name'], results])

            if environment_options.debug:
                print('Generating HTML template ...\n')
            generate_template(json_results)

    else:
        print('\nNo HTML templates were found in the "templates" directory.'
              'You will need one of these to continue.\n')


if __name__ == '__main__':
    main()
