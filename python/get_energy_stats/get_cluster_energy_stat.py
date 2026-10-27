"""
Usage Help


usage: get_cluster_energy_stats.py [-h] --pc_ip PC_IP --username USERNAME --password PASSWORD [--cluster_uuid CLUSTER_UUID | --host_uuid HOST_UUID | --hc-granularity HC_GRANULARITY] [--start_time START_TIME]
                                  [--end_time END_TIME] [--time_frame TIME_FRAME] [--down_sample_interval DOWN_SAMPLE_INTERVAL]


Get power stats(in Watts) from the Prism REST API v2.0.


options:
 -h, --help            show this help message and exit
 --pc_ip PC_IP         Prism Central IP address.
 --username USERNAME   Prism Central Username
 --password PASSWORD   Prism Central Password
 --cluster_uuid CLUSTER_UUID
                       Registered(to pc_ip) cluster's UUID for which power consumption stats are to be retrieved.
 --host_uuid HOST_UUID
                       Registered(to pc_ip) Host's UUID for which power consumption stats are to be retrieved.
 --hc-granularity HC_GRANULARITY
                       Granularity for the power stats. Possible values : CLUSTER|HOST
 --down_sample_interval DOWN_SAMPLE_INTERVAL
                       Down sample interval in seconds.


 --start_time START_TIME
                       Start time for the power stats in ISO-8601 compliant format e.g. "YYYY-MM-DDTHH:MM:SSZ".
 --end_time END_TIME   End time for the power stats in ISO-8601 compliant  format e.g. "YYYY-MM-DDTHH:MM:SSZ".
 --time_frame TIME_FRAME
                       Time frame for the power stats. Possible values : LASTHOUR|LASTDAY|LASTWEEK|LASTMONTH


Optional Args and Expected Results


None                                    : Gives Energy consumption stats for all the clusters registered to the Prism Central for the last hour.
--start_time --end_time                 : Gives Energy consumption stats for all the clusters registered to the Prism Central between given start and end time.
--time_frame                            : Gives Energy consumption stats for all the clusters registered to the Prism Central for the given time frame.
--cluster_uuid                          : Gives Energy consumption stats for the cluster with the given UUID for the last hour.
--cluster_uuid --start_time --end_time  : Gives Energy consumption stats for the cluster with the given UUID between given start and end time.
--cluster_uuid --time_frame             : Gives Energy consumption stats for the cluster with the given UUID for the given time frame.
--host_uuid                             : Gives Energy consumption stats for the host with the given UUID for the last hour.
--host_uuid --start_time --end_time     : Gives Energy consumption stats for the host with the given UUID between given start and end time.
--host_uuid --time_frame                : Gives Energy consumption stats for the host with the given UUID for the given time frame.




Validation Examples :
1. get_power_stats.py: error: Either None or one of the arguments --cluster_uuid --host_uuid --hc-granularity is required
2. get_power_stats.py: error: argument --host_uuid: not allowed with argument --cluster_uuid and --hc-granularity
3. get_power_stats.py: error: argument --cluster_uuid: not allowed with argument --host_uuid and --hc-granularity
4. get_power_stats.py: error: argument --hc-granularity: not allowed with argument --cluster_uuid and --host_uuid


Successful Examples
1.
   Power Stats: {'stats_specific_responses': [{'successful': True, 'message': None, 'start_time_in_usecs': 1740078000000000, 'interval_in_secs': 3600,
   'metric': 'power_consumption_instant_watt', 'values': [264, 265, 265, 271, 280, 275, 276, 253, 267, 269, 275, 268, 267, 268, 252, 248, 250, 248, 251,
   249, 247, 250, 252, 250, 250, 248, 247, 247, 250, 250, 250, 243, 248, 249, 251, 271, 270, 264, 265, 262, 259, 244, 246, 245, 243, 245, 245, 244]}]}
2.
   Power Stats: {'stats_specific_responses': [{'successful': True, 'message': None, 'start_time_in_usecs': 1740078000000000, 'interval_in_secs': 3600,
   'metric': 'power_consumption_instant_watt', 'values': [264, 265, 265, 271, 280, 275, 276, 253, 267, 269, 275, 268, 267, 268, 252, 248, 250, 248, 251,
   249, 247, 250, 252, 250, 250, 248, 247, 247, 250, 250, 250, 243, 248, 249, 251, 271, 270, 264, 265, 262, 259, 244, 246, 245, 243, 245, 245, 244]}]}
3.
+--------------+-----------------+----------------------+
| Cluster Name | Number of Nodes | Energy Consumed(KWh) |
+--------------+-----------------+----------------------+
| bigtwin15-4  |        1        |                0.243 |
| bigtwin15-3  |        1        |                  0.0 |
+--------------+-----------------+----------------------+


README :
This section explains how to create a Python virtual environment and install the required non-standard libraries using pip:


Setting Up the Python Virtual Environment
To ensure that your project dependencies are isolated from other projects and the system Python packages, it is recommended to use a virtual environment. Follow these steps to set up a virtual environment and install the required libraries:


Step 1: Create a Virtual Environment
Open a terminal and navigate to your project directory:


Create a virtual environment named venv:
python3 -m venv .virtualenvpower


Step 2: Activate the Virtual Environment
On macOS and Linux:
source .virtualenvpower/bin/activate


On Windows:
.virtualenvpower\Scripts\activate


Step 3: Install Required Libraries
With the virtual environment activated, install the required non-standard libraries using pip. The libraries needed for this project are listed below:


requests
prettytable


You can install these libraries by running the following command:
pip install requests prettytable


Step 4: Verify Installation
To verify that the libraries have been installed correctly, you can list the installed packages:


pip list


You should see requests and prettytable listed among the installed packages.


Step 5: Deactivate the Virtual Environment
Once you are done working in the virtual environment, you can deactivate it by running:


deactivate


By following these steps, you will have a virtual environment set up with the necessary libraries installed, ensuring that your project dependencies are managed effectively.


"""


