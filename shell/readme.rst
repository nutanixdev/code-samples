Nutanix Developer Portal Code Samples - Bash Shell
##################################################

To use the Bash Shell code samples, the following environment is recommended.

- **curl** command available
- **jq** (official documentation for `jq <https://stedolan.github.io/jq/download/>`_)
- The accompanying JSON files from this repository (instructions and usage provided below).
- A suitable editor, e.g. `Microsoft Visual Studio Code <https://code.visualstudio.com/>`_ for GUI editing or **vi** for terminal editing.
- Access to a Nutanix Cluster for API v2.0 testing purposes.
- Access to a Nutanix Prism Central instance for API v3 testing purposes.
- Nutanix Community Edition is supported but may not always provide the exact same APIs as a "full" Nutanix cluster.

.. note:: The readme below assumes you are creating the scripts from scratch and have not cloned the entire repository to your local system.

Bash Shell Script Usage
.......................

The provided bash shell scripts are designed to be standalone and can be run without additional dependencies beyond those provided above.

The examples and screenshots below are from the **create_vm_v3_basic/create_vm_v3_basic** sample.  This sample uses **create_vm_v3_basic.json** for the request parameters.

#. Create a new file:

   .. code-block:: bash

      touch ~/create_vm_v3_basic

#. Open the new file in vi:

   .. code-block:: bash

      vi ~/create_vm_v3_basic

#. Have the code sample open in your browser.
#. Copy the script source to your clipboard.
#. Enable vi **INSERT** mode by pressing *i*.
#. Paste the script source into vi by pressing Ctrl-Shift-V (typical for Linux terminals) or by pressing the middle mouse button, if available.

   .. note:: The copy and paste steps don't really need to be included as they will vary from system to system.  They're included here for completeness' sake only.

#. Exit vi **INSERT** mode by pressing **ESC**.
#. Save the file by using the vi save and quit keystroke sequence:

   .. code-block: bash

      :wq

#. Make the script executable:

   .. code-block: bash

      chmod u+x ~/create_vm_v3_basic

#. Repeat steps 1-8 for the accompanying JSON file (the JSON file does not need to be executable).  This file is required as it contains the parameters used for cURL request:

   - Copy the JSON source into the local clipboard, if using the example from the repository
   - In the terminal, create the JSON file and add the contents:

     .. code-block: bash

        touch ~/create_vm_v3_basic.json
        vi ~/create_vm_v3_basic.json

   - Press "i" for vi INSERT mode
   - Paste the JSON into vi
   - Press ESC to exit INSERT mode
   - Save the file by using the vi save and quit keystroke sequence ":wq", as before (without the quotes!)

#. Run the script:

   .. code-block: bash

      ~/create_vm_v3_basic

   .. figure:: script_output.png

#. Check the output to make sure the request has a state of **PENDING**.

