/**
 * Temporal server utilities for Next.js.
 * Use in API routes, server actions, and server components only.
 * Auto-generated - DO NOT EDIT MANUALLY
 */

import { Client, Connection } from '@temporalio/client';
import type { WorkflowHandle } from '@temporalio/client';
import type { WorkflowProgress, StepProgress, WorkflowStatus } from './types';

// =============================================================================
// Configuration
// =============================================================================

export interface TemporalConfig {
  host: string;
  namespace: string;
  taskQueue: string;
}

const defaultConfig: TemporalConfig = {
  host: process.env.TEMPORAL_HOST || 'localhost:7233',
  namespace: process.env.TEMPORAL_NAMESPACE || 'default',
  taskQueue: process.env.TEMPORAL_TASK_QUEUE || 'generation-queue',
};

let _client: Client | null = null;
let _config: TemporalConfig = defaultConfig;

/**
 * Configure the Temporal client.
 * Call this once at app startup if you need custom settings.
 */
export function configureTemporalClient(config: Partial<TemporalConfig>): void {
  _config = { ...defaultConfig, ...config };
  _client = null; // Reset client to use new config
}

/**
 * Get or create the Temporal client (singleton).
 */
export async function getTemporalClient(): Promise<Client> {
  if (!_client) {
    const connection = await Connection.connect({
      address: _config.host,
    });

    _client = new Client({
      connection,
      namespace: _config.namespace,
    });
  }

  return _client;
}

/**
 * Get the current task queue.
 */
export function getTaskQueue(): string {
  return _config.taskQueue;
}

// =============================================================================
// Workflow Execution
// =============================================================================

export interface StartWorkflowResult {
  workflowId: string;
}

/**
 * Start a workflow and return its ID.
 *
 * @example
 * ```ts
 * const { workflowId } = await startWorkflow('RubyWorkflow', { topic: 'AI news' });
 * ```
 */
export async function startWorkflow<TInput>(
  workflowName: string,
  input: TInput,
  options?: { id?: string; idPrefix?: string }
): Promise<StartWorkflowResult> {
  const client = await getTemporalClient();
  const workflowId =
    options?.id || `${options?.idPrefix || workflowName.toLowerCase()}-${randomId()}`;

  await client.workflow.start(workflowName, {
    taskQueue: _config.taskQueue,
    workflowId,
    args: [input],
  });

  return { workflowId };
}

/**
 * Get the current progress of a workflow.
 */
export async function getWorkflowProgress(workflowId: string): Promise<WorkflowProgress> {
  const client = await getTemporalClient();
  const handle = client.workflow.getHandle(workflowId);

  try {
    const description = await handle.describe();
    const executionStatus = description.status.name;

    let status: WorkflowStatus = 'pending';
    let currentStep: StepProgress | null = null;
    let result: unknown = undefined;
    let error: string | undefined = undefined;

    if (isWorkflowRunning(executionStatus)) {
      try {
        status = await handle.query<WorkflowStatus>('get_status');
        currentStep = await handle.query<StepProgress>('get_current_step');
      } catch {
        status = 'running';
      }
    } else if (executionStatus === 'COMPLETED') {
      status = 'completed';
      try {
        result = await handle.result();
      } catch (e) {
        error = String(e);
      }
    } else if (
      executionStatus === 'FAILED' ||
      executionStatus === 'TERMINATED' ||
      executionStatus === 'TIMED_OUT'
    ) {
      status = 'failed';
      error = `Workflow ${executionStatus.toLowerCase()}`;
    } else if (executionStatus === 'CANCELLED') {
      status = 'cancelled';
    }

    return {
      workflowId,
      status,
      executionStatus,
      currentStep,
      result,
      error,
    };
  } catch (e) {
    return {
      workflowId,
      status: 'failed',
      executionStatus: 'NOT_FOUND',
      currentStep: null,
      error: `Workflow not found: ${String(e)}`,
    };
  }
}

/**
 * Wait for a workflow to complete and return its result.
 */
export async function waitForWorkflow<TResult>(
  workflowId: string,
  timeoutMs: number = 300000
): Promise<{ result?: TResult; error?: string; timedOut?: boolean }> {
  const client = await getTemporalClient();
  const handle = client.workflow.getHandle(workflowId);

  try {
    const result = await Promise.race([
      handle.result() as Promise<TResult>,
      new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error('TIMEOUT')), timeoutMs)
      ),
    ]);
    return { result };
  } catch (e) {
    const errorStr = String(e);
    if (errorStr.includes('TIMEOUT')) {
      return { timedOut: true };
    }
    return { error: errorStr };
  }
}

/**
 * Cancel a running workflow.
 */
export async function cancelWorkflow(
  workflowId: string
): Promise<{ success: boolean; error?: string }> {
  const client = await getTemporalClient();
  const handle = client.workflow.getHandle(workflowId);

  try {
    await handle.cancel();
    return { success: true };
  } catch (e) {
    return { success: false, error: String(e) };
  }
}

/**
 * Get a handle to an existing workflow.
 */
export async function getWorkflowHandle(workflowId: string): Promise<WorkflowHandle> {
  const client = await getTemporalClient();
  return client.workflow.getHandle(workflowId);
}

// =============================================================================
// Helpers
// =============================================================================

function randomId(): string {
  return Math.random().toString(36).substring(2, 14);
}

function isWorkflowRunning(status: string): boolean {
  return status === 'RUNNING' || status === 'CONTINUED_AS_NEW';
}

