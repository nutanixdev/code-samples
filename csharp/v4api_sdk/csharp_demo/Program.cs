/*
Use the Nutanix v4 API SDKs to register a Prism Central
domain to Nutanix Central
Requires Prism Central 7.5.1 or later, AOS 7.5.1
or later and Nutanix Central 2.0 or later
Author: Chris Rasmussen, Senior Technical Marketing Engineer, Nutanix
Date: June 2026
*/

using Nutanix.VmmSDK.Api;
using Nutanix.VmmSDK.Client;
using Nutanix.VmmSDK.Model.Vmm.V4.Ahv.Config;
using Nutanix.VmmSDK.Model.Request.Vm;
using System.Text.Json;
using System.Security;

// default Prism Central port
const int DefaultPort = 9440;

// console table width
// can be modified here for consoles/terminal with different sizes
const int ConsoleTableWidth = 120;

// load the environment configuration from environment.json
var jsonPath = Path.Combine(AppContext.BaseDirectory, "environment.json");
var jsonContent = File.ReadAllText(jsonPath);
var jsonConfig = JsonSerializer.Deserialize<EnvConfig>(jsonContent) ?? throw new InvalidOperationException("Failed to load environment configuration");

/// <summary>Reads a password from console input without echoing characters to the screen.</summary>
SecureString ReadPassword(string prompt = "Password: ")
{
    Console.Write(prompt);
    var password = new SecureString();

    while (true)
    {
        var key = Console.ReadKey(intercept: true);

        if (key.Key == ConsoleKey.Enter)
        {
            Console.WriteLine();
            break;
        }

        if (key.Key == ConsoleKey.Backspace)
        {
            if (password.Length > 0)
                password.RemoveAt(password.Length - 1);
        }
        else
        {
            password.AppendChar(key.KeyChar);
        }
    }

    password.MakeReadOnly();
    return password;
}

// get the user's password
using var password = ReadPassword("Enter password:");

// setup the connection configuration
var config = new Configuration()
{
    Host = jsonConfig.pc_fqdn,
    Port = DefaultPort,
    Username = jsonConfig.pc_username,
    Password = password,
    VerifySsl = false
};

// setup the API client and VPI instance
var client = new ApiClient(config);
var vmApi = new VmApi(client);

// try to list the VMs, following up with a list of those VMs
// display an appropriate message if the VM list request fails
try
{
    var request = new ListVmsRequest();
    var response = vmApi.ListVms(request);
    var vms = response.Data as List<Vm>;

    if (vms == null || vms.Count == 0)
    {
        Console.WriteLine("No virtual machines found.");
        return;
    }

    Console.WriteLine($"{"Name",-70} {"Power State",-15} {"UUID"}");
    Console.WriteLine(new string('-', ConsoleTableWidth));

    foreach (Vm vm in vms)
    {
        Console.WriteLine($"{vm.Name,-70} {vm.PowerState.ToString() ?? "unknown",-15} {vm.ExtId}");
    }

    Console.WriteLine($"\nTotal: {vms.Count} VM(s)");
}
catch (ApiException ex)
{
    Console.Error.WriteLine($"API error {ex.ErrorCode}: {ex.Message}");
}