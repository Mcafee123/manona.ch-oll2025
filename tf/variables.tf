variable "subscription_id" {
  type        = string
  description = "Azure subscription ID."
}

variable "base_name" {
  type        = string
  description = "Base name for all resources."
}

variable "location" {
  type        = string
  description = "location of resources."
}

variable "restart_var" {
  type        = string
  description = "Dummy restart environment variable name."
}

# CLoudflare
variable "cloudflare_zone_id" {
  type        = string
  description = "Cloudflare zone id."
}

variable "cloudflare_api_token" {
  type        = string
  description = "Cloudflare API token."
  sensitive   = true
}
