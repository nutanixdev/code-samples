Bash Code Samples - batch_request_simple
########################################

This readme file is specifically for the **batch_request_simple** Bash script.

The setup instructions are the same as all other Bash scripts in this repository.  This file is provided as additional/supplemental information for this specific code sample.

Please see the `main <https://github.com/nutanixdev/code-samples/tree/master/shell>`_ page for general instructions.

Script Usage
............

Once you have configured your system to run these scripts (see link above), the script can be run as follows.

#. Edit **batch_request_simple.json** and change the Prism Central IP address to match your environment.

   .. code-block:: json

      "cluster_ip":"10.0.0.1"

#. Edit **batch_request_simple.json** and edit the following variables to suit your requirements:

   .. code-block:: json

      "username":"admin"

#. Edit **batch_request_simple** and edit the following variables to suit your requirements:

   .. code-block:: json

      \"name\": \"vm_from_batch\",

   .. code-block:: json

      \"name\": \"image_from_batch\"

#. Execute the script:

   .. code-block:: bash

      ./batch_request_simple

#. Verify the script ran successfully and that the batch API request returned HTTP code 202:

   .. figure:: script_output.png

#. If you prefer, you can also check Prism Central to ensure the VM and image were both created successfully.