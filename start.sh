#!/usr/bin/env bash

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

cleanup() {
    echo ""
    echo -e "${YELLOW}Stopping services...${NC}"
    jobs -p | xargs -r kill 2>/dev/null || true
    wait 2>/dev/null || true
    echo -e "${GREEN}Stopped.${NC}"
}
trap cleanup EXIT INT TERM

# =============================================================================
# Step 1: Clear Python cache (critical for fresh imports)
# =============================================================================
echo -e "${BLUE}Clearing Python cache...${NC}"
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# =============================================================================
# Step 2: Start Temporal dev server
# =============================================================================
echo -e "${BLUE}Starting Temporal server...${NC}"
temporal server start-dev --ui-port 8080 2>&1 | sed 's/^/[temporal] /' &
TEMPORAL_PID=$!

# Wait for Temporal gRPC to be ready (port 7233)
echo -e "${YELLOW}Waiting for Temporal gRPC (port 7233)...${NC}"
for i in {1..30}; do
    if nc -z localhost 7233 2>/dev/null; then
        echo -e "${GREEN}Temporal gRPC ready!${NC}"
        break
    fi
    if ! kill -0 $TEMPORAL_PID 2>/dev/null; then
        echo -e "${RED}Temporal server died!${NC}"
        exit 1
    fi
    sleep 1
done

if ! nc -z localhost 7233 2>/dev/null; then
    echo -e "${RED}Temporal failed to start within 30s${NC}"
    exit 1
fi

# Extra wait for Temporal to fully initialize internal services
# This is critical - gRPC port can be open before server is ready
echo -e "${YELLOW}Waiting for Temporal to fully initialize...${NC}"
sleep 3

# =============================================================================
# Step 3: Start Worker
# =============================================================================
echo -e "${BLUE}Starting worker...${NC}"
PYTHONUNBUFFERED=1 uv run python -m app.temporal.worker 2>&1 | sed 's/^/[worker] /' &
WORKER_PID=$!

# Wait for worker to register
echo -e "${YELLOW}Waiting for worker to register workflows/activities...${NC}"
for i in {1..30}; do
    if ! kill -0 $WORKER_PID 2>/dev/null; then
        echo -e "${RED}Worker died unexpectedly!${NC}"
        exit 1
    fi
    sleep 1
    # Check if worker has started by looking for the log message
    # We use jobs to check if worker is still running
    if jobs -r | grep -q .; then
        # Worker is running, give it a moment to register
        if [ $i -ge 5 ]; then
            break
        fi
    fi
done

# =============================================================================
# Ready!
# =============================================================================
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Ready!${NC}"
echo -e "  ${BLUE}Temporal UI:${NC} http://localhost:8080"
echo -e "  ${BLUE}Task Queue:${NC}  generation-queue"
echo -e "${GREEN}================================================${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
echo ""

# Keep running - wait for any background job to exit
wait
