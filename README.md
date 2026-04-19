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

## Manual Test Run

The deployed Function App includes a protected HTTP trigger:

```text
POST /api/run-digest
```

To run today's digest manually, get the function URL from the Azure Portal:

```text
Function App -> Functions -> run_digest -> Get function URL
```

Then call it:

```bash
curl -X POST "https://func-chicago-event-pulse-dev-0pn9zc.azurewebsites.net/api/run-digest?code=FUNCTION_KEY"
```

To test a specific date:

```bash
curl -X POST "https://func-chicago-event-pulse-dev-0pn9zc.azurewebsites.net/api/run-digest?date=2026-04-19&code=FUNCTION_KEY"
```

The manual trigger fetches Ticketmaster events, writes Blob/Table Storage records, sends the SendGrid email, and returns a JSON summary.

## Schedule

The timer trigger runs daily at:

```text
7:00 AM America/Chicago
```

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
