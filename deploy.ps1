# =============================================================================
# deploy.ps1 — Always-On Memory Server Deployment
# =============================================================================
# Suppress profile errors (fnm, nvm, etc.)
$ErrorActionPreference = "SilentlyContinue"
$ProgressPreference = "SilentlyContinue"
$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if (-not $ProjectDir) { $ProjectDir = $PWD.Path }
Set-Location $ProjectDir
$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Always-On Memory Server - Deploy" -ForegroundColor Cyan
Write-Host " sector-7 Foundry + LEANN + MCP" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

# --- Helper: refresh PATH without restarting ---
function Refresh-Path {
    $machinePath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machinePath;$userPath"
}

# --- Check + install prerequisites ---
Write-Host "[1/7] Checking prerequisites..." -ForegroundColor Yellow

# Check terraform
$hasTF = Get-Command terraform -ErrorAction SilentlyContinue
if (-not $hasTF) {
    Write-Host "  Terraform not found. Installing..." -ForegroundColor Yellow
    try {
        winget install Hashicorp.Terraform --accept-package-agreements --accept-source-agreements --silent 2>$null
        Refresh-Path
        $hasTF = Get-Command terraform -ErrorAction SilentlyContinue
        if (-not $hasTF) {
            # winget sometimes installs to a path not yet in current session
            $tfPaths = @(
                "$env:LOCALAPPDATA\Microsoft\WinGet\Links\terraform.exe",
                "C:\ProgramData\chocolatey\bin\terraform.exe",
                "$env:USERPROFILE\AppData\Local\Microsoft\WinGet\Packages\Hashicorp.Terraform_Microsoft.Winget.Source_8wekyb3d8bbwe\terraform.exe"
            )
            foreach ($p in $tfPaths) {
                $dir = Split-Path $p -Parent
                if (Test-Path $dir) { $env:Path += ";$dir"; break }
            }
            # Also scan Program Files
            $found = Get-ChildItem "C:\Program Files\*terraform*" -Recurse -Filter "terraform.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($found) { $env:Path += ";$($found.DirectoryName)" }
            Refresh-Path
        }
        $hasTF = Get-Command terraform -ErrorAction SilentlyContinue
        if ($hasTF) {
            Write-Host "  Terraform installed!" -ForegroundColor Green
        } else {
            Write-Host "  Terraform installed but not in PATH yet." -ForegroundColor Yellow
            Write-Host "  Close this window, open a NEW terminal, and run deploy.ps1 again." -ForegroundColor Yellow
            Write-Host "  (This only happens once after first install)" -ForegroundColor Gray
            Read-Host "Press Enter to exit"
            exit 0
        }
    } catch {
        Write-Host "  Auto-install failed. Install manually:" -ForegroundColor Red
        Write-Host "  winget install Hashicorp.Terraform" -ForegroundColor Gray
        Write-Host "  Or: https://developer.hashicorp.com/terraform/install" -ForegroundColor Gray
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "  Terraform: OK ($(terraform version -json 2>$null | ConvertFrom-Json | Select-Object -Expand terraform_version -ErrorAction SilentlyContinue))" -ForegroundColor Green
}

# Check az CLI
$hasAZ = Get-Command az -ErrorAction SilentlyContinue
if (-not $hasAZ) {
    Write-Host "  Azure CLI not found. Installing..." -ForegroundColor Yellow
    try {
        winget install Microsoft.AzureCLI --accept-package-agreements --accept-source-agreements --silent 2>$null
        Refresh-Path
        $hasAZ = Get-Command az -ErrorAction SilentlyContinue
        if ($hasAZ) {
            Write-Host "  Azure CLI installed!" -ForegroundColor Green
        } else {
            Write-Host "  Azure CLI installed but not in PATH yet." -ForegroundColor Yellow
            Write-Host "  Close this window, open a NEW terminal, and run deploy.ps1 again." -ForegroundColor Yellow
            Read-Host "Press Enter to exit"
            exit 0
        }
    } catch {
        Write-Host "  Auto-install failed. Install: winget install Microsoft.AzureCLI" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
} else {
    Write-Host "  Azure CLI: OK" -ForegroundColor Green
}

# --- Check Azure login ---
Write-Host ""
Write-Host "[2/7] Checking Azure login..." -ForegroundColor Yellow
$ErrorActionPreference = "SilentlyContinue"
$azCheck = az account show --query "id" -o tsv 2>$null
$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($azCheck)) {
    Write-Host "  Not logged in. Opening browser..." -ForegroundColor Gray
    az login 2>$null
    $azCheck = az account show --query "id" -o tsv 2>$null
    if ([string]::IsNullOrWhiteSpace($azCheck)) {
        Write-Host "  Azure login failed. Please run 'az login' manually first." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}
$currentSub = $azCheck.Trim()
Write-Host "  Logged in. Subscription: $currentSub" -ForegroundColor Green

# --- Gather variables ---
Write-Host ""
Write-Host "[3/7] Configuration" -ForegroundColor Yellow
Write-Host "  Press Enter to accept [defaults]" -ForegroundColor Gray
Write-Host ""

$subId = Read-Host "  Azure Subscription ID [$currentSub]"
if ([string]::IsNullOrWhiteSpace($subId)) { $subId = $currentSub }

$apiKeySecure = Read-Host "  Foundry API Key (sector-7)" -AsSecureString
$bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($apiKeySecure)
$apiKey = [Runtime.InteropServices.Marshal]::PtrToStringAuto($bstr)
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
if ([string]::IsNullOrWhiteSpace($apiKey)) {
    Write-Host "  ERROR: API key required." -ForegroundColor Red
    Read-Host "Press Enter to exit"; exit 1
}

# Auto-detect public IP
$myIp = $null
try { $myIp = (Invoke-RestMethod -Uri "https://api.ipify.org" -TimeoutSec 5) } catch {}
$sshIp = Read-Host "  Your public IP for SSH [$myIp] (Enter=use detected, 'skip'=no SSH)"
if ($sshIp -eq "skip") { $sshIp = "" }
elseif ([string]::IsNullOrWhiteSpace($sshIp)) { $sshIp = $myIp }

$vmSize = Read-Host "  VM size [Standard_D4s_v6]"
if ([string]::IsNullOrWhiteSpace($vmSize)) { $vmSize = "Standard_D4s_v6" }

$smKey = Read-Host "  Supermemory API key [skip] (optional cold storage)"
if ($smKey -eq "skip") { $smKey = "" }

# --- Generate terraform.tfvars ---
Write-Host ""
Write-Host "[4/7] Generating terraform.tfvars..." -ForegroundColor Yellow

$sshLine = if ([string]::IsNullOrWhiteSpace($sshIp)) { "[]" } else { "[`"$sshIp/32`"]" }

@"
subscription_id                  = "$subId"
project_name                     = "leann-memory"
environment                      = "prod"
location                         = "southcentralus"
cognitive_location               = "eastus"
vm_size                          = "$vmSize"
admin_username                   = "adminuser"
allowed_ssh_cidrs                = $sshLine
existing_cognitive_account_name   = "sector-7"
existing_cognitive_resource_group = "sector-7-rg"
foundry_endpoint                 = "https://sector-7.openai.azure.com/openai/v1"
embedding_model                  = "embed-v-4-0"
chat_model                       = "gpt-4.1-mini"
"@ | Set-Content -Path "$ProjectDir\terraform.tfvars" -Encoding utf8

Write-Host "  Written: terraform.tfvars" -ForegroundColor Green

# --- Set API key as env var (never in tfvars file) ---
$env:TF_VAR_foundry_api_key = $apiKey

# --- Terraform Init ---
Write-Host ""
Write-Host "[5/7] terraform init..." -ForegroundColor Yellow
terraform init -no-color 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
if ($LASTEXITCODE -ne 0) {
    Write-Host "  terraform init FAILED" -ForegroundColor Red
    Read-Host "Press Enter to exit"; exit 1
}
Write-Host "  Init complete" -ForegroundColor Green

# --- Terraform Plan ---
Write-Host ""
Write-Host "[6/7] terraform plan..." -ForegroundColor Yellow
terraform plan -out=tfplan -no-color 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
if ($LASTEXITCODE -ne 0) {
    Write-Host "  terraform plan FAILED" -ForegroundColor Red
    Read-Host "Press Enter to exit"; exit 1
}

Write-Host ""
$confirm = Read-Host "  Apply this plan? (y/n)"
if ($confirm -ne "y") {
    Write-Host "  Aborted." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"; exit 0
}

# --- Terraform Apply ---
Write-Host ""
Write-Host "[7/7] Deploying..." -ForegroundColor Yellow
terraform apply tfplan -no-color 2>&1 | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }
if ($LASTEXITCODE -ne 0) {
    Write-Host "  terraform apply FAILED" -ForegroundColor Red
    Read-Host "Press Enter to exit"; exit 1
}
Remove-Item tfplan -ErrorAction SilentlyContinue
Write-Host ""
Write-Host "  Deploy complete!" -ForegroundColor Green

# =============================================================================
# POST-DEPLOY
# =============================================================================
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " Infrastructure Created!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green

$vmFqdn = (terraform output -raw vm_fqdn 2>$null).Trim()
$mcpEndpoint = (terraform output -raw mcp_endpoint 2>$null).Trim()
$mcpToken = (terraform output -raw mcp_bearer_token 2>$null).Trim()
$sshCmd = (terraform output -raw ssh_command 2>$null).Trim()

Write-Host ""
Write-Host "  VM:   $vmFqdn" -ForegroundColor Cyan
Write-Host "  MCP:  $mcpEndpoint" -ForegroundColor Cyan
Write-Host "  SSH:  $sshCmd" -ForegroundColor Cyan

# --- Wait for health check ---
Write-Host ""
Write-Host "Waiting for VM bootstrap (~2-3 min)..." -ForegroundColor Yellow
$healthUrl = "https://$vmFqdn/health"
$healthy = $false

for ($i = 1; $i -le 20; $i++) {
    Write-Host "  Health check $i/20..." -NoNewline
    try {
        $ErrorActionPreference = "SilentlyContinue"
        $resp = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 5 2>$null
        $ErrorActionPreference = "Stop"
        if ($resp.status -eq "ok") {
            Write-Host " UP!" -ForegroundColor Green
            $healthy = $true
            Write-Host ""
            Write-Host ($resp | ConvertTo-Json -Depth 5) -ForegroundColor Gray
            break
        }
        Write-Host " not ready" -ForegroundColor DarkGray
    } catch {
        Write-Host " not ready" -ForegroundColor DarkGray
    }
    Start-Sleep -Seconds 15
}
$ErrorActionPreference = "Stop"

if (-not $healthy) {
    Write-Host ""
    Write-Host "  VM still bootstrapping. Check manually in a few minutes:" -ForegroundColor Yellow
    Write-Host "  curl $healthUrl" -ForegroundColor Gray
}

# --- Claude Code MCP ---
Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " Claude Code MCP Setup" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

$hasClaude = Get-Command claude -ErrorAction SilentlyContinue
if ($hasClaude) {
    $addMcp = Read-Host "  Claude Code detected. Add memory MCP? (y/n)"
    if ($addMcp -eq "y") {
        Write-Host "  Adding leann-memory MCP..." -ForegroundColor Yellow
        $ErrorActionPreference = "SilentlyContinue"
        claude mcp add --scope user leann-memory --transport http "https://$vmFqdn/mcp" --header "Authorization: Bearer $mcpToken" 2>$null
        $ErrorActionPreference = "Stop"
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Claude Code MCP configured!" -ForegroundColor Green
        } else {
            Write-Host "  Auto-add failed. Add manually:" -ForegroundColor Yellow
            Write-Host "  claude mcp add --scope user leann-memory --transport http `"https://$vmFqdn/mcp`" --header `"Authorization: Bearer $mcpToken`"" -ForegroundColor White
        }
    }
} else {
    Write-Host "  Claude Code not in PATH. Add MCP manually:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  claude mcp add --scope user leann-memory \" -ForegroundColor White
    Write-Host "    --transport http \" -ForegroundColor White
    Write-Host "    `"https://$vmFqdn/mcp`" \" -ForegroundColor White
    Write-Host "    --header `"Authorization: Bearer $mcpToken`"" -ForegroundColor White
}

# --- Supermemory cold storage (optional) ---
if (-not [string]::IsNullOrWhiteSpace($smKey)) {
    Write-Host ""
    Write-Host "Configuring supermemory cold storage..." -ForegroundColor Yellow
    Write-Host "  (will be configured after VM is fully ready)" -ForegroundColor Gray
    Write-Host "  SSH in and run:" -ForegroundColor Gray
    Write-Host "  echo 'SUPERMEMORY_API_KEY=$smKey' | tee -a /etc/leann-memory/env" -ForegroundColor White
    Write-Host "  systemctl restart leann-mcp" -ForegroundColor White
}

# --- Save credentials locally (gitignored) ---
@"
# Always-On Memory Server Credentials
# Generated: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
# DO NOT COMMIT THIS FILE
VM_FQDN=$vmFqdn
MCP_ENDPOINT=$mcpEndpoint
MCP_BEARER_TOKEN=$mcpToken
SSH_COMMAND=$sshCmd
"@ | Set-Content "$ProjectDir\.credentials" -Encoding utf8

# --- Final summary ---
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " ALL DONE" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Health:   https://$vmFqdn/health" -ForegroundColor White
Write-Host "  MCP:      $mcpEndpoint" -ForegroundColor White
Write-Host "  SSH:      $sshCmd" -ForegroundColor White
Write-Host ""
Write-Host "  Arch:     Always-On Memory Agent v2" -ForegroundColor Gray
Write-Host "  Embed:    embed-v-4-0 (sector-7)" -ForegroundColor Gray
Write-Host "  Chat:     gpt-4.1-mini (sector-7)" -ForegroundColor Gray
Write-Host "  Consol:   Every 30 min (background)" -ForegroundColor Gray
Write-Host "  Creds:    .credentials (local, gitignored)" -ForegroundColor Gray
Write-Host ""
Write-Host "  NEXT:" -ForegroundColor Yellow
Write-Host "  1. Rotate Foundry API key in Azure portal" -ForegroundColor White
Write-Host "  2. Test: curl https://$vmFqdn/health" -ForegroundColor White
Write-Host "  3. Use in Claude Code: retain, recall, reflect" -ForegroundColor White
Write-Host ""

# Clean up sensitive vars
$env:TF_VAR_foundry_api_key = ""
$apiKey = ""

Read-Host "Press Enter to close"
