import os
import json
import string
import secrets
import requests
from time import time
from rich import print as pp
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth2Session
from flask import Flask, request, redirect, session, url_for
from jinja2 import Environment, FileSystemLoader, select_autoescape


# In this example, we will be saving the OAuth refresh tokens in a clear text file
# NEVER STORE SECRECTS IN A CLEAR TEXT FILE! This is only for the simplicity of the example

def read_token_file() -> dict:
    try:
        with open("./refresh_tokens_prod.txt", 'r') as f:
            tokens = json.loads(f.read())
    except:
        print("Looks like the token list does not exist. Creating a new one...")
        with open("./refresh_tokens_prod.txt", 'w') as f:
            tokens = {}
            json.dump(tokens, f)
    return (tokens)


def update_token_file(org_id: str, token: str):
    tokens = read_token_file()
    tokens[str(org_id)] = token
    with open("./refresh_tokens_prod.txt", 'w') as f:
        json.dump(tokens, f)
    pp("Updated token list:\n")
    pp(tokens)
    pp("\n")


def remove_token(org_id: str):
    tokens = read_token_file()
    tokens.pop(str(org_id))
    with open("./refresh_tokens_prod.txt", 'w') as f:
        json.dump(tokens, f)
    pp("Updated token list:\n")
    pp(tokens)
    pp("\n")


def get_validated_token_list():
    pp("Validating token list...")
    tokens = read_token_file()
    for org_id, token in tokens.items():
        if is_token_still_valid(token):
            pass
        else:
            new_token = refresh_the_token(token)
            tokens[org_id] = new_token
            update_token_file(org_id, new_token)
    return(tokens)


def is_token_still_valid(token):
    if time() < token['expires_at']:
        pp(f"The Token for org {token['organization_id']} is still valid")
        return True
    else:
        pp(f"The Token for org {token['organization_id']} is not valid")
        return False


def refresh_the_token(token):
    pp(f"Refreshing token for org {token['organization_id']}...")
    new_token = oauth.refresh_token(token_url, refresh_token=token['refresh_token'], auth=basic_auth)
    pp(80*"*" + "\nRefreshed token: \n")
    pp (new_token)
    pp(80*"*")
    return(new_token)


# This function will be used to generate a random string for the "state"
def generate_random_string(length):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))


app = Flask(__name__)


# This information is obtained upon registration of a new app on Meraki's app registry (https://integrate.meraki.com/).
client_id = os.getenv('MERAKI_CLIENT_ID')
client_secret = os.getenv('MERAKI_CLIENT_SECRET')
authorization_base_url = 'https://as.meraki.com/oauth/authorize'
token_url = 'https://as.meraki.com/oauth/token'
redirect_uri = 'https://localhost:5050/callback'
scope = "dashboard:general:config:read"

# Meraki settings
meraki_base_url = "https://api.meraki.com/api/v1/"
meraki_headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}


# Step 1: Redirect the user to the Meraki Dashboard to authenticate
# and grant the app permission to access the organization

@app.route("/login")
def demo():
    """
    Step 1: User Authorization.
    Redirect the user/resource owner to the OAuth provider
    using an URL with a few key OAuth parameters.
    """    
    # State is used to prevent CSRF, keep this for later.
    state = generate_random_string(20)
    session['oauth_state'] = state
    session['oauth_token'] = None

    # Redirect the user to the Meraki consent form
    return redirect(authorization_url)


# Step 2: User authorization, this happens on the provider.

@app.route("/callback", methods=["GET"])
def callback():
    """
    Step 2: Retrieving an access token.
    The user has been redirected back from the provider to your registered
    callback URL. With this redirection comes an authorization code included
    in the redirect URL. We will use that to obtain an access token.
    """
    # Return an error, if an error is returned from the Auth server.
    if "error" in request.args.keys():
        error = request.args["error"]
        error_description = request.args["error_description"]
        # Setup Jinja2 environment
        env = Environment(
            loader=FileSystemLoader('.'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        # Load the template
        template = env.get_template('error.j2')
        # Render the template with data
        output = template.render(error=error, error_description=error_description)
        return(output)

    # Since no error is returned, use the authorizarion grant to obtain a refresh token.

    authorization_response = request.url
    token = oauth.fetch_token(token_url, authorization_response=authorization_response, client_secret=client_secret)
    print(80*"*" + "\nNew token: \n")
    print (token)
    print(80*"*")
    # TODO: error handling

    # Saving the refresh token to a "secure location"
    # "secure location" being a text file for the simplicity of the example.
    # NEVER STORE SECRECTS IN A CLEAR TEXT FILE!
    org_id = token['organization_id']
    update_token_file(org_id, token)
    return redirect(url_for('.networks'))


@app.route("/networks", methods=["GET"])
@app.route("/", methods=["GET"])
def networks():
    """
    Step 3: Fetching a protected resource using an OAuth 2 token.
    For this example it will be the list of networks in the organization.
    """
    tokens = get_validated_token_list()
    all_networks = []
    for org_id, token in tokens.items():
        url = meraki_base_url + 'organizations/' + org_id + '/networks'
        meraki_headers['Authorization'] = 'Bearer ' + token['access_token']
        try:
            networks = requests.get(url, headers=meraki_headers).json()
            #print(networks)
            if type(networks) == list:
                all_networks += networks
            else:
                all_networks.append({'organizationId': org_id, 'name': "Error getting information from this organization, perhaps the token needs <a href=https://localhost:5050/refresh>a refresh</a>?", 'productTypes': ""})
        except:
            all_networks.append({'organizationId': org_id, 'name': "Error getting information from this organization", 'productTypes': ""})
    # Filter data
    data = []
    for network in all_networks:
        data.append({'Org ID': network['organizationId'], 'Name': network['name'], 'Product Types': network['productTypes']})
    if data == []:
        data.append({'Org ID': "", 'Name': "", 'Product Types': ""})
    # Setup Jinja2 environment
    env = Environment(
        loader=FileSystemLoader('.'),
        autoescape=select_autoescape(['html', 'xml'])
    )
    # Load the template
    template = env.get_template('table.j2')
    # Render the template with data
    output = template.render(data=data)
    return(output)


@app.route("/delete_org/<org_id>", methods=["GET"])
def delete_token(org_id):
    """
    Delete an org from the token list.
    """
    try:
        remove_token(org_id)
        return redirect(url_for('.networks'))
    except KeyError:
        return f"No token found for organization {org_id}.", 404
    except Exception as e:
        return f"An error occurred: {str(e)}", 500


if __name__ == "__main__":
    # Initialize OAuth session
    oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
    basic_auth = HTTPBasicAuth(client_id, client_secret)

    # Get authorization URL
    authorization_url, state = oauth.authorization_url(authorization_base_url)  

    os.environ['DEBUG'] = "1"
    app.secret_key = os.urandom(24)
    app.run(host="0.0.0.0", debug=True, port=5050, ssl_context='adhoc')
