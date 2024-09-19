import os
import requests
from requests_oauthlib import OAuth2Session

# Replace these values with your actual client ID and secret from the Meraki app registry
CLIENT_ID = os.getenv('MERAKI_CLIENT_ID')  # Best to use environment variables for security
CLIENT_SECRET = os.getenv('MERAKI_CLIENT_SECRET')
AUTHORIZATION_BASE_URL = 'https://as.meraki.com/oauth/authorize'  # Authorization URL
TOKEN_URL = 'https://as.meraki.com/oauth/token'  # Token URL
REDIRECT_URI = 'https://localhost'  # This is your redirect URI, it won't work and that's ok.

# OAuth scopes define the access your app will have
SCOPE = "dashboard:general:config:read"

# Step 1: User Authorization URL
meraki_oauth = OAuth2Session(CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPE)

# Step 2: Direct user to the authorization URL
authorization_url, state = meraki_oauth.authorization_url(AUTHORIZATION_BASE_URL)

print(f'Go to this URL and authorize the app: {authorization_url}')

# Step 3: User provides authorization response with redirect to your callback
# You would typically receive this in a web app, but for testing you can copy the full URL manually
redirect_response = input('Paste the full redirect URL here: ')

# Step 4: Fetch the access token
token = meraki_oauth.fetch_token(TOKEN_URL, authorization_response=redirect_response, client_secret=CLIENT_SECRET)

# Step 5: Use the access token to interact with the API
headers = {
    'Authorization': f'Bearer {token["access_token"]}',
    'Content-Type': 'application/json'
}

# Make an API call to list organizations
# Replace these with relevant API calls you'd like to make.
response = requests.get('https://api.meraki.com/api/v1/organizations', headers=headers)
print(response.json())
