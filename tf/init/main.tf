terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "4.9.0"
    }
  }
}

provider "azurerm" {
  subscription_id = var.subscription_id
  features {}
}

# resource group
resource "azurerm_resource_group" "rg" {
  location = var.location
  name     = "${var.base_name}_rg"
}

# storage account
resource "azurerm_storage_account" "tfstate" {
  name                     = "${var.base_name}tfstate"
  resource_group_name      = azurerm_resource_group.rg.name
  location                 = azurerm_resource_group.rg.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
  blob_properties {
    delete_retention_policy {
      days = 14  # Minimum recommended retention period
    }
    versioning_enabled = true
  }
}

resource "azurerm_storage_container" "state" {
  name                  = "state"
  storage_account_id    = azurerm_storage_account.tfstate.id
  container_access_type = "private"
}
