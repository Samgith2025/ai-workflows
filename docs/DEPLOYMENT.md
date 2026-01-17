# GPTMarket Generator - Deployment Guide

Complete guide for deploying the Temporal-based media generation service with Dokploy.

## Architecture Overview

```
┌─────────────────┐                              ┌─────────────────────────────┐
│   Vercel        │                              │   Dokploy Server            │
│   (Next.js)     │                              │                             │
└────────┬────────┘                              │  ┌─────────────────────┐    │
         │                                       │  │ Temporal Server     │    │
         │ gRPC + WORKFLOW_SECRET_KEY            │  │ (port 42713)        │    │
         ▼                                       │  └──────────┬──────────┘    │
┌─────────────────┐                              │             │               │
│                 │         Direct Connection    │  ┌──────────▼──────────┐    │
│  your-server:   │◄────────────────────────────►│  │ Workers (×2)        │    │
│     42713       │                              │  │ - AI Generation     │    │
│                 │                              │  │ - FFmpeg Processing │    │
└─────────────────┘                              │  └─────────────────────┘    │
                                                 │                             │
                                                 │  ┌─────────────────────┐    │
                                                 │  │ PostgreSQL          │    │
                                                 │  │ (Temporal state)    │    │
                                                 │  └─────────────────────┘    │
                                                 └─────────────────────────────┘
```

**Security:** Authentication via `WORKFLOW_SECRET_KEY` - all workflow inputs must include a valid secret key. Invalid requests are rejected immediately with a non-retryable error.

---

## Prerequisites

