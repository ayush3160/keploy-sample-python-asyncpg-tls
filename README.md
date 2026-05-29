# provider-engagement sample

A small Python service that mirrors the tech stack and surface area of the original
`provider-engagement-service` recorded in the Keploy bundle next to this folder.

## Stack (matches original)

- Python 3.13
- `gunicorn` + `uvicorn.workers.UvicornWorker` (ASGI)
- `FastAPI` (the recorded responses show `Server: uvicorn` and camelCase JSON)
- `SQLAlchemy[asyncio]` + `asyncpg` against PostgreSQL
  (the recorded 409 error is `sqlalchemy.dialects.postgresql.asyncpg.IntegrityError`)
- `pydantic` v2 with `alias_generator=to_camel` for camelCase JSON
- `boto3` for SNS publishing (the bundle shows `Action=Publish` to
  `test-provider-engagement-internal-topic` / `test-events-topic`)
- `sentry-sdk` (the originals emit `Baggage` / `Sentry-Trace` headers)
- `pydantic-settings` reading the same `PROVIDER_ENGAGEMENT_SERVICE_*` env vars used in the
  recorded `k8s/deployment.yaml`

## Endpoints (lifted from the recorded test cases)

| Method | Path | Source test |
| --- | --- | --- |
| `GET`  | `/api/health` | k8s liveness/readiness probe |
| `GET`  | `/api/public/v1/project_provider?project_id=...&provider_id=...` | get-api-public-v1-project-provider-9 |
| `GET`  | `/api/private/v1/project_provider?project_id=...` | (mirrors public, lifted from logs) |
| `GET`  | `/api/public/v1/project_provider/project/{project_id}/provider/{provider_id}` | get-api-public-v1-project-provider-10/11/12 |
| `GET`  | `/api/private/v1/project_provider/project/{project_id}/provider/{provider_id}` | get-api-private-v1-project-provider-5/6/7 |
| `POST` | `/api/public/v1/project_provider_batch` | post-api-public-v1-project-provider-5 |
| `POST` | `/api/public/v1/project_provider/command` | post-api-public-v1-project-provider-4 |
| `POST` | `/api/public/v1/nda/command` | post-api-public-v1-nda-command-1 |

## Outgoing calls

These match the `kind: Http` mocks in `testset/mocks.yaml`:

- **AWS STS** `AssumeRoleWithWebIdentity` (handled transparently by boto3)
- **AWS Secrets Manager** `GetSecretValue` (only used if `AWS_*` env vars are missing —
  for local dev you should set them directly)
- **AWS SNS** `Publish` to the internal/public topics, in the outbox-event shape observed
  in the bundle:
  `{"mediaType": "...", "opaqueData": {request-headers}, "uri": "<resource uri>"}`

Media types emitted (matching the recordings):

- `application/vnd.globality.pubsub._.created.project_provider_batch`
- `application/vnd.globality.pubsub._.created.project_provider_event.provider_showed_interest`
- `application/vnd.globality.pubsub._.created.project_provider_event.proposal_submitted`
- `application/vnd.globality.pubsub._.created.nda_command.{initialize,select,mark_ready_for_signature,waive}`

## Run

### Docker compose (recommended)

```sh
docker compose up --build
```

App is on `http://localhost:8080`, Postgres on `localhost:5432`.

### Local

```sh
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# point at any running postgres
export PROVIDER_ENGAGEMENT_SERVICE_POSTGRES__HOST=localhost
export PROVIDER_ENGAGEMENT_SERVICE_POSTGRES__PASSWORD=postgres
export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1

gunicorn -c gunicorn.conf.py app.main:app
```

## Smoke test

```sh
curl -s http://localhost:8080/api/health

curl -s -X POST http://localhost:8080/api/public/v1/project_provider_batch \
  -H 'Content-Type: application/json' \
  -d '{"createdBy":"90ecb6c9-7fb0-4ef1-b4b5-aa8ce14c4ef8",
       "projectId":"6e9ab068-bb9d-489a-83dc-27662a943a60",
       "providers":[{"workspaceId":"cf51ed43-eec4-40c7-bb99-849368d89a40",
                     "providerName":"QAAutotest Provider 01",
                     "providerId":"c1a88792-8ce2-4a88-b619-b924503059d7",
                     "isApprovalRequired":false}],
       "allowAutoApprove":false}'
```
