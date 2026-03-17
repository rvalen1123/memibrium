variable "resource_group_name" {
  type = string
}
variable "location" {
  type = string
}
variable "project_name" {
  type = string
}
variable "environment" {
  type = string
}
variable "embedding_model" {
  type = string
}
variable "tags" {
  type = map(string)
}
variable "existing_cognitive_account_name" {
  type = string
}
variable "existing_cognitive_resource_group" {
  type = string
}
variable "foundry_endpoint" {
  type = string
}
variable "foundry_api_key" {
  type      = string
  sensitive = true
}

data "azurerm_cognitive_account" "sector7" {
  name                = var.existing_cognitive_account_name
  resource_group_name = var.existing_cognitive_resource_group
}

resource "azurerm_cognitive_deployment" "embedding_fallback" {
  name                 = "text-embedding-3-small"
  cognitive_account_id = data.azurerm_cognitive_account.sector7.id

  model {
    format  = "OpenAI"
    name    = "text-embedding-3-small"
    version = "1"
  }

  sku {
    name     = "Standard"
    capacity = 120
  }
}

output "endpoint" {
  value = var.foundry_endpoint
}
output "primary_key" {
  value     = var.foundry_api_key
  sensitive = true
}
output "openai_base_url" {
  value = var.foundry_endpoint
}
output "cognitive_account_id" {
  value = data.azurerm_cognitive_account.sector7.id
}
output "available_models" {
  value = {
    embedding = var.embedding_model
    chat      = "gpt-4.1-mini"
    reasoning = ["Kimi-K2-Thinking", "grok-4-fast-reasoning"]
    general   = ["Kimi-K2.5", "Mistral-Large-3"]
  }
}
