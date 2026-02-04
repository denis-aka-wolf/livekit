#!/bin/bash

echo "=== LiveKit Agent Performance Monitor ==="
echo "Date: $(date)"
echo ""

echo "1. Checking container status:"
docker compose ps
echo ""

echo "2. Checking LLM service status:"
docker logs llama_cpp 2>&1 | tail -10
echo ""

echo "3. Checking Whisper STT service status:"
docker logs whisper 2>&1 | tail -10
echo ""

echo "4. Checking LiveKit server status:"
docker logs livekit 2>&1 | tail -10
echo ""

echo "5. Checking resource usage:"
if command -v docker &> /dev/null; then
    echo "CPU and Memory usage by containers:"
    docker stats --no-stream
else
    echo "Docker not found"
fi
echo ""

echo "6. Testing LLM endpoint:"
curl -sf http://localhost:11434/v1/models || echo "LLM endpoint not responding"
echo ""

echo "7. Testing Whisper endpoint:"
curl -sf http://localhost:11435/v1/models || echo "Whisper endpoint not responding"
echo ""

echo "Performance monitoring completed."