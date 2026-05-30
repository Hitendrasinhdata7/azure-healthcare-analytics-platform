resource "azurerm_databricks_workspace" "main" {
  name                        = "dbw-${var.project_name}-${var.environment}"
  resource_group_name         = var.resource_group_name
  location                    = var.location
  sku                         = var.databricks_sku
  managed_resource_group_name = "rg-${var.project_name}-databricks-managed-${var.environment}"

  custom_parameters {
    virtual_network_id                                   = var.vnet_id
    public_subnet_name                                   = var.public_subnet_name
    private_subnet_name                                  = var.private_subnet_name
    public_subnet_network_security_group_association_id  = azurerm_subnet_network_security_group_association.public.id
    private_subnet_network_security_group_association_id = azurerm_subnet_network_security_group_association.private.id
    no_public_ip                                         = true
  }

  tags = var.tags
}

resource "azurerm_network_security_group" "databricks" {
  name                = "nsg-databricks-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags
}

resource "azurerm_subnet_network_security_group_association" "public" {
  subnet_id                 = data.azurerm_subnet.public.id
  network_security_group_id = azurerm_network_security_group.databricks.id
}

resource "azurerm_subnet_network_security_group_association" "private" {
  subnet_id                 = data.azurerm_subnet.private.id
  network_security_group_id = azurerm_network_security_group.databricks.id
}

data "azurerm_subnet" "public" {
  name                 = var.public_subnet_name
  virtual_network_name = data.azurerm_virtual_network.main.name
  resource_group_name  = var.resource_group_name
}

data "azurerm_subnet" "private" {
  name                 = var.private_subnet_name
  virtual_network_name = data.azurerm_virtual_network.main.name
  resource_group_name  = var.resource_group_name
}

data "azurerm_virtual_network" "main" {
  name                = "vnet-${var.project_name}-${var.environment}"
  resource_group_name = var.resource_group_name
}

output "workspace_id"  { value = azurerm_databricks_workspace.main.id }
output "workspace_url" { value = "https://${azurerm_databricks_workspace.main.workspace_url}" }

variable "resource_group_name" {}
variable "location" {}
variable "project_name" {}
variable "environment" {}
variable "vnet_id" {}
variable "public_subnet_name" {}
variable "private_subnet_name" {}
variable "databricks_sku" { default = "premium" }
variable "tags" { default = {} }
