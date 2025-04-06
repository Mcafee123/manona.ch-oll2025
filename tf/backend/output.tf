output "backend_url" {
  value = azurerm_container_app.cap.ingress[0].fqdn
}