Nutanix Developer Portal Code Samples - create_vm_v3_basic.ps1
##############################################################

This readme file is specifically for the **create_vm_v3_basic.ps1** PowerShell script.

The setup instructions are the same as all other PowerShell scripts in this repository.  This file is provided as additional/supplemental information for this specific code sample.

Please see the `main <https://github.com/nutanixdev/code-samples/tree/master/powershell>`_ page for general instructions.

Script Usage
............

Once you have configured your system to run these scripts (see link above), the script can be run as follows.

#. Edit **create_vm_v3_basic.ps1** and edit the following link to match your Prism Central IP address.

   .. code-block:: powershell

      $parameters.cluster_ip = "10.0.0.1"

#. Edit **create_vm_v3_basic.ps1** and edit the following variable to suit your requirements:

   .. code-block:: powershell

      $parameters.vm_name = "BasicVMViaAPIv3"

#. Execute the script:

   .. code-block:: powershell

      create_vm_v3_basic.ps1

#. Verify the script ran successfully and that the batch API request returned HTTP code 202:

   .. figure:: script_output.png

#. If you prefer, you can also check Prism Central to ensure your VM was created successfully.