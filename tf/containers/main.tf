data "azurerm_resource_group" "rg" {
  name = var.rg_name
}

# container registry
resource "azurerm_container_registry" "acr" {
  name                = "${var.base_name}acr"
  resource_group_name = var.rg_name
  location            = data.azurerm_resource_group.rg.location
  sku                 = "Basic"
  admin_enabled       = true
}

# container app environment
resource "azurerm_container_app_environment" "cae" {
  name                       = "${var.base_name}-cae"
  location                   = data.azurerm_resource_group.rg.location
  resource_group_name        = var.rg_name
  log_analytics_workspace_id = var.log_analytics_workspace_id
}

# user managed identity for container registry
resource "azurerm_user_assigned_identity" "acr_identity" {
  location            = data.azurerm_resource_group.rg.location
  name                = "${var.base_name}_acr_identity"
  resource_group_name = var.rg_name
}

# acrpull role for container registry identity
resource "azurerm_role_assignment" "acr_identity_role" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "acrpull"
  principal_id         = azurerm_user_assigned_identity.acr_identity.principal_id
  depends_on = [
    azurerm_user_assigned_identity.acr_identity
  ]
}