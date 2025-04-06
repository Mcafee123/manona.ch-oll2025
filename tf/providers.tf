terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "4.9.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "4.50.0"
    }
    azapi = {
      source  = "azure/azapi"
      version = "~>1.0"
    }
  }
}
