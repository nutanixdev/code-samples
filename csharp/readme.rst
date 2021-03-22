Nutanix Developer Portal Code Samples - C#
##########################################

To use the C# code samples, the following environment is recommended.

- `Visual Studio Community <https://visualstudio.microsoft.com/vs/community/>`_ (free & recommended)
- Visual Studio "full" edition (commercial software)
- Access to a Nutanix Cluster for testing API v2.0 requests
- Access to Prism Central for API v3 requests
- Nutanix Community Edition is supported but may not always provide the exact same APIs as a "full" Nutanix cluster.
- The Newtonsoft.Json extension for .NET.  To install Newtonsoft.Json, please see the official `documentation <https://www.nuget.org/packages/Newtonsoft.Json/>`_.  **This will need to be done before continuing below**.

.. note:: Please note that instructions provided in this repository will assume the use of Visual Studio Community software.

Console Applications
....................

The provided C# console applications are designed to demonstrate use of the Nutanix Prism REST APIs from C#.  To use the samples in your environment, please follow the instructions below.

The examples and screenshots below are from the **list_vm_vs/list_vm_v3.cs** sample.

#. Open Visual Studio Community_
#. Select **Create a new project**

   .. figure:: new_project.png

#. Select **Console App (.NET Framework)** from the list of options (it may be easier to search for **console** in the search bar)

   .. figure:: new_console_app.png

#. Click **Next** and configure the app as appropriate for your environment (example shown below).

   .. figure:: configure_console_app.png

#. Click **Create**

#. Add a reference to **NewtonSoft.Json**:

   - Click **View** > **Other Windows** > **Package Manager Console**
   - Enter the following command:

      .. code-block:: bash

         Install-Package Newtonsoft.Json -Version 12.0.2

#. Add a reference to **System.Web.Extensions** - this is required for the **System.Web.Script.Serialization** that some code samples use:

   - Right-click **References** in the Solution Explorer and select **Add Reference**
   - Find **System.Web.Extensions** in the list and check the box next to it (the checkbox won't be visible until you mouse over the option)
   - Click OK

#. When the new console application is created, the default Program.cs contents can be completely replaced (copied/pasted) with the code from the repository sample you are using.

   - Tip: Make sure you replace **all** the existing contents of Program.cs, including all **Using** statements at the top.

#. In the default sample code, edit **ClusterIp**, **ClusterUsername** and **ClusterPassword** variables so they are correct for your environment.

#. Either build (Ctrl-Shift-B) or run (F5) the application.  The complete JSON response will be shown in the console application window.

#. The screenshots below show two examples:

   - An example of a console app aimed at small environments with fewer than 500 VMs.  This is taken from **list_vm_v3.cs**.
   - An example of a console app designed for larger environments i.e. more than 500 VMs.  This is taken from **list_vm_v3_large.cs**.

   .. figure:: app_running.png
   .. figure:: app_running_large.png

