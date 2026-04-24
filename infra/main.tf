data "azurerm_client_config" "current" {}

resource "random_string" "suffix" {
  length  = 6
  upper   = false
  special = false
}

locals {
  clean_project_name = replace(var.project_name, "-", "")
  name_prefix        = "${var.project_name}-${var.environment}"
  short_prefix       = substr(local.clean_project_name, 0, 12)
}

resource "azurerm_resource_group" "main" {
  name     = "rg-${local.name_prefix}"
  location = var.location
}

resource "azurerm_log_analytics_workspace" "main" {
  name                = "log-${local.name_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}

resource "azurerm_application_insights" "main" {
  name                = "appi-${local.name_prefix}"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  workspace_id        = azurerm_log_analytics_workspace.main.id
  application_type    = "web"
}

resource "azurerm_storage_account" "main" {
  name                     = substr("st${local.short_prefix}${random_string.suffix.result}", 0, 24)
  resource_group_name      = azurerm_resource_group.main.name
  location                 = azurerm_resource_group.main.location
  account_tier             = "Standard"
  account_replication_type = "LRS"
}

resource "azurerm_storage_container" "raw_events" {
  name                  = "raw-events"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "processed_events" {
  name                  = "processed-events"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

resource "azurerm_storage_container" "email_logs" {
  name                  = "email-logs"
  storage_account_id    = azurerm_storage_account.main.id
  container_access_type = "private"
}

resource "azurerm_storage_table" "events" {
  name                 = "Events"
  storage_account_name = azurerm_storage_account.main.name
}

resource "azurerm_storage_table" "digests" {
  name                 = "Digests"
  storage_account_name = azurerm_storage_account.main.name
}

resource "azurerm_storage_table" "email_logs" {
  name                 = "EmailLogs"
  storage_account_name = azurerm_storage_account.main.name
}

resource "azurerm_service_plan" "main" {
  name                = "asp-${local.name_prefix}"
  resource_group_name = azurerm_resource_group.main.name
  location            = var.app_service_location
  os_type             = "Linux"
  sku_name            = "B1"
}

resource "azurerm_key_vault" "main" {
  name                       = substr("kv-${local.short_prefix}-${random_string.suffix.result}", 0, 24)
  location                   = azurerm_resource_group.main.location
  resource_group_name        = azurerm_resource_group.main.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  soft_delete_retention_days = 7
}

resource "azurerm_key_vault_access_policy" "deployer" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = data.azurerm_client_config.current.object_id

  secret_permissions = [
    "Get",
    "List",
    "Set",
    "Delete",
    "Purge",
    "Recover",
  ]
}

resource "azurerm_key_vault_secret" "ticketmaster_api_key" {
  name         = "TICKETMASTER-API-KEY"
  value        = var.ticketmaster_api_key
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault_access_policy.deployer]
}

resource "azurerm_key_vault_secret" "seatgeek_client_id" {
  name         = "SEATGEEK-CLIENT-ID"
  value        = var.seatgeek_client_id
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault_access_policy.deployer]
}

resource "azurerm_key_vault_secret" "sendgrid_api_key" {
  name         = "SENDGRID-API-KEY"
  value        = var.sendgrid_api_key
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault_access_policy.deployer]
}

resource "azurerm_key_vault_secret" "daily_email_to" {
  name         = "DAILY-EMAIL-TO"
  value        = var.daily_email_to
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault_access_policy.deployer]
}

resource "azurerm_key_vault_secret" "daily_email_from" {
  name         = "DAILY-EMAIL-FROM"
  value        = var.daily_email_from
  key_vault_id = azurerm_key_vault.main.id

  depends_on = [azurerm_key_vault_access_policy.deployer]
}

resource "azurerm_linux_function_app" "main" {
  name                = "func-${local.name_prefix}-${random_string.suffix.result}"
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_service_plan.main.location

  service_plan_id            = azurerm_service_plan.main.id
  storage_account_name       = azurerm_storage_account.main.name
  storage_account_access_key = azurerm_storage_account.main.primary_access_key

  identity {
    type = "SystemAssigned"
  }

  site_config {
    always_on = true

    application_stack {
      python_version = "3.11"
    }

    application_insights_connection_string = azurerm_application_insights.main.connection_string
  }

  app_settings = {
    FUNCTIONS_WORKER_RUNTIME = "python"
    AzureWebJobsFeatureFlags = "EnableWorkerIndexing"
    WEBSITE_TIME_ZONE        = "America/Chicago"
    STORAGE_ACCOUNT_NAME     = azurerm_storage_account.main.name
    TICKETMASTER_API_KEY     = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.ticketmaster_api_key.versionless_id})"
    SEATGEEK_CLIENT_ID       = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.seatgeek_client_id.versionless_id})"
    SENDGRID_API_KEY         = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.sendgrid_api_key.versionless_id})"
    DAILY_EMAIL_TO           = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.daily_email_to.versionless_id})"
    DAILY_EMAIL_FROM         = "@Microsoft.KeyVault(SecretUri=${azurerm_key_vault_secret.daily_email_from.versionless_id})"
  }
}

resource "azurerm_role_assignment" "function_blob_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Blob Data Contributor"
  principal_id         = azurerm_linux_function_app.main.identity[0].principal_id
}

resource "azurerm_role_assignment" "function_table_contributor" {
  scope                = azurerm_storage_account.main.id
  role_definition_name = "Storage Table Data Contributor"
  principal_id         = azurerm_linux_function_app.main.identity[0].principal_id
}

resource "azurerm_key_vault_access_policy" "function_app" {
  key_vault_id = azurerm_key_vault.main.id
  tenant_id    = data.azurerm_client_config.current.tenant_id
  object_id    = azurerm_linux_function_app.main.identity[0].principal_id

  secret_permissions = [
    "Get",
    "List",
  ]
}
