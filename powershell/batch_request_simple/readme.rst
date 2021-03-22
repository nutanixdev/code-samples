Nutanix Developer Portal Code Samples - batch_request_simple.ps1
################################################################

This readme file is specifically for the **batch_request_simple.ps1** PowerShell script.

The setup instructions are the same as all other PowerShell scripts in this repository.  This file is provided as additional/supplemental information for this specific code sample.

Please see the `main <https://github.com/nutanixdev/code-samples/tree/master/powershell>`_ page for general instructions.

Script Usage
............

Once you have configured your system to run these scripts (see link above), the script can be run as follows.

#. Edit **batch_request_simple.ps1** and edit the following link to match your Prism Central IP address.

   .. code-block:: powershell

      $parameters.cluster_ip = "10.0.0.1"

#. Edit **batch_request_simple.ps1** and edit the following variables to suit your requirements:

   .. code-block:: json

      ""name"": ""vm_from_batch"", `

   .. code-block:: json

      ""name"": ""image_from_batch"" `

#. Execute the script:

   .. code-block:: powershell

      batch_request_simple.ps1

#. Verify the script ran successfully and that the batch API request returned HTTP code 202:

   .. figure:: script_output.png

#. If you prefer, you can also check Prism Central to ensure the VM and image were both created successfully.