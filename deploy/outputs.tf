output "vm_fqdn" {
  value = module.vm.fqdn
}

output "vm_public_ip" {
  value = module.vm.public_ip
}

output "mcp_endpoint" {
  value = "https://${module.vm.fqdn}/mcp"
}

output "db_password" {
  value     = random_password.db_password.result
  sensitive = true
}

output "ssh_command" {
  value = "ssh -i ~/.ssh/memibrium ${var.admin_username}@${module.vm.fqdn}"
}

output "models_deployed" {
  value = module.cognitive.available_models
}
