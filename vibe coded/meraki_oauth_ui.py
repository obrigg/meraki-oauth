"""
Meraki OAuth Manager - Beautiful UI Edition

🎨 VIBE CODED ENHANCEMENT 🎨

This is an enhanced version of the basic Flask OAuth example, featuring:
- Rich library for beautiful terminal output with colors, tables, and panels
- Enhanced HTML templates with modern UI/UX
- Progress indicators and visual feedback
- Token validation and auto-refresh capabilities
- Multi-organization support with detailed statistics

⚠️ IMPORTANT NOTE:
This enhanced version is NOT meant to be the primary learning resource for OAuth.
The basic Flask example (without UI enhancements) exists separately to provide
a clean, readable introduction to OAuth concepts for developers who are new to
the OAuth flow. That basic example contains minimal code and no UI "noise",
making it ideal for understanding the core OAuth mechanics.

This "vibe coded" version demonstrates what's possible when building a 
production-ready OAuth application with better user experience, but the 
additional complexity would obscure OAuth fundamentals for newcomers.

If you're learning OAuth for the first time, start with the basic example!
If you need a production-ready OAuth manager with a great UI, you're in the right place.

⚠️ SECURITY WARNING:
This application stores OAuth tokens in CLEAR TEXT in a JSON file. This is
intentionally insecure to allow developers learning OAuth to easily examine
and understand the token structure. DO NOT USE THIS IN PRODUCTION!
Production applications should:
- Encrypt tokens at rest
- Store tokens in secure databases or key vaults
- Use OS keyring services for local storage
- Implement proper access controls

A Flask-based OAuth2 application for managing Meraki Dashboard API tokens
with an enhanced visual interface using Rich library for terminal output.
"""

import os
import json
import string
import secrets
import requests
from time import time
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth2Session
from flask import Flask, request, redirect, session, url_for, render_template
from jinja2 import Environment, FileSystemLoader, select_autoescape


# Initialize Rich console for beautiful terminal output
console = Console()

# Token storage file
# ⚠️ SECURITY WARNING: Tokens are stored in CLEAR TEXT for educational purposes!
# This allows developers learning OAuth to examine token structure and understand
# how refresh tokens work. DO NOT use this approach in production environments.
# Production apps should use encrypted storage, databases, or OS keyring services.
TOKEN_FILE = "./refresh_tokens_prod.txt"


def print_banner():
    """Display a beautiful welcome banner"""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║          🌐 Meraki OAuth Token Manager 🔐                  ║
    ║                                                           ║
    ║          Beautiful UI Edition with Rich                   ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold cyan")


def read_token_file() -> dict:
    """
    Read OAuth tokens from file with beautiful error handling
    
    Returns:
        dict: Dictionary of organization tokens
    """
    try:
        with open(TOKEN_FILE, 'r') as f:
            tokens = json.loads(f.read())
            console.print(f"✅ Successfully loaded {len(tokens)} token(s)", style="green")
            return tokens
    except FileNotFoundError:
        console.print(
            Panel.fit(
                "Token list doesn't exist. Creating a new one...",
                title="⚠️ Warning",
                border_style="yellow"
            )
        )
        with open(TOKEN_FILE, 'w') as f:
            tokens = {}
            json.dump(tokens, f)
        return tokens
    except json.JSONDecodeError:
        console.print("❌ Error: Token file is corrupted", style="bold red")
        return {}


