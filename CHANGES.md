# Changes Summary: Owner Email Notifications for Budget Alerts

## Overview
Added functionality to automatically include environment owners' email addresses in budget alert notifications for Azure Deployment Environment (ADE) resource groups.

## Changes Made

### 1. Dependencies (`requirements.txt`)
- **Added**: `azure-mgmt-devcenter` - Azure Dev Center Management SDK for accessing deployment environment information

### 2. Main Function Code (`function_app.py`)

#### New Imports
```python
from azure.mgmt.devcenter import DevCenterManagementClient
```

#### New Functions Added

##### `get_owner_email_from_deployment(resource_client, resource_group_name)`
- **Purpose**: Extract owner email from deployment history
- **How it works**:
  - Lists all deployments in the resource group (up to 50 recent deployments)
  - Sorts deployments by timestamp (oldest first) to prioritize creation deployment
  - Searches deployment outputs for owner fields: `owner`, `ownerEmail`, `owner_email`, `creatorEmail`, `userEmail`
  - Searches deployment parameters for owner fields: `owner`, `ownerEmail`, `owner_email`, `creatorEmail`, `principalName`
  - Checks `provisioned_by` field if available
  - Validates that values contain `@` to confirm they're emails
  - Returns the email address or `None` if not found
  - Includes detailed logging of deployments, outputs, and parameters for troubleshooting

##### `get_environment_owner_email(credential, subscription_id, resource_group_name, devcenter_name, project_name)`
- **Purpose**: Get owner email from Azure Deployment Environment using Dev Center SDK
- **Status**: Prepared for future use with Dev Center data plane API
- **Note**: Currently focuses on resource group tag-based approach as primary method

##### `get_environment_owner_from_user_environments(credential, subscription_id, resource_group_name, devcenter_name, project_name)`
- **Purpose**: Alternative method to retrieve owner through Dev Center project listing
- **Status**: Framework for future enhancement with Dev Center data plane SDK

#### Modified Functions

##### `create_budget_for_resource_group()`
- **New Parameter**: `owner_email=None`
- **Changes**:
  - Accepts optional owner email parameter
  - Adds owner email to `contact_emails` list in budget notifications
  - Logs when owner email is added to notifications
  - Budget creation succeeds with or without owner email

##### `timer_trigger()`
- **Changes in resource group processing**:
  - Calls `get_owner_email_from_deployment()` for each ADE resource group
  - Retrieves deployment history to extract owner information
  - Stores owner email in resource group dictionary: `{'name': ..., 'location': ..., 'id': ..., 'owner_email': ...}`
  - Logs owner email status for each resource group
  
- **Changes in budget creation**:
  - Extracts owner email from resource group dictionary
  - Passes owner email to `create_budget_for_resource_group()`
  - Logs budget creation with owner information

### 3. Test Script (`test_owner_lookup.py`)
- **Purpose**: Test and verify owner email lookup functionality from deployments
- **Features**:
  - Lists all ADE resource groups
  - Displays deployment history for each resource group (up to 5 recent deployments)
  - Shows deployment outputs and parameters
  - Indicates timestamp and provisioning status
  - Shows which owner emails were found and from which source (outputs/parameters)
  - Provides diagnostic output for troubleshooting

### 4. Documentation (`README.md`)
- **New Section**: "Owner Email Notifications"
  - Explains how the feature works
  - Lists supported tag names
  - Provides testing instructions
  - Documents how to set owner tags
  - Describes fallback behavior

## How It Works

### Workflow
1. Function runs on schedule (every 5 minutes)
2. Retrieves resource groups tagged with ADE identifier
3. For each resource group:
   - Retrieves deployment history (up to 50 recent deployments)
   - Searches deployment outputs for owner email
   - Searches deployment parameters for owner email
   - Checks provisioning metadata for owner identity
   - Extracts owner email if available
   - Checks if budget exists
   - If budget doesn't exist, creates new budget with owner email in notifications
4. Owner receives budget alert emails along with Action Group

### Deployment-Based Approach Benefits
- **Automatic**: No manual tagging required - uses deployment metadata
- **Accurate**: Owner information comes directly from deployment source
- **Template-Driven**: Controlled via infrastructure-as-code templates
- **Auditable**: Deployment history provides clear trail of ownership
- **Standard**: Leverages Azure's native deployment tracking

### Notification Configuration
When owner email is found, the budget notification includes:
- **Threshold**: 80% of budget amount
- **Operator**: GreaterThan
- **Contact Emails**: [owner@example.com]
- **Contact Groups**: [Action Group ID]

## Environment Variables
No new required environment variables. Existing variables for Dev Center are already configured:
- `AZURE_DEV_CENTER_NAME`
- `AZURE_DEV_CENTER_PROJECT_NAME`

## Backward Compatibility
- ✅ Fully backward compatible
- ✅ Works with or without owner email
- ✅ No breaking changes to existing functionality
- ✅ Graceful fallback if owner email not found

## Testing
Run the test script to verify owner email detection:
```zsh
python test_owner_lookup.py
```

## Future Enhancements
- Integration with Dev Center data plane API for direct environment owner lookup
- Support for multiple notification recipients per environment
- Configurable notification thresholds per owner
- Owner email validation against Azure AD

## Rollback
If needed, the changes can be easily rolled back by:
1. Removing the `owner_email` parameter from budget creation calls
2. Reverting to empty `contact_emails` list
3. No data or budget modifications required
