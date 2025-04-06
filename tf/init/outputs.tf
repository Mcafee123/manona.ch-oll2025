output "subscription_id" {
  value = var.subscription_id
  description = "The subscription ID."
}

output "rg_name" {
  value = azurerm_resource_group.rg.name
  description = "The name of the resource group."
}

output "storage_account_id" {
  value = azurerm_storage_account.tfstate.id
  description = "The ID of the storage account."
}

output "storage_account_name" {
  value = azurerm_storage_account.tfstate.name
  description = "The name of the storage account."
}