import requests
import argparse
from datetime import datetime
import time
import json
from statistics import mean
from requests.auth import HTTPBasicAuth
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from prettytable import PrettyTable


# ensure best practices are followed regarding certificate management
# consider the implications of disabling certificate verification in a production environment.
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def make_request(api_url, auth, headers=None, method="GET", data=None):
   """
   Makes a request to the given API URL using the specified method.


   Parameters:
   api_url (str): The URL of the API endpoint.
   auth (tuple): A tuple containing the username and password for authentication.
   headers (dict): Optional headers to include in the request.
   method (str): The HTTP method to use (GET, POST, PUT, DELETE).
   data (dict): The data to send in the request body.


   Returns:
   dict: The JSON response
   """
   headers = {
       "Content-Type": "application/json"
   }
   try:
       response = requests.request(method, api_url, auth=auth, headers=headers, json=data, verify=False)
       response.raise_for_status()  # Raise an HTTPError for bad responses
       return response.json()
   except requests.exceptions.RequestException as e:
       print(f"An error occurred: {e}")
       return None


def get_power_stats(api_url, auth):
   """
   Makes a GET request to the given API URL to retrieve power stats.


   Parameters:
   api_url (str): The URL of the API endpoint.
   auth (tuple): A tuple containing the username and password for authentication.
   headers (dict): Optional headers to include in the request.


   Returns:
   dict: The JSON response from the API if the request is successful.
   None: If the request fails.
   """
   try:
       return make_request(api_url, auth)
   except requests.exceptions.RequestException as e:
       print(f"An error occurred: {e}")
       return None


def convert_to_epoch(time_str):
   """
   Converts a time string in the format "YYYY-MM-DDTHH:MM:SSZ" to epoch time in microseconds.


   Parameters:
   time_str (str): The time string to convert.


   Returns:
   int: The epoch time in microseconds.
   """
   dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")
   epoch_time = int(time.mktime(dt.timetuple()) * 1e6)
   return epoch_time


