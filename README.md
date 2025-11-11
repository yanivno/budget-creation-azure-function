# Budget Creation Function

This project is an Azure Functions app written in Python. It is designed to automate budget creation tasks, likely integrating with JFrog or related services.

## Project Structure

- `function_app.py` - Main Azure Function entry point.
- `host.json` - Global configuration options for all functions.
- `local.settings.json` - Local app settings for development (not for production use).
- `requirements.txt` - Python dependencies.

## Prerequisites

- Python 3.8 or later
- [Azure Functions Core Tools](https://docs.microsoft.com/azure/azure-functions/functions-run-local)
- [Azure CLI](https://docs.microsoft.com/cli/azure/install-azure-cli) (optional, for deployment)
- An Azure subscription

## Environment Variables

Ensure the following environment variables are set in `local.settings.json` or your Azure Function App settings:
os.environ['AZURE_SUBSCRIPTION_ID'] = 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx' # Azure Subscription ID
os.environ['AZURE_BUDGET_NAME_FILTER'] = 'default-budget' # Budget name filter to match existing budgets
os.environ['AZURE_RESOURCE_GROUP_TAG'] = 'dev-environment' # Resource group tag to filter resources
os.environ['AZURE_BUDGET_AMOUNT'] = '400' # Budget amount in USD 
os.environ['AZURE_ACTION_GROUP_ID'] = '/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/microsoft.insights/actiongroups/{actionGroupName}' # Action group ID for budget alerts
os.environ['AZURE_DEV_CENTER_NAME'] = 'my-devcenter' # Azure Dev Center name
os.environ['AZURE_DEV_CENTER_PROJECT_NAME'] = 'my-project' # Azure Dev Center project name

or create a `.env` file in the root directory with the following content:

```plaintext
AZURE_SUBSCRIPTION_ID='xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx'
AZURE_BUDGET_NAME_FILTER='default-budget'
AZURE_RESOURCE_GROUP_TAG='dev-environment'
AZURE_BUDGET_AMOUNT='400'
AZURE_ACTION_GROUP_ID='/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/microsoft.insights/actiongroups/{actionGroupName}'
AZURE_DEV_CENTER_NAME='my-devcenter'
AZURE_DEV_CENTER_PROJECT_NAME='my-project'
AZURE_RESOURCE_GROUP_CREATED_BY_TAG='created_by'
AZURE_DEFAULT_MAIL='default@example.com'
```


## Setup

1. **Clone the repository:**
   ```zsh
   git clone <repository-url>
   cd budget-creation-azure-function
   ```

2. **Create and activate a virtual environment:**
   ```zsh
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies:**
   ```zsh
   pip3 install -r requirements.txt
   ```

## Running Locally

1. **Start the Azure Functions host:**
   ```zsh
   func host start
   ```

2. The function will be available at the local URL provided in the terminal output.

## Configuration

- Update `local.settings.json` with your local development settings and secrets.
- Do not commit sensitive information to source control.

## Deployment

create a new Azure Function App in your Azure subscription and deploy the function using the Azure CLI or Azure Portal.

```bash
# Function app and storage account names must be unique.

# Variable block
location="swedencentral"
resourceGroup="budget-function-app-rg"
storage="budgetfunctionappstorage"
functionApp="budget-function-app"
skuStorage="Standard_LRS"
pythonVersion="3.12"

# Create a resource group
echo "Creating $resourceGroup in "$location"..."
az group create --name $resourceGroup --location "$location"

# Create an Azure storage account in the resource group.
echo "Creating $storage"az functionapp config appsettings set \
  --name <function-app-name> \
  --resource-group <resource-group> \
  --settings AzureWebJobsStorage="DefaultEndpointsProtocol=https;AccountName=<your-storage-account>;AccountKey=<your-key>;EndpointSuffix=core.windows.net"
az storage account create --name $storage --location "$location" --resource-group $resourceGroup --sku $skuStorage

# Create a serverless python function app in the resource group.
echo "Creating $functionApp"
az functionapp create --name $functionApp --storage-account $storage --flexconsumption-location "$location" --resource-group $resourceGroup --os-type Linux --runtime python --runtime-version $pythonVersion
```

## Azure Function Managed Identity
This function uses Azure Managed Identity for authentication. Ensure that the function app has a system-assigned managed identity enabled and that it has the necessary permissions to create budgets in Azure Cost Management : 
- **Contributor** – Can create, modify, or delete resources in the subscription.
- **Cost Management Contributor** – Can create, modify, or delete budgets.

## Owner Email Notifications

The function automatically adds the environment owner's email to budget alert notifications. This feature works by:

1. **Deployment History Lookup**: When processing each Azure Deployment Environment (ADE) resource group, the function retrieves the deployment history to find owner information.

2. **Owner Information Sources**: The function searches for owner email in deployment metadata:
   - **Deployment Outputs**: Checks output values for keys like `owner`, `ownerEmail`, `owner_email`, `creatorEmail`, `userEmail`
   - **Deployment Parameters**: Checks parameter values for keys like `owner`, `ownerEmail`, `owner_email`, `creatorEmail`, `principalName`
   - **Provisioned By**: Checks the `provisioned_by` field if available

3. **Email Validation**: The function validates that values contain an `@` symbol to ensure they're email addresses.

4. **Budget Notification**: If an owner email is found, it's automatically added to the `contact_emails` list in the budget alert notification configuration.

### Testing Owner Email Lookup

You can test the owner email lookup functionality using the provided test script:

```zsh
python test_owner_lookup.py
```

This script will:
- List all ADE resource groups (filtered by the configured tag)
- Display deployment history for each resource group
- Show deployment outputs and parameters
- Indicate which owner emails were found or not found

### How Deployment-Based Owner Lookup Works

The function retrieves owner information from deployment metadata automatically created when Azure Deployment Environments are provisioned. The deployment typically contains:

1. **Deployment Outputs**: Values exported by the deployment template (Bicep/ARM)
2. **Deployment Parameters**: Input parameters used during deployment
3. **Provisioning Metadata**: Information about who initiated the deployment

No additional configuration is needed if your deployment templates already include owner information in outputs or parameters.

### Fallback Behavior

If no owner email is found in the resource group tags:
- The budget will still be created successfully
- Notifications will be sent to the Action Group only
- A warning message will be logged indicating that no owner email was found

## License

[MIT](LICENSE)