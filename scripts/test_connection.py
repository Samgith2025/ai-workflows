#!/usr/bin/env python
"""Test connection to Temporal server and workflow execution.

Tests the full production path:
1. Connect to Temporal server
2. Execute HelloWorldWorkflow (must be registered by the worker)
3. Verify result

Usage:
    # Test local
    uv run python scripts/test_connection.py

    # Test production
    TEMPORAL_HOST=your-server:42713 \
    WORKFLOW_SECRET_KEY=your-secret \
    uv run python scripts/test_connection.py
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


async def test_connection() -> None:
    """Test Temporal connection and workflow execution."""
    from temporalio.client import Client
    from temporalio.contrib.pydantic import pydantic_data_converter

    from app.temporal.workflows.hello_world import HelloWorldInput, HelloWorldWorkflow

    host = os.getenv('TEMPORAL_HOST', 'localhost:7233')
    namespace = os.getenv('TEMPORAL_NAMESPACE', 'default')
    task_queue = os.getenv('TEMPORAL_TASK_QUEUE', 'generation-queue')
    secret_key = os.getenv('WORKFLOW_SECRET_KEY', '')

    print('=' * 60)
    print('Temporal Connection Test')
    print('=' * 60)
    print()
    print('Configuration:')
    print(f'  TEMPORAL_HOST: {host}')
    print(f'  TEMPORAL_NAMESPACE: {namespace}')
    print(f'  TEMPORAL_TASK_QUEUE: {task_queue}')
    print(f'  WORKFLOW_SECRET_KEY: {"***" if secret_key else "(not set)"}')
    print()

    print('Connecting...')

    try:
        client = await Client.connect(host, namespace=namespace, data_converter=pydantic_data_converter)
        print('✅ Connection established!')
        print()

        # Test: List workflow executions
        print('Testing workflow list query...')
        count = 0
        async for _ in client.list_workflows():
            count += 1
        print(f'✅ Query successful! (found {count} workflow executions)')
        print()

        # Test: Run HelloWorld workflow
        print('Testing workflow execution...')
        workflow_id = f'hello-world-test-{uuid.uuid4().hex[:8]}'
        print(f'  Workflow ID: {workflow_id}')
        print(f'  Task queue: {task_queue}')

        # Build input with optional secret key
        input_data = HelloWorldInput(
            name='World',
            secret_key=secret_key if secret_key else None,
        )

        result = await client.execute_workflow(
            HelloWorldWorkflow.run,
            input_data,
            id=workflow_id,
            task_queue=task_queue,
        )

        print(f'✅ Workflow executed! Result: "{result.message}"')
        print()

        print('=' * 60)
        print('✅ All tests passed!')
        print('=' * 60)

    except Exception as e:
        print()

        # Extract the actual error message from Temporal's wrapped exceptions
        error_msg = str(e)
        cause = e.__cause__
        while cause:
            if hasattr(cause, 'message'):
                error_msg = cause.message
                break
            cause = cause.__cause__

        print(f'❌ Test failed: {error_msg}')
        print()

        error_lower = error_msg.lower()
        if 'connection' in error_lower or 'connect' in error_lower:
            print('Troubleshooting (connection issue):')
            print('  1. Is the Temporal server running?')
            print('  2. Is the host/port correct?')
            print('  3. Check firewall allows the port')
        elif 'no workers' in error_lower or 'task queue' in error_lower:
            print('Troubleshooting (no worker):')
            print('  1. Is the worker running? (make worker)')
            print('  2. Is the task queue correct?')
            print('  3. Check worker logs for errors')
        elif 'authentication' in error_lower:
            print('Troubleshooting (authentication):')
            print('  1. Is WORKFLOW_SECRET_KEY set correctly?')
            print('  2. Does it match the server config?')
        else:
            print('Troubleshooting:')
            print('  1. Check Temporal server logs')
            print('  2. Check worker logs')
        print()
        raise


def main() -> None:
    """Run the test."""
    try:
        asyncio.run(test_connection())
        sys.exit(0)
    except KeyboardInterrupt:
        print('\nCancelled.')
        sys.exit(130)
    except Exception:
        sys.exit(1)


if __name__ == '__main__':
    main()