def get_cluster_uuid_list(pc_ip, auth):


   cluster_list_url = "https://{pc_ip}:9440/api/clustermgmt/v4.0/config/clusters/".format(pc_ip=pc_ip)


   response = make_request(cluster_list_url, auth)
   cluster_info = []
   for cluster in response['data']:
       if "AOS" in cluster["config"]["clusterFunction"]:
           uuid = cluster['extId']
           number_of_hosts = cluster['nodes']['numberOfNodes']
           cluster_name = cluster['name']
           cluster_info.append((uuid, cluster_name, number_of_hosts))


   return cluster_info


def convert_timeframe_to_hours(start_time_epoch=0, end_time_epoch=0):
   """
   Converts the time frame string to total hours.
   """
   diff = end_time_epoch - start_time_epoch
   return diff / 1e6 / 3600


def get_time_frame(time_frame):


   end_time_epoch = int(time.time() * 1e6)
   if time_frame.upper() == 'LASTHOUR':
       start_time_epoch = end_time_epoch - int(3600 * 1e6)
   elif time_frame.upper() == 'LASTDAY':
       start_time_epoch = end_time_epoch - int(24 * 3600 * 1e6)
   elif time_frame.upper() == 'LASTWEEK':
       start_time_epoch = end_time_epoch - int(7 * 24 * 3600 * 1e6)
   elif time_frame.upper() == 'LASTMONTH':
       start_time_epoch = end_time_epoch - int(30 * 24 * 3600 * 1e6)
   else:
       start_time_epoch = 0
       end_time_epoch = 0


   return (start_time_epoch, end_time_epoch)


def get_power_stats_for_individual_cluster(pc_ip, auth, cluster_uuid, start_time_epoch=None, end_time_epoch=None, down_sample_interval=300):
   """
   Get power stats for a specific cluster registered to the Prism Central.


   Returns:
   """   
   base_url = "https://{pc_ip}:9440/PrismGateway/services/rest/v2.0/clusters/{uuid}/stats?"


   v2_stats_url = base_url + ("metrics=power_consumption_instant_watt&" +
                              "start_time_in_usecs={start}&" +
                              "end_time_in_usecs={end_time}&" +
                              "interval_in_secs={interval}")


   v2_stats_url = v2_stats_url.format(pc_ip=pc_ip,
                                      uuid=str(cluster_uuid),
                                      start=start_time_epoch,
                                      end_time=end_time_epoch,
                                      interval=down_sample_interval)


   return get_power_stats(v2_stats_url, auth)


def get_power_stats_for_individual_host(pc_ip, auth, host_uuid, start_time_epoch=None, end_time_epoch=None, down_sample_interval=300):
   """
   Get power stats for a specific host registered to the Prism Central.


   Returns:
   """  
   base_url = "https://{pc_ip}:9440/PrismGateway/services/rest/v2.0/hosts/{uuid}/stats?"


   v2_stats_url = base_url + ("metrics=power_consumption_instant_watt&" +
                              "start_time_in_usecs={start}&" +
                              "end_time_in_usecs={end_time}&" +
                              "interval_in_secs={interval}")


   v2_stats_url = v2_stats_url.format(pc_ip=pc_ip,
                                      uuid=str(host_uuid),
                                      start=start_time_epoch,
                                      end_time=end_time_epoch,
                                      interval=down_sample_interval)


   return get_power_stats(v2_stats_url, auth)