- Server with Docker (4+ vCPU, 8GB+ RAM recommended)
- [Dokploy](https://dokploy.com/) installed on server
- Vercel account for Next.js deployment

---

## Step 1: Deploy to Dokploy

### 1.1 Create Application

1. Log into Dokploy dashboard
2. Click **Create Application** → **Compose**
3. Configure:
   - **Name:** `gptmarket-generator`
   - **Repository:** Your GitHub repo URL
   - **Compose File:** `docker-compose.prod.yml`
   - **Branch:** `main`

### 1.2 Enable Auto Deploy

1. Go to your application → **General** tab
2. Toggle **Auto Deploy** ON
3. Dokploy will automatically deploy when you push to the configured branch

### 1.3 Set Environment Variables

In Dokploy, go to **Environment** tab and add these variables. Dokploy automatically creates a `.env` file that gets passed to containers.

#### Required Variables

| Variable | Description |
|----------|-------------|
| `WORKFLOW_SECRET_KEY` | Secret for workflow auth (generate: `openssl rand -hex 32`) |
| `POSTGRES_PASSWORD` | Strong password for Temporal database |

#### AI Providers (at least one required)

| Variable | Description |
|----------|-------------|
| `REPLICATE_API_KEY` | Replicate API key |
| `OPENAI_API_KEY` | OpenAI API key |
| `GEMINI_API_KEY` | Google Gemini API key |
| `ELEVENLABS_API_KEY` | ElevenLabs API key |
| `CARTESIA_API_KEY` | Cartesia API key |

#### R2 Storage (recommended)

| Variable | Description |
|----------|-------------|
| `R2_BUCKET` | Cloudflare R2 bucket name |
| `R2_ENDPOINT_URL` | R2 endpoint URL |
| `R2_ACCESS_KEY_ID` | R2 access key |
| `R2_SECRET_ACCESS_KEY` | R2 secret key |
| `R2_PUBLIC_BASE_URL` | Public URL for media files |

#### S3 Storage (alternative)

| Variable | Description |
|----------|-------------|
| `S3_BUCKET` | S3 bucket name |
| `S3_REGION` | AWS region (default: us-east-1) |
| `S3_ACCESS_KEY` | AWS access key |
| `S3_SECRET_KEY` | AWS secret key |
| `S3_ENDPOINT_URL` | Custom endpoint (optional) |
| `S3_PUBLIC_URL_BASE` | Public URL base |

#### GPTMarket API

| Variable | Description |
|----------|-------------|
| `GPTMARKET_API_URL` | API URL (default: https://www.gptmarket.io/api) |
| `GPTMARKET_API_KEY` | GPTMarket API key |

#### Optional Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_USER` | `temporal` | Database username |
| `WORKER_REPLICAS` | `2` | Number of worker instances |
| `LOG_LEVEL` | `INFO` | Log level |
| `TEMPORAL_NAMESPACE` | `default` | Temporal namespace |
| `TEMPORAL_TASK_QUEUE` | `generation-queue` | Task queue name |
| `TEMPORAL_PORT` | `42713` | External port for Temporal gRPC |
| `WORKFLOW_SECRET_ENABLED` | `true` | Enable/disable workflow auth |

### 1.4 Deploy

Click **Deploy** in Dokploy. Monitor logs to ensure all services start correctly.

---

## Step 2: Configure Firewall (Important!)

Temporal's gRPC port is exposed publicly. While workflow-level authentication protects against unauthorized workflow execution, you should still restrict access at the network level if possible.

### Option A: Restrict to Vercel IPs (Recommended)

Get [Vercel's IP ranges](https://vercel.com/docs/edge-network/ip-addresses) and configure your firewall:

```bash
# Example with ufw
ufw allow from <vercel-ip-range> to any port 42713
ufw deny 42713
```

### Option B: Use Cloudflare Proxy

Put a Cloudflare tunnel in front for additional DDoS protection (optional, see old docs if needed).

### Option C: Accept the Risk

For MVP/low-risk deployments, workflow-level auth alone may be sufficient. Risks:
- Attackers can see workflow list/status (not inputs/outputs without valid key)
- Potential for connection spam (mitigated by Temporal's rate limiting)

---

## Step 3: Configure Vercel (Next.js)

### 3.1 Install Dependencies

```bash
npm install @temporalio/client
```

### 3.2 Set Environment Variables

In Vercel dashboard → Settings → Environment Variables:

| Variable | Value | Description |
|----------|-------|-------------|
| `TEMPORAL_HOST` | `your-server-ip:42713` | Your Dokploy server address |
| `WORKFLOW_SECRET_KEY` | Same as server | Secret key for authentication |

### 3.3 Connect from Next.js

```typescript
// lib/temporal.ts
import { Client, Connection } from '@temporalio/client';

let client: Client | null = null;

export async function getTemporalClient(): Promise<Client> {
  if (client) return client;

  const connection = await Connection.connect({
    address: process.env.TEMPORAL_HOST || 'localhost:7233',
  });

  client = new Client({ connection });
  return client;
}
```

### 3.4 Start Workflows with Authentication

```typescript
// app/actions/generate.ts
'use server'

import { getTemporalClient } from '@/lib/temporal';

interface RubyInput {
  secret_key: string;  // Required for authentication
  emotion?: string;
  additional_prompt?: string;
  rewrite_enabled?: boolean;
}

export async function startRubyGeneration(emotion?: string) {
  const client = await getTemporalClient();
  
  const handle = await client.workflow.start('RubyWorkflow', {
    taskQueue: 'generation-queue',
    workflowId: `ruby-${Date.now()}`,
    args: [{
      secret_key: process.env.WORKFLOW_SECRET_KEY,  // Include secret key!
      emotion,
      rewrite_enabled: true,  // Bypass platform detection
    }],
  });

  return { workflowId: handle.workflowId };
}

export async function getWorkflowStatus(workflowId: string) {
  const client = await getTemporalClient();
  const handle = client.workflow.getHandle(workflowId);
  
  const status = await handle.query('get_status');
  return status;
}
```

**⚠️ Important:** Always include `secret_key` in workflow inputs when `WORKFLOW_SECRET_ENABLED=true`.

---

## Step 4: Verify Deployment

### Check Docker Services

```bash
# SSH into server
ssh root@your-server

# Check all containers are running
docker ps

# Should see:
# - temporal-...-temporal-1 (Temporal server)
# - temporal-...-temporal-postgres-1 (Database)
# - temporal-...-temporal-ui-1 (Web UI)
# - temporal-...-worker-1 (Worker)
# - temporal-...-worker-2 (Worker)
```

### Check Worker Logs

```bash
docker logs temporal-...-worker-1

# Look for:
# - "Workflow secret authentication ENABLED"
# - "Worker started!"
```

### Access Temporal UI

The UI is only accessible via SSH tunnel (not exposed publicly):

```bash
# Run locally
ssh -L 8080:localhost:8080 root@your-server

# Then open in browser
open http://localhost:8080
```

### Test Authentication

Try starting a workflow without the secret key - it should fail immediately with:
```
ApplicationError: Authentication required: secret_key missing from input
```

---

## Troubleshooting

### "Authentication required" Error

1. Ensure `WORKFLOW_SECRET_KEY` is set in both Dokploy and Vercel
2. Verify you're including `secret_key` in workflow input
3. Check the key values match exactly

### "Authentication failed" Error

The secret key in your workflow input doesn't match the server's key. Check for:
- Trailing whitespace
- Copy/paste errors
- Different values in different environments

### Workers Not Processing

1. Check worker logs:
   ```bash
   docker logs temporal-...-worker-1
   ```
2. Verify worker is connected to Temporal (look for "Worker started")
3. Check task queue name matches between client and worker

### Temporal Server Not Starting

1. Check PostgreSQL is healthy:
   ```bash
   docker logs temporal-...-temporal-postgres-1
   ```
2. Check Temporal logs:
   ```bash
   docker logs temporal-...-temporal-1
   ```

### Connection Refused from Vercel

1. Check firewall allows port 42713
2. Verify `TEMPORAL_HOST` is correct (use IP, not hostname if DNS not set up)
3. Test connection:
   ```bash
   nc -zv your-server-ip 42713
   ```

---

## Scaling

### More Workers

Set in Dokploy environment variables:
```
WORKER_REPLICAS=4
```

### Bigger Workers

Edit `docker-compose.prod.yml`:
```yaml
worker:
  deploy:
    resources:
      limits:
        memory: 4G  # Increase from 2G
```

---

## Security Checklist

- [ ] Strong `WORKFLOW_SECRET_KEY` set (64+ characters)
- [ ] Same key configured in Dokploy and Vercel
- [ ] `WORKFLOW_SECRET_ENABLED=true` (default)
- [ ] Strong `POSTGRES_PASSWORD` set
- [ ] Temporal UI only accessible via SSH tunnel
- [ ] API keys stored in Vercel/Dokploy (not in code)
- [ ] Firewall configured to limit port 42713 access (optional but recommended)

---

## Maintenance

### Rotate Secret Key

1. Generate new key: `openssl rand -hex 32`
2. Update Dokploy environment variable
3. Redeploy workers (they will pick up new key)
4. Update Vercel environment variable
5. Redeploy Vercel app

### View Logs

```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker logs -f temporal-...-worker-1
```

### Backup Database

```bash
# Backup
docker exec temporal-...-temporal-postgres-1 \
  pg_dump -U temporal temporal > backup.sql

# Restore
docker exec -i temporal-...-temporal-postgres-1 \
  psql -U temporal temporal < backup.sql
```

---

## Quick Reference

| Service | Access Method |
|---------|---------------|
| Temporal gRPC | `your-server:42713` (direct) |
| Temporal UI | SSH tunnel to `localhost:8080` |
| PostgreSQL | Internal only |
| Workers | Internal only |

| Env Variable | Where | Purpose |
|--------------|-------|---------|
| `WORKFLOW_SECRET_KEY` | Dokploy + Vercel | Authenticates workflow requests |
| `TEMPORAL_HOST` | Vercel | Temporal server address |
| `POSTGRES_PASSWORD` | Dokploy | Database password |

---

## Next Steps

- [Next.js Integration](NEXTJS_INTEGRATION.md) - Connect your frontend
- [Documentation Index](README.md) - All guides
- [Main README](../README.md) - Project overview
