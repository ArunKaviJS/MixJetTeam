# frontend

React + Vite. Light, aviation-themed UI for the **Aviation Permit Requests** queue.
Talks only to `awery-backend` (never to Awery or Mongo directly).

## Screens

- **List** (`src/App.jsx`) — table of permit-request emails: #, File Name, Status,
  Uploaded At, Extracted results, Awery badge. Search, pagination, manual **Refresh**,
  and a 15 s auto-poll so new emails show up while you watch.
- **Detail** (`src/Detail.jsx`) — opens on row click:
  - left: **Extraction Results** form — scalar fields editable, `Flight Schedule` /
    `Flight Sectors` shown as read-only tables.
  - right: source **PDF** (`originalFile`) + the **Send to Awery ERP** panel.
  - **Proceed →** calls `POST /files/{id}/proceed`; shows `status`, `Awery flight_id`,
    `flight_no`, and the full request/response JSON.
  - **Update** saves edited values (`PUT /files/{id}`). **Prev / Next** walk the list.

## Run

```bash
cd frontend
npm install
copy .env.example .env      # cp on macOS/Linux
npm run dev                 # http://localhost:5173
```

`.env`: `VITE_API_BASE=http://localhost:8200` (the awery-backend). That origin must
be in the backend's `AWERY_CORS_ORIGINS`.

## Proceed options (in the detail panel)

| Control | Effect |
|---|---|
| Awery company | `company__name` on the flight |
| skip duplicate check | sends `unique:[0]` (Awery won't reject as duplicate) |
| create customer first | `createCustomer` before `createFlight` |
| dry run | build + show the payload, send nothing |
