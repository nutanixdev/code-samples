C# Code Samples - list_vm_v3.cs
###############################

This readme file is specifically for the **list_vm_v3.cs** C# console app.

The setup instructions are the same as all other console apps in this repository.  This file is provided as additional/supplemental information for this specific code sample.

Please see the `main <https://github.com/nutanixdev/code-samples/tree/master/csharp>`_ page for general instructions.

Code Sample Details
...................

A quick intro, first.  The **list_vm_v3.cs** code sample shows a basic demo of REST API interactions with C#.

Please note there is no specific provision for environments of a specific size as all API requests will be made with the default parameters.  For example:

- A maximum of 20 entities are returned with each request
- No offset has been specified i.e. every request will return the first 20 VMs **only**
- If you are looking for code appropriate for use in large environments, please see the `list_vm_v3_large <https://github.com/nutanixdev/code-samples/tree/master/csharp/list_vm_v3_large>`_ code sample.
- A final prompt ensures the console app doesn't "flash" before the user can view the output.

Please make sure to modify the code appropriately before you use it in production.

An example of the console application's output is shown below:

   .. figure:: ../app_running.png
