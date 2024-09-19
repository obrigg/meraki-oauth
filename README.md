# Meraki API OAuth2 Examples

`minimalistic_example.py`: This is a minimalistic Python example demonstrating how to leverage Meraki's OAuth2 capabilities to authenticate and make API requests using OAuth tokens.

## Prerequisites

Before running the code, ensure you have the following:

1. Python 3.x installed.
2. Required Python libraries:
   - `requests`
   - `requests_oauthlib`
   
   You can install these libraries using pip:
   ```bash
   pip install requests requests_oauthlib
   ```
3. Meraki Dashboard API Access:
    * Register your app on the [Meraki OAuth app registry](as.meraki.com) to obtain a CLIENT_ID and CLIENT_SECRET.
    * Set up environment variables for your CLIENT_ID and CLIENT_SECRET for security purposes:
    ```bash
    export MERAKI_CLIENT_ID=<your-client-id>
    export MERAKI_CLIENT_SECRET=<your-client-secret>
    ```

## How It Works
This script follows the OAuth2 authorization flow to:
1. Request user authorization by redirecting them to Meraki’s OAuth authorization URL.
2. Receive an access token after user authorization.
3. Use the access token to interact with the Meraki API.

## Steps
1. Clone this repository.
2. Set the necessary environment variables.
3. Run the script.
4. After running the script, you will be prompted to visit an authorization URL. Open this URL in your browser and authorize the app.
5. After authorizing, you will be redirected to a URL (https://localhost/). Copy the entire URL from your browser and paste it into the script when prompted.
6. The script will use the access token to make an authenticated API request to list organizations in your Meraki account and print the response.

## Notes
* Redirect URI: For testing purposes, the redirect URI is set to `https://localhost`, which may not work unless you're running a local server. You can configure this in your Meraki app settings.
* Scopes: The scope used in this example is `dashboard:general:config:read`. Adjust the scope based on the permissions your app needs.


----
### Licensing info
Copyright (c) 2024 Cisco and/or its affiliates.

This software is licensed to you under the terms of the Cisco Sample
Code License, Version 1.1 (the "License"). You may obtain a copy of the
License at

               https://developer.cisco.com/docs/licenses

All use of the material herein must be in accordance with the terms of
the License. All rights not expressly granted by the License are
reserved. Unless required by applicable law or agreed to separately in
writing, software distributed under the License is distributed on an "AS
IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
or implied.
