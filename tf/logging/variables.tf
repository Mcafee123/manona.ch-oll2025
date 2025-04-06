variable "base_name" {
  type        = string
  description = "Base name for all resources."
}

variable "rg_name" {
  type        = string
  description = "Name of the resource group in which to create the resources."
}

variable "location" {
  type        = string
  description = "Azure region where the resources will be created."
}
