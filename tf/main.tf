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

# Logging-Module
module "Logging" {
  source = "./logging"
  # variables
  base_name = var.base_name
  rg_name   = local.rg_name
  location  = local.location
}

# Containers Module
module "Containers" {
  source = "./containers"
  # variables
  base_name                  = var.base_name
  rg_name                    = local.rg_name
  log_analytics_workspace_id = module.Logging.log_analytics_workspace_id
  location                   = local.location

  depends_on = [module.Logging]
}

# Backend Module
module "Backend" {
  source = "./backend"

  providers = {
    cloudflare = cloudflare
  }
  # variables
  base_name   = var.base_name
  rg_name     = local.rg_name
  domain_name = var.backend_domain_name

  cloudflare_zone_id   = var.cloudflare_zone_id
  cloudflare_api_token = var.cloudflare_api_token

  container_app_environment_id = module.Containers.container_app_environment_id
  acr_identity_id              = module.Containers.acr_identity_id
  acr_login_server             = module.Containers.acr_login_server
  image_name                   = "backend"

  client_api_key = var.client_api_key
  openai_api_key = var.openai_api_key

  depends_on = [module.Containers]
}

# Frontend Module
module "Frontend" {
  source = "./frontend"

  providers = {
    cloudflare = cloudflare
  }
  # variables
  base_name   = var.base_name
  rg_name     = local.rg_name
  domain_name = var.frontend_domain_name

  cloudflare_zone_id   = var.cloudflare_zone_id
  cloudflare_api_token = var.cloudflare_api_token

  container_app_environment_id        = module.Containers.container_app_environment_id
  container_app_environment_static_ip = module.Containers.container_app_environment_static_ip
  acr_identity_id                     = module.Containers.acr_identity_id
  acr_login_server                    = module.Containers.acr_login_server
  image_name                          = "frontend"
  backend_domain_name                 = "api.manona.ch"

  depends_on = [module.Containers]
}
