#!/bin/sh

# author: martin@affolter.net

terraform init

. ../env.sh

terraform apply -auto-approve

subscription_id=$(terraform output -raw subscription_id)
rg_name=$(terraform output -raw rg_name)
storage_account_id=$(terraform output -raw storage_account_id)
storage_account_name=$(terraform output -raw storage_account_name)

az lock create --name $delete_lock_name \
--lock-type CanNotDelete \
--resource "$storage_account_id" \
--notes "Deny delete lock for storage account"

echo "terraform {
  backend \"azurerm\" {
    resource_group_name  = \"${rg_name}\"
    storage_account_name = \"${storage_account_name}\"
    container_name       = \"state\"
    key                  = \"prod.terraform.tfstate\"
  }
}" > ../backend.tf


yellow "../backend.tf created"

pushd .

cd ..

# terraform init -migrate-state

popd