variable "subscription_id" {
  type        = string
  description = "Azure subscription id."
}

variable "project_name" {
  type        = string
  description = "Project name used for Azure resource naming."
  default     = "chicago-event-pulse"
}

variable "location" {
  type        = string
  description = "Primary Azure region for shared resources."
  default     = "eastus"
}

variable "app_service_location" {
  type        = string
  description = "Azure region for the App Service Plan and Function App."
  default     = "centralus"
}

variable "environment" {
  type        = string
  description = "Deployment environment."
  default     = "dev"
}

variable "ticketmaster_api_key" {
  type        = string
  description = "Ticketmaster Discovery API key."
  sensitive   = true
}

variable "seatgeek_client_id" {
  type        = string
  description = "SeatGeek client id."
  sensitive   = true
  default     = ""
}

variable "sendgrid_api_key" {
  type        = string
  description = "SendGrid API key."
  sensitive   = true
}

variable "daily_email_to" {
  type        = string
  description = "Daily digest recipient email address."
  sensitive   = true
}

variable "daily_email_from" {
  type        = string
  description = "Verified SendGrid sender email address."
  sensitive   = true
}
