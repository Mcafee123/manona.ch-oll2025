provider "azurerm" {
  subscription_id = var.subscription_id
  features {}
}

provider "cloudflare" {
  api_token = var.cloudflare_api_token
}

locals {
  rg_name  = "${var.base_name}_rg"
  location = var.location
}