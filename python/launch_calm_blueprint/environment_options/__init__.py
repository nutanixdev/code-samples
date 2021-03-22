#!/usr/bin/env python

'''
EnvironmentOptions class to work with the launch_calm_blueprint.py code sample
'''

import argparse
import getpass


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
        # this the UUID for the blueprint we'll launch
        self.blueprint_uuid = ''
        self.app_profile_reference = ''

    def __repr__(self):
        '''
        decent __repr__ for debuggability
        this is something recommended by Raymond Hettinger
        '''
        return (f'{self.__class__.__name__}(cluster_ip={self.cluster_ip},'
                f'username={self.username},password=<hidden>,'
                f'blueprint_uuid={self.blueprint_uuid},'
                f'app_name={self.app_name},app_desc={self.app_desc},'
                f'app_profile_reference={self.app_profile_reference},'
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
            'blueprint_uuid',
            help='UUID of the blueprint to be launched'
        )
        parser.add_argument(
            'app_name',
            help='The name of the application to be launched'
        )
        parser.add_argument(
            'app_desc',
            help='Description for the new application'
        )
        parser.add_argument(
            '-a',
            '--app_profile',
            help='App profile reference UUID'
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
        self.blueprint_uuid = args.blueprint_uuid
        self.app_name = args.app_name
        self.app_desc = args.app_desc
        self.app_profile_reference = (args.app_profile if args.app_profile
                                      else '')

        self.debug = True if args.debug == 'enable' else False
