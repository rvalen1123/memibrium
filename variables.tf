variable "subscription_id" {
  type = string
}
variable "project_name" {
  type    = string
  default = "leann-memory"
}
variable "environment" {
  type    = string
  default = "prod"
}
variable "location" {
  type    = string
  default = "southcentralus"
}
variable "cognitive_location" {
  type    = string
  default = "eastus"
}
variable "vm_size" {
  type    = string
  default = "Standard_D4s_v6"
}
variable "admin_username" {
  type    = string
  default = "adminuser"
}
variable "allowed_ssh_cidrs" {
  type    = list(string)
  default = []
}
variable "embedding_model" {
  type    = string
  default = "embed-v-4-0"
}
variable "chat_model" {
  type    = string
  default = "gpt-4.1-mini"
}
variable "existing_cognitive_account_name" {
  type    = string
  default = "sector-7"
}
variable "existing_cognitive_resource_group" {
  type    = string
  default = "sector-7-rg"
}
variable "foundry_endpoint" {
  type    = string
  default = "https://sector-7.openai.azure.com/openai/v1"
}
variable "foundry_api_key" {
  type      = string
  sensitive = true
}
