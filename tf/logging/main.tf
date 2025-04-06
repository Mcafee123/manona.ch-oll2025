# log analytics workspace
resource "azurerm_log_analytics_workspace" "law" {
  name                = "${var.base_name}-law"
  location            = var.location
  resource_group_name = var.rg_name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}
