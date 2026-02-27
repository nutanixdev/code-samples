/*
Use the Nutanix v4 REST APIs to request a list of all available VMs
With the response, show the total number of VMs in the response
Requires Prism Central 7.5 or later and AOS 7.5 or later
Author: Chris Rasmussen, Senior Technical Marketing Engineer, Nutanix
Date: February 2026
*/

using System.Net;
using System.Net.Http.Headers;
using System.Net.Security;
using System.Security.Authentication;
using System.Text;
using System.Text.Json;

// not required for this demo but is required
// for POST requests combined with JSON payload
// using System.Text.Json;

namespace Nutanix_v4_API_Demo___List_VMs
{
    class Program
    {

        /*
         * get an Int32 value from a JSON element
        */
        static int? GetInt32(JsonElement obj, string prop) =>
            obj.TryGetProperty(prop, out var v) && v.ValueKind == JsonValueKind.Number && v.TryGetInt32(out var i) ? i : null;

        static async Task Main(string[] args)
        {

            try
            {

                /**
                 * alter these settings before use in your environment
                */
                var requestUrl = "https://10.0.0.1:9440/api/vmm/v4.2/ahv/config/vms";
                var username = "admin";
                var password = "nutanix/4u";

                /*
                 * format for adding payloads to these requests
                 * this is not required for this demo but has been left here
                 * as an example
                */
                // var payload = new { header_name = "header_value" };

                var handler = new SocketsHttpHandler
                {
                    AutomaticDecompression = DecompressionMethods.GZip | DecompressionMethods.Deflate,
                    /*
                     * optionally restrict TLS versions whilst still skipping validation
                    */
                    SslOptions = new SslClientAuthenticationOptions
                    {
                        EnabledSslProtocols = SslProtocols.Tls12 | SslProtocols.Tls13,
                        /*
                         * accept any SSL certificate
                         * this is not recommended in production
                        */
                        RemoteCertificateValidationCallback = (sender, cert, chain, errors) => true
                    }
                };

                // request timeout
                using var http = new HttpClient(handler)
                {
                    Timeout = TimeSpan.FromSeconds(30)
                };


                /*
                 * setup authentication
                 * this uses the username and password variables defined at the top of this demo
                */
                var base64 = Convert.ToBase64String(
                    Encoding.UTF8.GetBytes(
                        $"{username}:{password}"
                    )
                );
                http.DefaultRequestHeaders.Authorization = new AuthenticationHeaderValue(
                    "Basic", base64
                );

                /*
                 * add default headers
                */
                http.DefaultRequestHeaders.UserAgent.ParseAdd(
                    "Nutanix_v4_API_Demo___List_VMs/1.0 (+https://www.nutanix.dev)"
                );
                http.DefaultRequestHeaders.Accept.ParseAdd(
                    "application/json"
                );
                http.DefaultRequestHeaders.Add(
                    "X-Correlation-Id",
                    Guid.NewGuid().ToString()
                );

                /*
                 * specify this is an HTTP GET request
                */
                using var req = new HttpRequestMessage
                    (HttpMethod.Get,
                    requestUrl
                );
                /*
                 * the following syntax is not required for this demo
                 * but has been left here an example of sending an HTTP POST request
                */
                /*
                using var req = new HttpRequestMessage
                    (HttpMethod.Post,
                    requestUrl
                );
                */

                /*
                 * add custom headers
                 * potential use cases for Nutanix v4 APIs and SDKs:
                 * 1. X-Ntnx-Api-Key: API key authentication
                 * 2. Ntnx-Request-Id for APIs requiring request idempotency
                 * 3. If-Match to manage request collision
                */
                // req.Headers.Add("Ntnx-Request-Id", "b95137e0-d39d-41db-a3fb-9cc8d3b07fe3");

                /*
                 * serialize the payload to JSON format
                 * this is not required for this demo but will be required for Nutanix v4 APIs requiring request payloads
                */
                /*
                 * var json = JsonSerializer.Serialize(payload, new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.CamelCase });
                 * req.Content = new StringContent(json, Encoding.UTF8, "application/json");
                */

                // send the request
                using var res = await http.SendAsync(req, HttpCompletionOption.ResponseHeadersRead);
                var body = await res.Content.ReadAsStringAsync();

                // verify the request was successful
                if (!res.IsSuccessStatusCode)
                {
                    Console.Error.WriteLine($"Request failed: {(int)res.StatusCode} {res.ReasonPhrase}");
                    Console.Error.WriteLine(body);
                    Environment.ExitCode = 1;
                    return;
                }

                using var doc = JsonDocument.Parse(body);
                var root = doc.RootElement;

                // response metadata
                if (root.TryGetProperty("metadata", out var metadata) && metadata.ValueKind == JsonValueKind.Object)
                {
                    // for this demo, show some basic info about the response
                    var total = GetInt32(metadata, "totalAvailableResults");
                    Console.WriteLine($"Total available results (across pages): {total}");
                }
            }
            /*
             * extremely basic exception handling, just for demo purposes
             * production environments typically require appropriate exception handling
            */
            catch (System.NotSupportedException ex)
            {
                Console.WriteLine("An error occurred while making the request e.g. an unsupported protocol.");
                Console.WriteLine(ex.Message.ToString());
            }
            catch (System.Net.WebException ex)
            {
                Console.WriteLine("An error occurred while making the request (e.g. network, request properties, authentication).");
                Console.WriteLine(ex.Message.ToString());
            }
            catch (System.Net.ProtocolViolationException ex)
            {
                Console.WriteLine("A payload/request body error occurred while making the request.");
                Console.WriteLine(ex.Message.ToString());
            }
            finally
            {
                Console.WriteLine("\r\nPress any key to exit.");
                /**
                 * wait for the user to press a key
                 * this is only here because there's an assumption/guess that, initially at least,
                 * this small demo app will be run inside Visual Studio
                */
                Console.ReadKey();
            }

        }

    }

}