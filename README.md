# Chicago Event Pulse

Daily Chicago event digest built with Azure Functions, Azure Storage, SendGrid, Terraform, and GitHub Actions.

## MVP

The MVP sends one daily email with events happening in Chicago today.

- Event source: Ticketmaster Discovery API
- Email provider: SendGrid
- Runtime: Python Azure Functions
- Storage: Azure Blob Storage
- Infrastructure: Terraform
- CI/CD: GitHub Actions

See [MVP.md](MVP.md) for the full architecture and build checklist.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp local.settings.json.example local.settings.json
```

Fill in the placeholder values in `local.settings.json`, then run:

```bash
pytest
func start
```

## Required Settings

The function expects these settings:

- `TICKETMASTER_API_KEY`
- `SENDGRID_API_KEY`
- `DAILY_EMAIL_TO`
- `DAILY_EMAIL_FROM`
- `STORAGE_ACCOUNT_NAME`
- `AzureWebJobsStorage`

In Azure, secrets should be stored in Key Vault and exposed to the Function App through Key Vault references.

