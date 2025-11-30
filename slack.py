import urllib3
import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_slack_token():
    # Retrieve Slack token from environment variable
    return os.environ.get('SLACK_TOKEN') if not None else None
    
def extract_budget_details(message):
    budget_details = {}
    
    # Replace \\n with a unique delimiter
    message = message.replace('\\n', '|||')
    
    lines = message.split('|||')
    
    for line in lines:
        parts = line.split('\n')
        for part in parts:
            key_value = part.split(': ')
            if len(key_value) == 2:
                key = key_value[0].strip()
                value = key_value[1].strip()
                budget_details[key] = value
                
    logger.info("Extracted budget details: %s", budget_details)
    return budget_details


def get_user_by_email(email):
    # Implement the logic to retrieve user ID based on email
    # Return None if user is not found
    slack_token = get_slack_token()
    api = 'https://slack.com/api/'

    http = urllib3.PoolManager()
    request_url = api + 'users.lookupByEmail?email=' + email
    r = http.request('GET', request_url, headers={"Authorization": "Bearer " + slack_token})
    resp = json.loads(r.data.decode('utf-8'))
    print(resp)
    if not resp['ok']:
        # can't find user id, return None
        return None
    return resp['user']['id']
    
def send_slack_message(channel, message):
    # Implement the logic to send a Slack message
    # This function remains unchanged from your original code
    slack_token = get_slack_token()
    api = 'https://slack.com/api/'

    http = urllib3.PoolManager()
    data = {
        'token': slack_token,
        'channel': channel,
        'as_user': True,
        'text': message,
        'link_names': True
    }
    request_url = api + 'chat.postMessage'
    r = http.request('POST', request_url, fields=data)
    if r.status != 200:
        return False
    return True

def modify_email(email):
    """
    Modifies the email to remove any characters after the '+' symbol.
    """
    if '+' in email:
        # Split the email by '+', take the first part and the domain part
        local_part, domain_part = email.split('@')
        local_part = local_part.split('+')[0]
        modified_email = f"{local_part}@{domain_part}"
        return modified_email
    
    # If the email doesn't contain '+', return the original email
    return email

def parse_amount(amount_string):
    """
    Parses the amount string and returns a float value.
    """
    if amount_string in ['N/A', None, '']:
        return None
    cleaned_string = amount_string.replace('$', '').replace(',', '').strip()
    try:
        return float(cleaned_string)
    except ValueError as e:
        logger.error(f"Could not convert string to float: '{amount_string}' - {str(e)}")
        return None

def send_message_to_webhook(message):
    """
    Sends a message to the specified Slack webhook URL.
    """
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
    if not webhook_url:
        logger.error("SLACK_WEBHOOK_URL environment variable is not set.")
        return False

    http = urllib3.PoolManager()
    payload = {
        "text": message
    }
    encoded_payload = json.dumps(payload).encode('utf-8')
    headers = {'Content-Type': 'application/json'}
    response = http.request('POST', webhook_url, body=encoded_payload, headers=headers)
    
    if response.status != 200:
        logger.error(f"Failed to send message to webhook. Status: {response.status}, Response: {response.data.decode('utf-8')}")
        return False
    return True


def format_slack_message(user_name, env_name, subscription_id, budget_details):
    """
    Formats a message to send on Slack based on budget and actual amounts.
    """
    budgeted_amount = budget_details.get('amount', None)
    actual_amount = budget_details.get('current_spend', None)

    # Emoji and message initialization
    frog_emoji = "\U0001F438"
    money_bag_emoji = "\U0001F4B0"
    warning_emoji = "\U000026A0\U0000FE0F"
    message_content = f"Hey {user_name}! {frog_emoji}\n\n"

    if actual_amount is not None and budgeted_amount is not None:
        if actual_amount >= budgeted_amount:
            # Exceeded budget
            message_content += (f"Uh oh! Your Azure Environment {env_name} budget has been exceeded! {warning_emoji}\n\n"
                                f"{money_bag_emoji} Budgeted Amount: {budgeted_amount}$\n"
                                f"{money_bag_emoji} Actual Amount: {actual_amount}$\n\n"
                                "Your account is at risk of being terminated unless you take action.\n\n")
        else:
            # Close to exceeding or under budget
            message_content += (f"Your Azure Environment {env_name} is within its budget, but keep an eye on it! {warning_emoji}\n\n"
                                f"{money_bag_emoji} Budgeted Amount: {budgeted_amount}$\n"
                                f"{money_bag_emoji} Actual Amount: {actual_amount}$\n\n")
    else:
        # Budget or actual amount not available
        message_content += "We're having trouble determining your budget or actual spending. Please check your Azure Environment directly.\n\n"

    # Suggested actions remain the same
    message_content += ("Here's what you can do:\n"
                        "1️⃣ Review and adjust your resources to manage costs.\n"
                        "2️⃣ Consider adjusting your budget settings if necessary.\n\n")
    # Add link to Cost Explorer
    cost_explorer_link = f"https://ms.portal.azure.com/#@jfildevx.onmicrosoft.com/resource/subscriptions/{subscription_id}/resourceGroups/{env_name}/costanalysis"
    message_content += f"\nYou can view your cost and usage report in <{cost_explorer_link}|Cost Analysis>.\n"                        

    return message_content

