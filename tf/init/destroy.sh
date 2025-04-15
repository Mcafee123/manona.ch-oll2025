#!/bin/sh

# author: martin@affolter.net

. ../env.sh

terraform refresh

storage_account_id=$(terraform output -raw storage_account_id)
echo "storage_account_id: $storage_account_id"

echo "Delete Lock..."
az lock delete --name $delete_lock_name \
  --resource "$storage_account_id"

echo "Delete terraform state..."
terraform destroy
