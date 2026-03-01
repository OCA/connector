## Onshape Developer Portal Setup

Before configuring the Odoo backend, you need API credentials from Onshape.

**HMAC API Keys (quickest to start):**

1. Sign in at https://cad.onshape.com
2. Go to your **User Menu** (top-right) > **My Account** > **API keys**
   (or visit https://dev-portal.onshape.com/keys directly)
3. Click **Create new API key**
4. Give it a name (e.g. `Odoo Connector`) and select scopes:

   - `OAuth2Read` — read documents, parts, assemblies, metadata
   - `OAuth2Write` — write metadata (Part Number, Description)
   - `OAuth2Delete` — only if you need webhook management

5. Copy the **Access key** and **Secret key** — the secret is shown only once.

**Finding your Team / Company ID:**

1. Go to https://cad.onshape.com
2. Click **Teams** in the left sidebar
3. Click on your team — the URL will show the team ID:
   `https://cad.onshape.com/team/<TEAM_ID>`

**OAuth2 App Store (recommended for production):**

HMAC keys and private OAuth2 apps count against an annual API quota
(~10,000 calls/user/year for Enterprise). Only **publicly listed App Store
apps** are exempt. To set up OAuth2:

1. Go to https://dev-portal.onshape.com > **OAuth applications**
2. Click **Create new OAuth application**
3. Fill in:

   - **Name**: Your app name (e.g. `My Odoo Connector`)
   - **Primary Format**: `com.yourcompany.odoo-connector` (cannot change later)
   - **Redirect URLs**: `https://your-odoo.com/connector_onshape/oauth/callback`
   - **OAuth Scopes**: `OAuth2Read`, `OAuth2Write`

4. For quota exemption, submit the app for App Store review
   by emailing `onshape-developer-relations@ptc.com`

## Odoo Backend Configuration

1. Install the `connector_onshape` module.
2. Go to **Onshape > Configuration > Backends** and create a new backend.
3. Fill in the connection details:

   - **Base URL**: `https://cad.onshape.com` (default)
   - **Authentication Mode**: HMAC or OAuth2
   - **Team / Company ID**: From step above

4. For **HMAC** mode, enter the **API Access Key** and **API Secret Key**.

5. For **OAuth2** mode:

   a. Enter the **OAuth2 Client ID** and **Client Secret** from the Onshape
      Developer Portal. Make sure you copy the **complete** secret including
      any trailing `=` padding characters (base64 encoding).
   
   b. Copy the **OAuth2 Redirect URI** shown on the form (click the clipboard
      icon) and register it in your Onshape app's redirect URLs.
   
   c. Click **Authorize with Onshape** — you will be redirected to Onshape
      to approve access. After approval, Onshape redirects back to Odoo
      and the token is stored automatically.
   
   d. The **OAuth2 Authorized** checkbox confirms the token was obtained.

6. Click **Check Credentials** — should show a green success notification.
7. Click **Activate** to enable the backend.

## Import Settings

- **Auto-create Products**: When enabled, creates new Odoo products for
  Onshape parts that don't match any existing SKU. When disabled, unmatched
  parts are skipped (no binding created).
- **Default Product Category**: Category assigned to auto-created products.
- **Import Products Since**: Only import parts modified after this date
  (for incremental sync).

## Webhooks (Real-Time Sync)

Webhooks push Onshape changes to Odoo in real time instead of waiting
for the next scheduled sync.

1. In Odoo, note your backend ID (visible in the URL when viewing the backend
   form, e.g. `/web#id=1&model=onshape.backend`).

2. Your webhook URL is:
   `https://your-odoo-instance.com/connector_onshape/webhook/<backend_id>`

3. Generate a webhook secret (any random string, e.g. `openssl rand -hex 32`)
   and enter it in the **Webhook Secret** field on the backend form.

4. Register the webhook in Onshape. You can do this via the Onshape API
   or by clicking the **Register Webhook** button (if available) on the backend.
   The module listens for these events:

   - `onshape.model.lifecycle.metadata` — re-imports part metadata
   - `onshape.workflow.transition` — updates lifecycle state
   - `onshape.revision.created` — marks parts as released
   - `onshape.model.lifecycle.createversion` — logs version creation

5. Ensure your Odoo instance is reachable from the internet (Onshape must
   be able to POST to the webhook URL).

## Scheduled Sync (Cron Jobs)

Three cron jobs are created (disabled by default):

- **Onshape: Import Documents** — every 6 hours
- **Onshape: Import Products** — every 6 hours
- **Onshape: Import BOMs** — every 12 hours

Enable them in **Settings > Technical > Automation > Scheduled Actions**
when you're ready for automatic background synchronization.
