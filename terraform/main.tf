terraform {
  required_version = ">= 1.6.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.90"
    }
    databricks = {
      source  = "databricks/databricks"
      version = "~> 1.38"
    }
  }
  backend "azurerm" {
    resource_group_name  = "rg-healthcare-tfstate"
    storage_account_name = "sahealthcaretfstate"
    container_name       = "tfstate"
    key                  = "healthcare.terraform.tfstate"
  }
}

provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = false
    }
    resource_group {
      prevent_deletion_if_contains_resources = true
    }
  }
  subscription_id = var.subscription_id
}

provider "databricks" {
  azure_workspace_resource_id = module.databricks.workspace_id
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${var.project_name}-${var.environment}"
  location = var.location
  tags     = local.tags
}

module "storage" {
  source              = "./modules/storage"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  project_name        = var.project_name
  environment         = var.environment
  tags                = local.tags
}

module "keyvault" {
  source              = "./modules/keyvault"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  project_name        = var.project_name
  environment         = var.environment
  tenant_id           = var.tenant_id
  tags                = local.tags
}

module "network" {
  source              = "./modules/network"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  project_name        = var.project_name
  environment         = var.environment
  tags                = local.tags
}

module "databricks" {
  source              = "./modules/databricks"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  project_name        = var.project_name
  environment         = var.environment
  vnet_id             = module.network.vnet_id
  public_subnet_name  = module.network.databricks_public_subnet_name
  private_subnet_name = module.network.databricks_private_subnet_name
  tags                = local.tags
}

module "synapse" {
  source                = "./modules/synapse"
  resource_group_name   = azurerm_resource_group.main.name
  location              = var.location
  project_name          = var.project_name
  environment           = var.environment
  storage_account_id    = module.storage.storage_account_id
  data_lake_filesystem  = module.storage.gold_filesystem_id
  keyvault_id           = module.keyvault.keyvault_id
  sql_admin_password    = var.synapse_sql_password
  tags                  = local.tags
}

module "monitoring" {
  source              = "./modules/monitoring"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.location
  project_name        = var.project_name
  environment         = var.environment
  tags                = local.tags
}

locals {
  tags = {
    Project     = var.project_name
    Environment = var.environment
    ManagedBy   = "Terraform"
    Owner       = var.owner
    CostCentre  = var.cost_centre
  }
}
