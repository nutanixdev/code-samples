#########################
Create Detailed API v3 VM
#########################

Python script to connect to Prism Central and use the v3 APIs to create a VM with detailed specs.

Unlike the basic example also available in this repository, this sample creates a virtual machine with attached disk and network adapter.

**********
Disclaimer
**********

This is **not** a production-grade script.  Please make sure you add appropriate exception handling and error-checking before running it in production.  See note re versions below, too.

******
Author
******

Chris Rasmussen, Developer Content Architect, Nutanix (Melbourne, AU)

*********
Changelog
*********

- 2020.02.20 - Code sample updated to deal with "missing cluster reference" case
- 2019.07.23 - Code sample created

*******
Details
*******

Connect to Prism Central and use the v3 APIs to create a VM with detailed specs.

Requires create_vm_v3_detailed.json to be populated with the following information:

- **pc_ip**: Prism Central IP address
- **username**: Prism Central username
- **vm_name**: The name of the VM to create
- **cluster_name**: The name of the cluster to create the VM on
- **cluster_uuid**: The UUID of the cluster to create the VM on
- **vcpus_per_socket**: The number of vCPUs per socket to assign to the new VM
- **num_sockets**: The number of sockets to assign to the new VM
- **memory_size_mib**: The memory size in MiB to assign to the new VM
- **first_disk_size_mib**: The size of the first disk in MiB to assign to the new VM
- **first_nic_subnet_name**: The name of the VM's first NIC's network/subnet
- **first_nic_subnet_uuid**: The UUID of the VM's first NIC's network/subnet

Note re cluster UUID - This is required to deal with the use case where the specified Prism Central instance has multiple connected clusters (quite common in the real world).

Example API **POST** request to get the cluster UUID:

.. code-block:: bash

   https://pc_ip:9440/api/nutanix/v3/clusters/list

Body to use with the request above:

.. code-block:: json

   {"kind":"cluster"}

Note re subnet UUID - This is required when creating attached VM NICs.

Example API **POST** request to get the subnet UUID:

.. code-block:: bash

   https://pc_ip:9440/api/nutanix/v3/subnets/list

Body to use with the request above:

.. code-block:: json

   {"kind":"subnet"}   


*****
Usage
*****

Virtual Environment
===================

All the steps below assume you have a terminal session running with the current directory set to the location of the script.

- It is strongly recommended to run development scripts like this within a virtual environment.  For example, if using Python 3.7 on Linux:

  .. code-block:: bash

     python3.7 -m venv venv
     . venv/bin/activate

- Install dependencies:

  .. code-block:: bash

     pip3 install -e .

- Edit **create_vm_v3_detailed.json** to match your environment

Script Command Line
===================

.. code-block:: bash

   python3.7 create_vm_v3_detailed.py create_vm_v3_detailed.json --help

Generates:

.. code-block:: bash

   usage: create_vm_v3_detailed.py [-h] json

   positional arguments:
     json        JSON file containing query parameters

   optional arguments:
     -h, --help  show this help message and exit

*****
Notes
*****

- High-level testing has been carried out on Prism Central version 5.11
- Other versions may produce unpredictable results
- The installation of specific Python versions, pip3 etc are beyond the scope of this readme

*******
Example
*******

A complete command-line example is shown below:

.. code-block:: bash

   python3.7 create_vm_v3_detailed.py create_vm_v3_detailed.json

**********
Screenshot
**********

This is what the script looks like as it is run.  This screenshot is the output of the example command above.

.. figure:: screenshot.png

*******
Support
*******

These scripts are *unofficial* and are not supported or maintained by Nutanix in any way.

In addition, please also be advised that these scripts may run and operate in ways that do not follow best practices.  Please check through each script to ensure it meets your requirements.

**Changes will be required before these scripts can be used in production environments.**