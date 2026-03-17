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
variable "vm_size" {
  type = string
}
variable "admin_username" {
  type = string
}
variable "subnet_id" {
  type = string
}
variable "tags" {
  type = map(string)
}
variable "foundry_endpoint" {
  type = string
}
variable "foundry_api_key" {
  type      = string
  sensitive = true
}
variable "embedding_model" {
  type = string
}
variable "chat_model" {
  type = string
}
variable "db_password" {
  type      = string
  sensitive = true
}
variable "dns_label" {
  type = string
}

resource "tls_private_key" "ssh" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "local_file" "ssh_private_key" {
  content         = tls_private_key.ssh.private_key_pem
  filename        = pathexpand("~/.ssh/leann_memory")
  file_permission = "0600"
}

resource "local_file" "ssh_public_key" {
  content  = tls_private_key.ssh.public_key_openssh
  filename = pathexpand("~/.ssh/leann_memory.pub")
}

resource "azurerm_public_ip" "main" {
  name                = "pip-${var.project_name}-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  allocation_method   = "Static"
  sku                 = "Standard"
  domain_name_label   = var.dns_label
  tags                = var.tags
}

resource "azurerm_network_interface" "main" {
  name                = "nic-${var.project_name}-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  tags                = var.tags

  ip_configuration {
    name                          = "internal"
    subnet_id                     = var.subnet_id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.main.id
  }
}

locals {
  foundry_openai_base = "${trimsuffix(var.foundry_endpoint, "/")}/"

  cloud_init = templatefile("${path.module}/cloud-init.yaml", {
    admin_username   = var.admin_username
    foundry_base_url = local.foundry_openai_base
    foundry_api_key  = var.foundry_api_key
    embedding_model  = var.embedding_model
    chat_model       = var.chat_model
    db_password      = var.db_password
    vm_fqdn          = azurerm_public_ip.main.fqdn
  })
}

resource "azurerm_linux_virtual_machine" "main" {
  name                  = "vm-${var.project_name}-${var.environment}"
  location              = var.location
  resource_group_name   = var.resource_group_name
  size                  = var.vm_size
  admin_username        = var.admin_username
  network_interface_ids = [azurerm_network_interface.main.id]
  tags                  = var.tags

  admin_ssh_key {
    username   = var.admin_username
    public_key = tls_private_key.ssh.public_key_openssh
  }

  os_disk {
    name                 = "osdisk-${var.project_name}"
    caching              = "ReadWrite"
    storage_account_type = "Premium_LRS"
    disk_size_gb         = 128
  }

  source_image_reference {
    publisher = "Canonical"
    offer     = "ubuntu-24_04-lts"
    sku       = "server"
    version   = "latest"
  }

  custom_data                     = base64encode(local.cloud_init)
  disable_password_authentication = true

  identity {
    type = "SystemAssigned"
  }
}

output "fqdn" {
  value = azurerm_public_ip.main.fqdn
}

output "public_ip" {
  value = azurerm_public_ip.main.ip_address
}

output "vm_identity_principal_id" {
  value = azurerm_linux_virtual_machine.main.identity[0].principal_id
}