def update_token_file(org_id: str, token: str):
    """
    Update token file with new token and display results
    
    Args:
        org_id: Organization ID
        token: OAuth token dictionary
    """
    tokens = read_token_file()
    tokens[str(org_id)] = token
    
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)
    
    # Display updated tokens in a beautiful table
    table = Table(title="📝 Updated Token List", box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("Org ID", style="cyan", no_wrap=True)
    table.add_column("Expires At", style="yellow")
    table.add_column("Status", justify="center")
    
    for o_id, tok in tokens.items():
        expires_at = datetime.fromtimestamp(tok['expires_at']).strftime('%Y-%m-%d %H:%M:%S')
        is_valid = "✅ Valid" if time() < tok['expires_at'] else "⚠️ Expired"
        table.add_row(o_id, expires_at, is_valid)
    
    console.print(table)
    console.print()


def remove_token(org_id: str):
    """
    Remove a token from the list with confirmation
    
    Args:
        org_id: Organization ID to remove
    """
    tokens = read_token_file()
    
    if str(org_id) not in tokens:
        console.print(f"❌ Organization {org_id} not found in token list", style="bold red")
        return
    
    tokens.pop(str(org_id))
    
    with open(TOKEN_FILE, 'w') as f:
        json.dump(tokens, f, indent=2)
    
    console.print(
        Panel.fit(
            f"Organization [bold cyan]{org_id}[/bold cyan] has been removed",
            title="🗑️ Token Removed",
            border_style="green"
        )
    )
    
    # Display remaining tokens
    if tokens:
        table = Table(title="📝 Remaining Tokens", box=box.ROUNDED)
        table.add_column("Org ID", style="cyan")
        table.add_column("Status", justify="center")
        
        for o_id, tok in tokens.items():
            is_valid = "✅ Valid" if time() < tok['expires_at'] else "⚠️ Expired"
            table.add_row(o_id, is_valid)
        
        console.print(table)
    else:
        console.print("📭 No tokens remaining", style="yellow")


def get_validated_token_list():
    """
    Validate all tokens and refresh expired ones with progress indication
    
    Returns:
        dict: Validated token dictionary
    """
    console.print(
        Panel.fit(
            "Validating all tokens...",
            title="🔍 Token Validation",
            border_style="blue"
        )
    )
    
    tokens = read_token_file()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Checking tokens...", total=len(tokens))
        
        for org_id, token in tokens.items():
            if is_token_still_valid(token):
                progress.update(task, advance=1)
            else:
                progress.update(task, description=f"[yellow]Refreshing token for org {org_id}...")
                new_token = refresh_the_token(token)
                tokens[org_id] = new_token
                update_token_file(org_id, new_token)
                progress.update(task, advance=1)
    
    console.print("✅ All tokens validated!", style="bold green")
    return tokens


def is_token_still_valid(token):
    """
    Check if a token is still valid
    
    Args:
        token: OAuth token dictionary
        
    Returns:
        bool: True if valid, False otherwise
    """
    org_id = token.get('organization_id', 'Unknown')
    if time() < token['expires_at']:
        console.print(f"✅ Token for org [cyan]{org_id}[/cyan] is valid", style="green")
        return True
    else:
        console.print(f"⚠️ Token for org [cyan]{org_id}[/cyan] has expired", style="yellow")
        return False


def refresh_the_token(token):
    """
    Refresh an expired token with visual feedback
    
    Args:
        token: Expired OAuth token
        
    Returns:
        dict: New token
    """
    org_id = token.get('organization_id', 'Unknown')
    
    console.print(
        Panel.fit(
            f"Refreshing token for organization: [bold cyan]{org_id}[/bold cyan]",
            title="🔄 Token Refresh",
            border_style="yellow"
        )
    )
    
    new_token = oauth.refresh_token(token_url, refresh_token=token['refresh_token'], auth=basic_auth)
    
    console.print(
        Panel.fit(
            f"Token refreshed successfully!\nNew expiry: {datetime.fromtimestamp(new_token['expires_at']).strftime('%Y-%m-%d %H:%M:%S')}",
            title="✅ Success",
            border_style="green"
        )
    )
    
    return new_token


def generate_random_string(length):
    """
    Generate a random string for OAuth state parameter
    
    Args:
        length: Length of string to generate
        
    Returns:
        str: Random string
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for i in range(length))


# Flask application setup
app = Flask(__name__)

# OAuth Configuration
client_id = os.getenv('MERAKI_CLIENT_ID', "If you're seeing this, you should set your own client ID in the environment variable MERAKI_CLIENT_ID for better security!")
client_secret = os.getenv('MERAKI_CLIENT_SECRET', "If you're seeing this, you should set your own client secret in the environment variable MERAKI_CLIENT_SECRET for better security!")
authorization_base_url = 'https://as.meraki.com/oauth/authorize'
token_url = 'https://as.meraki.com/oauth/token'
redirect_uri = 'https://localhost:5050/callback'
scope = "dashboard:general:config:read dashboard:general:config:write dashboard:licensing:config:read dashboard:licensing:telemetry:read"

# Meraki API settings
meraki_base_url = "https://api.meraki.com/api/v1/"
meraki_headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}


@app.route("/login")
def demo():
    """
    Step 1: User Authorization
    Redirect user to Meraki Dashboard for authentication
    """
    console.print(
        Panel.fit(
            "User initiated login flow",
            title="🔐 Login Request",
            border_style="blue"
        )
    )
    
    # Generate state for CSRF protection
    state = generate_random_string(20)
    session['oauth_state'] = state
    session['oauth_token'] = None
    
    console.print(f"Generated state: [dim]{state}[/dim]")
    console.print(f"Redirecting to: [link]{authorization_url}[/link]")
    
    return redirect(authorization_url)


@app.route("/callback", methods=["GET"])
def callback():
    """
    Step 2: Handle OAuth callback
    Process authorization code and retrieve access token
    """
    console.print(
        Panel.fit(
            "Processing OAuth callback...",
            title="🔄 Callback Handler",
            border_style="cyan"
        )
    )
    
    # Check for errors from auth server
    if "error" in request.args.keys():
        error = request.args["error"]
        error_description = request.args["error_description"]
        
        console.print(
            Panel.fit(
                f"[bold red]Error:[/bold red] {error}\n[yellow]Description:[/yellow] {error_description}",
                title="❌ Authentication Error",
                border_style="red"
            )
        )
        
        # Render error template
        return render_template('error.html', error=error, error_description=error_description)
    
    # Exchange authorization code for token
    authorization_response = request.url
    token = oauth.fetch_token(
        token_url,
        authorization_response=authorization_response,
        client_secret=client_secret,
        client_id=client_id
    )
    
    org_id = token['organization_id']
    
    console.print(
        Panel.fit(
            f"[bold green]Token obtained successfully![/bold green]\n"
            f"Organization ID: [cyan]{org_id}[/cyan]\n"
            f"Expires: {datetime.fromtimestamp(token['expires_at']).strftime('%Y-%m-%d %H:%M:%S')}",
            title="✅ Success",
            border_style="green"
        )
    )
    
    update_token_file(org_id, token)
    return redirect(url_for('.networks'))


@app.route("/networks", methods=["GET"])
def networks():
    """
    Step 3: Fetch protected resources
    Display networks from all authorized organizations
    """
    console.print(
        Panel.fit(
            "Fetching networks from all organizations...",
            title="🌐 Network Discovery",
            border_style="blue"
        )
    )
    
    tokens = get_validated_token_list()
    networks_by_org = {}
    total_networks = 0
    valid_tokens = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Loading networks...", total=len(tokens))
        
        for org_id, token in tokens.items():
            progress.update(task, description=f"[cyan]Fetching from org {org_id}...")
            url = meraki_base_url + 'organizations/' + org_id + '/networks'
            meraki_headers['Authorization'] = 'Bearer ' + token['access_token']
            
            try:
                networks_data = requests.get(url, headers=meraki_headers).json()
                
                if type(networks_data) == list:
                    networks_by_org[org_id] = networks_data
                    total_networks += len(networks_data)
                    valid_tokens += 1
                    console.print(f"  ✅ Found {len(networks_data)} network(s) in org {org_id}", style="green")
                else:
                    networks_by_org[org_id] = [{
                        'error': 'Could not fetch networks. Token may need refresh.',
                        'name': 'Error',
                        'id': 'N/A',
                        'productTypes': [],
                        'timeZone': 'N/A'
                    }]
                    console.print(f"  ⚠️ Error fetching networks from org {org_id}", style="yellow")
            except Exception as e:
                networks_by_org[org_id] = [{
                    'error': f'Exception: {str(e)}',
                    'name': 'Error',
                    'id': 'N/A',
                    'productTypes': [],
                    'timeZone': 'N/A'
                }]
                console.print(f"  ❌ Exception for org {org_id}: {str(e)}", style="red")
            
            progress.update(task, advance=1)
    
    # Display summary in terminal
    summary_table = Table(title="📊 Networks Summary", box=box.DOUBLE_EDGE)
    summary_table.add_column("Metric", style="cyan", no_wrap=True)
    summary_table.add_column("Value", style="green", justify="right")
    summary_table.add_row("Total Organizations", str(len(tokens)))
    summary_table.add_row("Total Networks", str(total_networks))
    summary_table.add_row("Valid Tokens", str(valid_tokens))
    console.print(summary_table)
    
    # Prepare stats for template
    stats = {
        'total_orgs': len(tokens),
        'total_networks': total_networks,
        'valid_tokens': valid_tokens
    }
    
    return render_template('networks.html', networks_by_org=networks_by_org, stats=stats)


@app.route("/", methods=["GET"])
def landing():
    """
    Landing page with beautiful UI
    """
    return render_template('landing.html')


@app.route("/delete_org/<org_id>", methods=["GET"])
def delete_token(org_id):
    """
    Delete an organization token from the list
    
    Args:
        org_id: Organization ID to remove
    """
    console.print(
        Panel.fit(
            f"Request to delete token for org: [cyan]{org_id}[/cyan]",
            title="🗑️ Delete Request",
            border_style="yellow"
        )
    )
    
    try:
        remove_token(org_id)
        return redirect(url_for('.networks'))
    except KeyError:
        console.print(f"❌ No token found for organization {org_id}", style="bold red")
        return f"No token found for organization {org_id}.", 404
    except Exception as e:
        console.print(f"❌ Error occurred: {str(e)}", style="bold red")
        return f"An error occurred: {str(e)}", 500


if __name__ == "__main__":
    # Display welcome banner
    print_banner()
    
    # Initialize OAuth session
    console.print("🔧 Initializing OAuth session...", style="bold blue")
    oauth = OAuth2Session(client_id, redirect_uri=redirect_uri, scope=scope)
    basic_auth = HTTPBasicAuth(client_id, client_secret)
    
    # Get authorization URL
    authorization_url, state = oauth.authorization_url(authorization_base_url)
    
    console.print("✅ OAuth session initialized", style="bold green")
    
    # Display configuration
    config_table = Table(title="⚙️ Configuration", box=box.ROUNDED, show_header=False)
    config_table.add_column("Setting", style="cyan", no_wrap=True)
    config_table.add_column("Value", style="yellow")
    config_table.add_row("Client ID", client_id[:20] + "..." if len(client_id) > 20 else client_id)
    config_table.add_row("Redirect URI", redirect_uri)
    config_table.add_row("Server Host", "0.0.0.0")
    config_table.add_row("Server Port", "5050")
    config_table.add_row("SSL Context", "adhoc")
    console.print(config_table)
    
    # Start Flask application
    console.print(
        Panel.fit(
            "[bold green]Starting Flask server...[/bold green]\n"
            "Access the application at: [link]https://localhost:5050[/link]\n"
            "Login at: [link]https://localhost:5050/login[/link]",
            title="🚀 Server Starting",
            border_style="green"
        )
    )
    
    os.environ['DEBUG'] = "1"
    app.secret_key = os.urandom(24)
    app.run(host="0.0.0.0", debug=True, port=5050, ssl_context='adhoc')
