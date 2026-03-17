terraform {
  required_providers {
    azurerm = { source = "hashicorp/azurerm", version = "~> 4.0" }
    random  = { source = "hashicorp/random", version = "~> 3.0" }
    tls     = { source = "hashicorp/tls", version = "~> 4.0" }
  }
}

provider "azurerm" {
  features {}
  subscription_id = var.subscription_id
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project_name}-${var.environment}"
  location = var.location
  tags     = local.common_tags
}

module "network" {
  source              = "./modules/network"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  project_name        = var.project_name
  environment         = var.environment
  tags                = local.common_tags
}

module "cognitive" {
  source              = "./modules/cognitive"
  resource_group_name = var.existing_cognitive_resource_group
  cognitive_name      = var.cognitive_account_name
  embedding_model     = var.embedding_model
}

module "vm" {
  source              = "./modules/vm"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  project_name        = var.project_name
  environment         = var.environment
  vm_size             = var.vm_size
  admin_username      = var.admin_username
  subnet_id           = module.network.subnet_id
  tags                = local.common_tags
  foundry_endpoint    = var.foundry_endpoint
  foundry_api_key     = var.foundry_api_key
  embedding_model     = var.embedding_model
  chat_model          = var.chat_model
  db_password         = random_password.db_password.result
  dns_label           = "${var.project_name}-${var.environment}"
}

resource "random_password" "db_password" {
  length  = 32
  special = false
}

locals {
  common_tags = {
    project     = var.project_name
    environment = var.environment
    managed_by  = "terraform"
  }
}
