import logging
import os
from datetime import datetime, timedelta, timezone
import azure.functions as func
from azure.identity import DefaultAzureCredential
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.consumption import ConsumptionManagementClient
#from azure.developer.devcenter import DevCenterClient
from azure.core.exceptions import AzureError

# Set the logging policy to default to 'none' (NOTSET)
logging.basicConfig(level=logging.WARNING)

app = func.FunctionApp()

@app.schedule(schedule="0 */5 * * * *", arg_name="myTimer", run_on_startup=True, use_monitor=False) 
def timer_trigger(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.warning('The timer is past due!')

    try:
        # Get subscription ID from environment variable
        subscription_id = get_env_variable('AZURE_SUBSCRIPTION_ID')
        budget_name_filter = get_env_variable('AZURE_BUDGET_NAME_FILTER')
        resource_group_tag = get_env_variable('AZURE_RESOURCE_GROUP_TAG')
        resource_group_created_by_tag = get_env_variable('AZURE_RESOURCE_GROUP_CREATED_BY_TAG')
        budget_amount = float(get_env_variable('AZURE_BUDGET_AMOUNT'))
        default_mail = get_env_variable('AZURE_DEFAULT_MAIL')

        #new variables for ADE
        #devcenter_name = get_env_variable('AZURE_DEV_CENTER_NAME')
        #devcenter_project_name = get_env_variable('AZURE_DEV_CENTER_PROJECT_NAME')
        #devcenter_endpoint = get_env_variable('AZURE_DEV_CENTER_ENDPOINT')

        # Initialize Azure credentials
        credential = DefaultAzureCredential()
        
        # Initialize clients
        resource_client = ResourceManagementClient(credential, subscription_id)
        consumption_client = ConsumptionManagementClient(credential, subscription_id)
        #devcenter_client = DevCenterClient(credential, devcenter_endpoint)
        
        # Get list of resource groups with tag 'create-budget' : 'true'
        logging.warning("Fetching resource groups from ADE ...")

        resource_groups = resource_client.resource_groups.list()
        filtered_resource_groups = []

        for rg in resource_groups:
            logging.warning(f"Processing resource group: {rg.name} in {rg.location}")
            tags = rg.tags or {}
            rg_obj = {}
            if resource_group_tag in tags:
                rg_obj = {'name': rg.name, 'location': rg.location, 'id': rg.id }
                logging.warning(f"Found ADE resource group: {rg.name} in {rg.location} with ID: {rg.id}")

            if resource_group_created_by_tag in tags:
                rg_obj['owner'] = tags[resource_group_created_by_tag]
                logging.warning(f"Resource group {rg.name} created by: {tags[resource_group_created_by_tag]}")
            
            if rg_obj:
                filtered_resource_groups.append(rg_obj)

        logging.warning(f"Filtered ADE resource groups found: {len(filtered_resource_groups)}")
        resource_groups = filtered_resource_groups

        # Get budgets with matching names
        matching_budgets = []
        created_budgets = []

        # Search for budgets at resource group scope
        for rg in resource_groups:
            if not rg['id']:
                continue
            try:
                rg_budgets = consumption_client.budgets.list(scope=rg['id'])
                found_budget = False
                
                for budget in rg_budgets:
                    if budget_name_filter.lower() in budget.name.lower():
                        found_budget = True
                        matching_budgets.append({
                            'name': budget.name,
                            'amount': budget.amount,
                            'time_grain': budget.time_grain,
                            'category': budget.category,
                            'scope': rg['id'],
                            'resource_group': rg['name']
                        })
                        logging.warning(f'Found existing budget in dev environment {rg["name"]}: {budget.name}')
                
                if not found_budget:
                    owner_email = rg['owner'] if 'owner' in rg else default_mail

                    logging.warning(f'Creating a new budget for environment {rg["name"]} with owner: {owner_email or "None"}')
                    budget = create_budget_for_resource_group(
                        consumption_client, 
                        rg['id'], 
                        budget_name_filter, 
                        budget_amount,
                        owner_email=owner_email
                    )
                    created_budgets.append(budget)
        
            except AzureError as e:
                logging.debug(f'No budgets found for resource group {rg["name"]}: {str(e)}')

        logging.warning(f'Total existing budgets found: {len(matching_budgets)}')
        logging.warning(f'Total created budgets: {len(created_budgets)}')
        
        # Log summary
        logging.warning('=== SUMMARY ===')
        logging.warning(f'Resource Groups: {len(resource_groups)}')
        logging.warning(f'Existing Budgets: {len(matching_budgets)}')
        
        if matching_budgets:
            logging.warning('Budget Details:')
            for budget in matching_budgets:
                logging.warning(f'  - {budget["name"]}: {budget["amount"]} ({budget.get("resource_group", "subscription level")})')
        

    except Exception as e:
        logging.error(f'Error in timer_trigger function: {str(e)}')
        raise

    logging.warning('Python timer trigger function executed successfully.')


def create_budget_for_resource_group(consumption_client, rg_id, budget_name, amount, 
                                     owner_email=None,
                                     time_grain='Monthly',
                                     category='Cost', 
                                     start_date=None, 
                                     end_date=None):

    action_group=get_env_variable('AZURE_ACTION_GROUP_ID')

    if not start_date:
        start_date = datetime.now(timezone.utc).replace(day=1).isoformat()

    if not end_date:
        end_date = (datetime.now(timezone.utc).replace(day=1) + timedelta(days=3650)).isoformat()
   
    scope = rg_id
    
    # Prepare contact emails list - include owner email if available
    contact_emails = []
    if owner_email:
        contact_emails.append(owner_email)
        logging.warning(f'Adding owner email to budget notifications: {owner_email}')

    budget_parameters = {
        'category': category,
        'amount': amount,
        'time_grain': time_grain,
        'time_period': {
            'start_date': start_date,
            'end_date': end_date
        },
        'notifications': {
            'Actual_GreaterThan_80_Percent': {
                'enabled': True,
                'operator': 'GreaterThan',
                'threshold': 80,
                'contact_emails': contact_emails,
                'contact_roles': [],
                'contact_groups': [
                    action_group
                ]
            },
            'Actual_GreaterThan_90_Percent': {
                'enabled': True,
                'operator': 'GreaterThan',
                'threshold': 90,
                'contact_emails': contact_emails,
                'contact_roles': [],
                'contact_groups': [
                    action_group
                ]
            },'Actual_100_Percent': {
                'enabled': True,
                'operator': 'GreaterThan',
                'threshold': 100,
                'contact_emails': contact_emails,
                'contact_roles': [],
                'contact_groups': [
                    action_group
                ]
            },
        }
    }
    try:
        budget = consumption_client.budgets.create_or_update(
            scope=scope,
            budget_name=budget_name,
            parameters=budget_parameters
        )
        logging.warning(f'Created budget {budget_name} in scope {scope} with {len(contact_emails)} contact email(s)')
        return budget
    except AzureError as e:
        logging.error(f'Failed to create budget {budget_name} in scope {scope}: {str(e)}')
        return None



def get_owner_email_from_deployment(dev_center_client, dev_center_project_name, rg_id):
    """
    Get owner email from resource group deployment history.
    Azure Deployment Environments store owner information in deployment outputs or parameters.
    
    Args:
        resource_client: ResourceManagementClient instance
        resource_group_name: Name of the resource group
    
    Returns:
        Owner email or None if not found
    """
    try:
        # List all deployments in the resource group, ordered by timestamp
        environments = dev_center_client.list_all_environments(project_name=dev_center_project_name)
        found_env = [env for env in environments if env.resource_group_id() == rg_id.lower()]
        if not found_env:
            logging.warning(f"No Environments found for Dev Center: {dev_center_client.endpoint}")
            return None
        
        # Check deployments for owner information
        for env in found_env:
            logging.warning(f"Checking deployment: {env.name}, resource group id : {env.resource_group_id}")
            
            # Check deployment outputs for owner information
            if env.user:
                logging.warning(f"✓ Found owner email in environment user: {env.user}")
                return env.user

        logging.warning(f"No owner email found in deployments for dev environment: {env.name}")
        return None
        
    except Exception as e:
        logging.error(f"Error getting owner from deployments: {str(e)}")
        import traceback
        logging.error(f"Traceback: {traceback.format_exc()}")
        return None


def get_env_variable(name):
    """Get an environment variable with a default value."""
    var = os.getenv(name)
    logging.warning(f'{name} environment variable: {var}')
    
    if not var:
        logging.error(f'{name} environment variable not set')
        raise EnvironmentError(f'{name} environment variable not set')
    return var


if __name__ == "__main__":
    from dotenv import load_dotenv
    # This block is only for local testing, not needed in Azure Functions
    load_dotenv()  # Load environment variables from .env file
    logging.basicConfig(level=logging.INFO)
    class DummyTimer:
        past_due = False
    timer_trigger(DummyTimer())
    logging.warning('Local test executed successfully.')