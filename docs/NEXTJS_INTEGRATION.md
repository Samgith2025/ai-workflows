# Next.js Integration Guide

How to connect your Next.js app (on Vercel) to the GPTMarket Generator Temporal service.

## Quick Start

### 1. Install Dependencies

```bash
npm install @temporalio/client @gptmarket/temporal-types
```

The `@gptmarket/temporal-types` package provides TypeScript types for all workflow inputs and outputs. See [npm package](https://www.npmjs.com/package/@gptmarket/temporal-types).

### 2. Set Environment Variables

In Vercel dashboard → Settings → Environment Variables:

| Variable | Development | Production |
|----------|-------------|------------|
| `TEMPORAL_HOST` | `localhost:7233` | `your-server-ip:42713` |
| `WORKFLOW_SECRET_KEY` | (optional for local) | `your-secret-key` |

### 3. Create Temporal Client

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

### 4. Create Server Actions

```typescript
// app/actions/generate.ts
'use server'

import { getTemporalClient } from '@/lib/temporal';
import { v4 as uuid } from 'uuid';

// Always include secret_key in production
function withAuth<T extends object>(input: T): T & { secret_key?: string } {
  return {
    ...input,
    secret_key: process.env.WORKFLOW_SECRET_KEY,
  };
}

export async function startRubyGeneration(data: {
  emotion?: string;
  additional_prompt?: string;
  text_overlay?: string;
  rewrite_enabled?: boolean;
  rewrite_device?: string;
}) {
  const client = await getTemporalClient();
  const workflowId = `ruby-${uuid()}`;

  await client.workflow.start('RubyWorkflow', {
    taskQueue: 'generation-queue',
    workflowId,
    args: [withAuth(data)],
  });

  return { workflowId };
}

export async function startPinterestSlideshow(data: {
  prompt: string;
}) {
  const client = await getTemporalClient();
  const workflowId = `pinterest-${uuid()}`;

  await client.workflow.start('SlideshowsPinterestWorkflow', {
    taskQueue: 'generation-queue',
    workflowId,
    args: [withAuth(data)],
  });

  return { workflowId };
}

export async function getWorkflowStatus(workflowId: string) {
  const client = await getTemporalClient();
  const handle = client.workflow.getHandle(workflowId);

  try {
    const status = await handle.query('get_status');
    const currentStep = await handle.query('get_current_step');
    return { status, currentStep };
  } catch (error) {
    // Workflow might have completed
    return { status: 'unknown', currentStep: null };
  }
}

export async function getWorkflowResult(workflowId: string) {
  const client = await getTemporalClient();
  const handle = client.workflow.getHandle(workflowId);

  return await handle.result();
}
```

---

## Workflow Types

### RubyWorkflow

Creates AI influencer reaction videos.

```typescript
interface RubyInput {
  secret_key?: string;  // Required in production
  
  // Core content
  additional_prompt?: string;       // Optional context for AI generation
  emotion?: string;                 // shocked, scared, surprised, etc.
  text_overlay?: string;            // Optional text on video
  
  // Person appearance
  gender?: string;                  // female, male
  age_range?: string;               // teen, early_20s, mid_20s, etc.
  ethnicity?: string;               // caucasian, black, asian, etc.
  hair_color?: string;              // black, brown, blonde, etc.
  
  // Style and setting
  style?: string;                   // coquette, clean_girl, dark_academia, etc.
  background?: string;              // bedroom, living_room, cafe, etc.
  clothing?: string;                // casual, streetwear, formal, etc.
  
  // Video settings
  aspect_ratio?: string;            // 9:16, 16:9, 1:1
  video_duration?: number;          // 5-10 seconds
  slowed_video?: boolean;           // Apply slow motion
  
  // Media rewriting (bypass platform detection)
  rewrite_enabled?: boolean;        // Make content appear as fresh uploads
  rewrite_device?: string;          // e.g., 'iPhone 15 Pro'
  
  // AI models (advanced)
  image_model?: string;             // e.g., 'nano-banana'
  video_model?: string;             // e.g., 'kling-v2.6'
}

interface RubyOutput {
  face_image_url: string;
  raw_video_url: string;
  final_video_url: string;
  enhanced_image_prompt: string;
  enhanced_video_prompt: string;
  image_model: string;
  video_model: string;
}
```

### SlideshowsPinterestWorkflow

Scrapes Pinterest for aesthetic images.

```typescript
interface SlideshowsPinterestInput {
  secret_key?: string;  // Required in production
  prompt: string;       // Description of desired images
}

interface SlideshowsPinterestOutput {
  images: Array<{
    id: string;
    title: string | null;
    description: string | null;
    image_url: string;
    aspect_ratio: string;
    image_width: number | null;
    image_height: number | null;
  }>;
  queries_used: string[];
  total_scraped: number;
}
```

---

## Polling for Progress

### Using React Query

```typescript
// hooks/useWorkflowProgress.ts
import { useQuery } from '@tanstack/react-query';
import { getWorkflowStatus, getWorkflowResult } from '@/app/actions/generate';

export function useWorkflowProgress(workflowId: string | null) {
  const statusQuery = useQuery({
    queryKey: ['workflow-status', workflowId],
    queryFn: () => getWorkflowStatus(workflowId!),
    enabled: !!workflowId,
    refetchInterval: (data) => {
      // Stop polling when complete or failed
      if (data?.status === 'COMPLETED' || data?.status === 'FAILED') {
        return false;
      }
      return 2000; // Poll every 2 seconds
    },
  });

  const resultQuery = useQuery({
    queryKey: ['workflow-result', workflowId],
    queryFn: () => getWorkflowResult(workflowId!),
    enabled: statusQuery.data?.status === 'COMPLETED',
  });

  return {
    status: statusQuery.data?.status,
    currentStep: statusQuery.data?.currentStep,
    result: resultQuery.data,
    isLoading: statusQuery.isLoading,
    isComplete: statusQuery.data?.status === 'COMPLETED',
    isFailed: statusQuery.data?.status === 'FAILED',
  };
}
```

### Component Example

```tsx
// components/GenerationProgress.tsx
'use client'

import { useWorkflowProgress } from '@/hooks/useWorkflowProgress';

export function GenerationProgress({ workflowId }: { workflowId: string }) {
  const { status, currentStep, result, isComplete, isFailed } = useWorkflowProgress(workflowId);

  if (isFailed) {
    return <div className="text-red-500">Generation failed</div>;
  }

  if (isComplete && result) {
    return (
      <div>
        <h3>Complete!</h3>
        <video src={result.final_video_url} controls />
      </div>
    );
  }

  return (
    <div>
      <p>Status: {status}</p>
      {currentStep && (
        <div>
          <p>{currentStep.step_name}</p>
          <progress value={currentStep.progress_pct} max={100} />
        </div>
      )}
    </div>
  );
}
```

---

## Error Handling

### Authentication Errors

If `WORKFLOW_SECRET_KEY` is wrong or missing:

```typescript
try {
  await startRubyGeneration({ emotion: 'shocked' });
} catch (error) {
  if (error.message.includes('Authentication required')) {
    // Missing secret_key in input
    console.error('WORKFLOW_SECRET_KEY not configured');
  } else if (error.message.includes('Authentication failed')) {
    // Wrong secret_key
    console.error('Invalid WORKFLOW_SECRET_KEY');
  }
}
```

### Connection Errors

```typescript
try {
  const client = await getTemporalClient();
} catch (error) {
  if (error.message.includes('ECONNREFUSED')) {
    console.error('Cannot connect to Temporal server');
    // Check TEMPORAL_HOST, firewall, server status
  }
}
```

---

## Local Development

### Option 1: Local Temporal (Recommended)

```bash
# Start local Temporal server
cd gptmarket-generator
make start

# In your Next.js app
TEMPORAL_HOST=localhost:7233  # Local dev uses standard port
# No WORKFLOW_SECRET_KEY needed locally
```

### Option 2: Connect to Production

```bash
# Set production variables locally
TEMPORAL_HOST=your-server-ip:42713
WORKFLOW_SECRET_KEY=your-secret-key
```

---

## Security Notes

1. **Never expose `WORKFLOW_SECRET_KEY` to the client** - only use in server actions/API routes
2. **Validate user input** before passing to workflows
3. **Use server actions** (`'use server'`) - don't call Temporal from client components
4. **Rate limit** your server actions to prevent abuse

```typescript
// Example with rate limiting
import { Ratelimit } from '@upstash/ratelimit';
import { Redis } from '@upstash/redis';

const ratelimit = new Ratelimit({
  redis: Redis.fromEnv(),
  limiter: Ratelimit.slidingWindow(10, '1 m'), // 10 per minute
});

export async function startRubyGeneration(data: RubyInput) {
  const { success } = await ratelimit.limit('generation');
  if (!success) {
    throw new Error('Rate limit exceeded');
  }
  
  // ... start workflow
}
```

---

## TypeScript Types

Install the official types package for full type safety:

```bash
npm install @gptmarket/temporal-types
```

```typescript
import type { RubyInput, RubyOutput } from '@gptmarket/temporal-types';

const input: RubyInput = {
  emotion: 'shocked',
  text_overlay: 'Hello world',
};
```

See [@gptmarket/temporal-types on npm](https://www.npmjs.com/package/@gptmarket/temporal-types) for all available types.

<details>
<summary>Alternative: Generate types locally</summary>

```bash
# In gptmarket-generator
make types

# Copy generated types to your Next.js app
cp scripts/generate_types/output/*.ts ../your-nextjs-app/types/
```

</details>

---

## Next Steps

- [Deployment Guide](DEPLOYMENT.md) - Production setup with Dokploy
- [Documentation Index](README.md) - All guides
- [Main README](../README.md) - Project overview
