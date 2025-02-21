"""
Simple module to allow function re-use across Nutanix
v4 SDK code samples

Requires Prism Central 2024.3 or later, AOS 7.0 or later
"""

import urllib3
from dataclasses import dataclass

from .utils import Config

class ApiClient:
    """
    class to Nutanix v4 API and SDK connections
    """

    def __init__(self, config: Config, sdk_module: str = ""):
        """
        class constructor
        """

        # disable insecure connection warnings
        # consider the security implications before doing this in production
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # import the specified SDK module
        self.imported_module = __import__(sdk_module)

        # setup the connection information
        self.configuration = self.imported_module.Configuration()
        self.configuration.host = config.pc_ip
        self.configuration.port = "9440"
        self.configuration.username = config.pc_username
        self.configuration.password = config.pc_password
        self.configuration.verify_ssl = False

        # setup the API client instance
        self.api_client = self.imported_module.ApiClient(configuration=self.configuration)
