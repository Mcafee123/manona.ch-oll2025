locals {
  image_name_full = "${var.base_name}-${var.image_name}"
}

# create the docker image and push it to the container registry
# necessary to use buildx on mac os with amd-architecture to build arm images
resource "null_resource" "docker-buildx" {
  
    # this trigger makes sure that the script is executed every time
  triggers = {
    timestamp = "${timestamp()}"
  }
  
  provisioner "local-exec" {
    # call buildx script
    working_dir = "./../src/backend/"
    command = "./containerize.sh ${var.acr_login_server} ${local.image_name_full}"
  }
}

# get the version dynamically from the container registry
data "external" "version" {
  program = ["bash", "-c", <<EOF
    version=$(az acr repository show-tags -n ${var.acr_login_server} --repository ${local.image_name_full} --top 1 --orderby time_desc -o tsv)
    echo "{\"version\": \"$version\"}"
  EOF
  ]

  depends_on = [ null_resource.docker-buildx ]
}

resource "azurerm_storage_share" "configshare" {
  name               = "configshare"
  storage_account_id = var.storage_account_id
  quota              = 1
}

resource "azurerm_container_app_environment_storage" "config_volume" {
  name                         = "configsvolume"
  container_app_environment_id = var.container_app_environment_id
  account_name                 = var.storage_account_name
  share_name                   = azurerm_storage_share.configshare.name
  access_key                   = var.storage_account_key
  access_mode                  = "ReadOnly"
}

resource "azurerm_container_app" "cap" {
  name                         = "${var.base_name}-backend"
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = var.rg_name
  revision_mode                = "Single"

  depends_on = [null_resource.docker-buildx, data.external.version]

  identity {
    type         = "UserAssigned"
    identity_ids = [var.acr_identity_id]
  }

  registry {
    server   = var.acr_login_server
    identity = var.acr_identity_id
  }

  ingress {
    external_enabled           = true
    target_port                = 8000
    transport                  = "http"
    traffic_weight {
      percentage = 100
      latest_revision = true
    }
  }
  template {
    
    min_replicas = 1
    max_replicas = 1
    
    container {
      name   = "backend"
      image  = "${var.acr_login_server}/${local.image_name_full}:${data.external.version.result.version}"
      cpu    = 1
      memory = "2Gi"
      # command = ["/opt/keycloak/bin/kc.sh", "start", "--optimized"] # "start", "--optimized" | "start-dev"

      env {
        name = "CLIENT_API_KEY"
        value = var.client_api_key
      }

      env {
        name = "OPENAI_API_KEY"
        value = var.openai_api_key
      }
      
      volume_mounts {
        name = "config"
        path = "/app/prompts"
      }
    }

    volume {
      name = "config"
      storage_name = azurerm_container_app_environment_storage.config_volume.name
      storage_type = "AzureFile"
    }
  }
}

resource "cloudflare_record" "asuid" {
  zone_id = var.cloudflare_zone_id
  name    = "asuid.${var.domain_name}"
  content = "\"${azurerm_container_app.cap.custom_domain_verification_id}\""
  type    = "TXT"
}

resource "cloudflare_record" "cname" {
  zone_id = var.cloudflare_zone_id
  name    = var.domain_name
  content = azurerm_container_app.cap.ingress[0].fqdn
  type    = "CNAME"
}

resource "null_resource" "add_custom_ssl_domain" {
  triggers = {
    timestamp = "${timestamp()}"
  }

  provisioner "local-exec" {
    command = <<EOF
    ./add_custom_domain.sh "${var.container_app_environment_id}" "${azurerm_container_app.cap.name}" "${var.domain_name}"
    EOF
  }

  depends_on = [ azurerm_container_app.cap, cloudflare_record.cname, cloudflare_record.asuid ]
}
