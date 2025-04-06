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
    working_dir = "./../src/frontend/"
    command = "./containerize.sh ${var.acr_login_server} ${local.image_name_full}"
  }
}

# # get the version dynamically from the container registry
# data "external" "version" {
#   program = ["bash", "-c", <<EOF
#     version=$(az acr repository show-tags -n ${var.acr_login_server} --repository ${local.image_name_full} --top 1 --orderby time_desc -o tsv)
#     echo "{\"version\": \"$version\"}"
#   EOF
#   ]

#   depends_on = [ null_resource.docker-buildx ]
# }

resource "azurerm_container_app" "cap" {
  name                         = "${var.base_name}-frontend"
  container_app_environment_id = var.container_app_environment_id
  resource_group_name          = var.rg_name
  revision_mode                = "Single"

  # depends_on = [null_resource.docker-buildx, data.external.version]

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
    target_port                = 80
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
      name   = "frontend"
      image  = "nginx:1.27.4-alpine-slim"
      cpu    = 1
      memory = "2Gi"
      # command = ["/opt/keycloak/bin/kc.sh", "start", "--optimized"] # "start", "--optimized" | "start-dev"

      # volume_mounts {
      #   name = "certs-volume"
      #   path = "/etc/ssl/certs"
      # }
    }

#     volume {
#       name = "certs-volume"
#       storage_name = var.storage_name
#       storage_type = "AzureFile"
#     }
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
  content = var.container_app_environment_static_ip
  type    = "A"
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
