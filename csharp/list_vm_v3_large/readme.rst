C# Code Samples - list_vm_v3_large.cs
#####################################

This readme file is specifically for the **list_vm_v3_large.cs** C# console app.

The setup instructions are the same as all other console apps in this repository.  This file is provided as additional/supplemental information for this specific code sample.

Please see the main_ page for general instructions.

Code Sample Details
...................

A quick intro, first.  The **list_vm_v3.cs** code sample shows a basic demo of REST API interactions with C#.  There is no provision for environments of a specific size as all API requests will be made with the default parameters.  For example:

- A maximum of 20 entities are returned with each request
- No offset has been specified i.e. every request will return VMs starting 0-19

In large environments this information is not overly useful.

**list_vm_v3_large.cs** has been provided with a number of additional capabilities and "architecture" choices:

- Clusters with >500 VMs will be identified.
- A single request will be made if the cluster has <=500 VMs i.e. VM 0-499.
- Additional requests will be made for VMs 500-n (where n is the total number of VMs in the cluster).
- The API request "work" has been broken out into a dedicated **RESTClient** class that exposes a public **SendRequest** method.
- The **RESTClient** class constructor accepts an array of parameters so that a single instance of the **RESTClient** class can be reused.
- The **SendRequest** method returns an instance of **RequestResponse**.
- **RequestResponse** contains public properties for a response **Code**, **Message** and **Details**, making it easy to see what the request result was in the event of a caught exception.
- The **SendRequest** method will be called as many times as necessary so that all VMs are captured.  For example:

   - A cluster with 1407 VMs will have the **SendRequest** method called three times.
   - The first request will returns VMs 0-499 (500 VMs).
   - The second request will return VMs 500-999 (500 VMs).
   - The third and final request will return VMs 1000-406 (407 VMs).

- A final prompt ensures the console app doesn't "flash" before the user can view the output.

While this demo is considerably more "advanced" than the standard **list_vm_v3.cs** demo, please still make sure to modify the code appropriately before you use it in production.

An example of the console application's output is shown below:

   .. figure:: ../app_running_large.png

.. _main: https://github.com/nutanixdev/code-samples/tree/master/csharp