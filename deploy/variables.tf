variable "subscription_id" {
  type = string
}

variable "project_name" {
  default = "memibrium"
}

variable "environment" {
  default = "prod"
}

variable "location" {
  default     = "eastus2"
  description = "Azure region for deployment"
}

variable "vm_size" {
  default = "Standard_D2s_v3"
}

variable "admin_username" {
  default = "adminuser"
}

variable "foundry_endpoint" {
  type        = string
  description = "Azure OpenAI / Foundry endpoint URL"
}

variable "foundry_api_key" {
  type      = string
  sensitive = true
}

variable "embedding_model" {
  default = "text-embedding-3-small"
}

variable "chat_model" {
  default = "gpt-4.1-mini"
}

variable "existing_cognitive_resource_group" {
  type        = string
  description = "Resource group containing your existing Azure OpenAI resource"
}

variable "cognitive_account_name" {
  type        = string
  default     = "sector-7"
  description = "Name of your existing Azure OpenAI / Foundry resource"
}

variable "allowed_ssh_cidrs" {
  type        = list(string)
  default     = ["0.0.0.0/0"]
  description = "CIDR blocks allowed to SSH. Restrict this in production."
}
