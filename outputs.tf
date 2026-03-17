output "vm_fqdn" {
  value = module.vm.fqdn
}

output "vm_public_ip" {
  value = module.vm.public_ip
}

output "mcp_endpoint" {
  value = "https://${module.vm.fqdn}/mcp"
}

output "mcp_bearer_token" {
  value     = random_password.mcp_token.result
  sensitive = true
}

output "foundry_endpoint" {
  value = var.foundry_endpoint
}

output "models_deployed" {
  value = module.cognitive.available_models
}

output "ssh_command" {
  value = "ssh -i ~/.ssh/leann_memory ${var.admin_username}@${module.vm.fqdn}"
}

output "claude_code_mcp_config" {
  value = jsonencode({
    mcpServers = {
      "leann-memory" = {
        type = "http"
        url  = "https://${module.vm.fqdn}/mcp"
        headers = {
          Authorization = "Bearer <run: terraform output -raw mcp_bearer_token>"
        }
      }
    }
  })
}
