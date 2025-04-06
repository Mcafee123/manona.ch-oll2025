#!/bin/sh

# author: martin@affolter.net

# Variables
CONTAINER_APP_ENV_ID="$1"
CONTAINER_APP_NAME="$2"
DOMAIN_NAME="$3"

# Define the maximum number of retries
MAX_RETRIES=50
# Define the sleep duration between retries (in seconds)
SLEEP_DURATION=30

# Parameter validation
if [ -z "$CONTAINER_APP_ENV_ID" ] || [ -z "$CONTAINER_APP_NAME" ] || [ -z "$DOMAIN_NAME" ]; then
  echo "Error: Missing required parameters."
  echo "Usage: $0 <container-app-env-id> <container-app-env-name> <resource-group> <domain-name> <file-path>"
  echo "  <container-app-env-id>    The id of the Azure Container App Environment."
  echo "  <domain-name>             The custom domain name to check or create a certificate for."
  echo "  <file-path>               The name of the local file to store the certificate id in."
  exit 1
fi

# get resource group name
RESOURCE_GROUP=$(echo "$CONTAINER_APP_ENV_ID" | sed -n 's|.*/resourceGroups/\([^/]*\)/.*|\1|p')
echo "Resource Group: $RESOURCE_GROUP"
CONTAINER_APP_ENV_NAME=$(az resource show --ids "$CONTAINER_APP_ENV_ID" --query "name" -o tsv)
echo "Container App Environment Name: $CONTAINER_APP_ENV_NAME"

# Check if the hostname is already bound
BOUND_HOSTNAME=$(az containerapp hostname list \
  --name "$CONTAINER_APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --query "[?name=='$DOMAIN_NAME'].bindingType" \
  -o tsv)

echo "BOUND_HOSTNAME: $BOUND_HOSTNAME"

if [ ! -n "$BOUND_HOSTNAME" ]; then
  echo "Create hostname '$DOMAIN_NAME'..."
  # Add the custom domain
  attempt=0   # Retry counter
  success=0
  while (( attempt < MAX_RETRIES )); do  
    az containerapp hostname add \
      --name "$CONTAINER_APP_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --hostname "$DOMAIN_NAME"

    exit_code=$?

    if [ $exit_code -eq 0 ]; then
        # If the command succeeds, break the loop
        echo "Hostname '$DOMAIN_NAME' successfully created in container app '$CONTAINER_APP_NAME'"
        success=1
        break
    else
        # If the command fails, increment the retry counter
        echo "Command failed with exit code $exit_code. Retrying in $SLEEP_DURATION seconds..."
        attempt=$((attempt + 1))
        sleep $SLEEP_DURATION
    fi
  done

  if [ $success -eq 0 ]; then
    echo "Failed to create hostname '$DOMAIN_NAME'. Please check the error above."
    exit 1
  fi
fi

if [ ! -n "$BOUND_HOSTNAME" ] || [ "$BOUND_HOSTNAME" != "SniEnabled" ]; then

  echo "Hostname '$DOMAIN_NAME' is not bound. Binding it now..."
  
  # Bind the hostname with the certificate
  attempt=0   # Retry counter
  success=0
  while (( attempt < MAX_RETRIES )); do  
    az containerapp hostname bind \
      --name "$CONTAINER_APP_NAME" \
      --resource-group "$RESOURCE_GROUP" \
      --hostname "$DOMAIN_NAME" \
      --environment "$CONTAINER_APP_ENV_NAME" \
      --validation-method "CNAME"

    exit_code=$?

    if [ $exit_code -eq 0 ]; then
        # If the command succeeds, break the loop
        echo "Hostname '$DOMAIN_NAME' successfully bound to the container app '$CONTAINER_APP_NAME'"
        success=1
        break
    else
        # If the command fails, increment the retry counter
        echo "Command failed with exit code $exit_code. Retrying in $SLEEP_DURATION seconds..."
        attempt=$((attempt + 1))
        sleep $SLEEP_DURATION
    fi
  done

  if [ $success -eq 0 ]; then
    echo "Failed to bind hostname '$DOMAIN_NAME' to the container app '$CONTAINER_APP_NAME'. Please check the error above."
    exit 1
  fi
fi
