Nutanix Developer Portal Code Samples - PowerShell
##################################################

To use the PowerShell code samples, the following environment is recommended.

- Windows PowerShell 5.1 or later
- A suitable PowerShell editor, e.g. `Microsoft Visual Studio Code <https://code.visualstudio.com/>`_ or `Microsoft Visual Studio Community <https://visualstudio.microsoft.com/vs/community/>`_.  Instructions for extending Visual Studio Code with PowerShell support are provided below.
- An alternative editor, built into some versions of Windows, is **PowerShell ISE**
- Access to a Nutanix Cluster for API testing purposes.
- Nutanix Community Edition is supported but may not always provide the exact same APIs as a "full" Nutanix cluster.

.. note:: Please note that instructions provided in this repository will assume the use of Visual Studio Code software.

PowerShell Script Usage
.......................

The provided PowerShell scripts are designed to be standalone and can be run without additional dependencies.

The examples and screenshots below are from the **create_vm_v3_basic.ps1** sample.

#. Open Windows PowerShell (administrative permissions are not required).
#. Verify your PowerShell version by entering **$psversiontable** or **$PSVersionTable** (the variable is not case-sensitive)

   .. figure:: check_ps_version.png

#. Select **View** > **Extensions**.
#. In the search field, enter **PowerShell**.
#. Install the **PowerShell** extension created by **Microsoft**.
#. Using the selected code sample, create a new PowerShell file (extension **.ps1**, by default).
#. Select the **$parameters.cluster_ip** variable with the correct IP address/FQDN of your cluster (the scripts will prompt for credentials).
#. Click **Debug** > **Start Debugging**.
#. The script will run and prompt for a username and password in the **Terminal** window.
#. After entering credentials, and if the request was successful, the JSON response will show a status as shown below.

   .. figure:: script_output.png
