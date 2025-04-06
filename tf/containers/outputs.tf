output "container_app_environment_id" {
  value = azurerm_container_app_environment.cae.id
}

output "acr_identity_id" {
  value = azurerm_user_assigned_identity.acr_identity.id
}

output "acr_login_server" {
  value = azurerm_container_registry.acr.login_server
}

output "container_app_environment_static_ip" {
  value = azurerm_container_app_environment.cae.static_ip_address
}