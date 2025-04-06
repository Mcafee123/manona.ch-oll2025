variable "base_name" {
  type        = string
  description = "Base name for all resources."
}

variable "rg_name" {
  type        = string
  description = "Name of the resource group in which to create the resources."
}

variable "log_analytics_workspace_id" {
  type        = string
  description = "ID of the Log Analytics workspace."
}