def get_power_stats_for_all_clusters(pc_ip, auth, start_time_epoch=None, end_time_epoch=None, down_sample_interval=300, output_format='json'):
   """
   Get power stats for all clusters registered to the Prism Central.


   Returns:
       Returns the power stats for all the clusters registered to the Prism Central.
   """
   cluster_info = get_cluster_uuid_list(pc_ip, auth)
   t = PrettyTable(['Cluster Name', 'Number of Nodes', 'Energy Consumed(KWh)'])
   t.align['Cluster Name'] = 'l'
   t.align['Number of Nodes'] = 'c'
   t.align['Energy Consumed(KWh)'] = 'r'
   t.padding_width = 1
   consumption_list = {}
   for (cluster_uuid, name, count) in cluster_info:
       power_stats = get_power_stats_for_individual_cluster(pc_ip, auth, cluster_uuid, start_time_epoch, end_time_epoch, down_sample_interval)
       power_stats_list = power_stats["stats_specific_responses"][0]["values"] or [0]
       total_hours = convert_timeframe_to_hours(start_time_epoch, end_time_epoch)
       total_energy_consumed = total_hours * mean(power_stats_list) / 1000
       t.add_row([name, count, "%.2f" % total_energy_consumed])
       consumption_list[name] = "%0.2f KWh" % total_energy_consumed
   if output_format == 'table':
       print(t)
   return consumption_list


def parse_arguments():
   """
   Parse the command-line arguments and return the Namespace object.


   Returns:
   Namespace: The parsed arguments.
   """
   parser = argparse.ArgumentParser(description='Get power stats(in Watts) from the Prism REST API v2.0.')
   parser.add_argument('--pc_ip', type=str, required=True, help='Prism Central IP address.')
   parser.add_argument('--username', type=str, required=True, help='Prism Central Username')
   parser.add_argument('--password', type=str, required=True, help='Prism Central Password')


   group1 = parser.add_mutually_exclusive_group(required=False)
   group1.add_argument('--cluster_uuid', type=str, required=False, help='Registered(to pc_ip) cluster\'s UUID for which power consumtion stats are to be retrieved.')
   group1.add_argument('--host_uuid', type=str, required=False, help='Registered(to pc_ip) Host\'s UUID for which power consumtion stats are to be retrieved.')
   group1.add_argument('--hc-granularity', type=str, required=False, default='CLUSTER', help='Granularity for the power stats. Possible values : CLUSTER|HOST')




   group2 = parser.add_argument_group()


   group2.add_argument('--start_time', type=str, required=False, help='Start time for the power stats in the format "YYYY-MM-DDTHH:MM:SSZ".')
   group2.add_argument('--end_time', type=str, required=False, help='End time for the power stats in the format "YYYY-MM-DDTHH:MM:SSZ".')   
   group2.add_argument('--time_frame', type=str, required=False, default='LASTHOUR', help='Time frame for the power stats. Possible values : LASTHOUR|LASTDAY|LASTWEEK|LASTMONTH')


   parser.add_argument('--down_sample_interval', type=int, required=False, default=300, help='Down sample interval in seconds.')
   parser.add_argument('--output-format', type=str, required=False, default='table', help='Output format for the power stats. Possible values : table, json')
   return parser.parse_args()


if __name__ == "__main__":
   args = parse_arguments()


   auth = HTTPBasicAuth(args.username, args.password)


   if args.start_time is not None and args.end_time is not None:
       start_time_epoch = convert_to_epoch(args.start_time)
       end_time_epoch = convert_to_epoch(args.end_time)
   elif args.time_frame is not None :
       start_time_epoch, end_time_epoch = get_time_frame(args.time_frame)


   if args.cluster_uuid is not None:
       power_stats = get_power_stats_for_individual_cluster(args.pc_ip, auth, args.cluster_uuid, start_time_epoch, end_time_epoch, args.down_sample_interval)
       print(f"Power Stats: {power_stats}")
   elif args.host_uuid is not None:
       power_stats = get_power_stats_for_individual_host(args.pc_ip, auth, args.host_uuid, start_time_epoch, end_time_epoch, args.down_sample_interval)
       print(f"Power Stats: {power_stats}")
   elif args.hc_granularity.upper() == 'CLUSTER':
       power_stats = get_power_stats_for_all_clusters(args.pc_ip, auth, start_time_epoch, end_time_epoch, args.down_sample_interval, args.output_format)
       if args.output_format == 'json':
           print(json.dumps(power_stats, indent=2))
   else:
       print("Invalid arguments passed. Please check the usage help.")
