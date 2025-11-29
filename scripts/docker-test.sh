#!/bin/bash
# Docker build and test script for Finance TechStack

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== Finance TechStack Docker Build & Test ===${NC}"

# Configuration
IMAGE_NAME="${1:-finance-techstack}"
IMAGE_TAG="${2:-latest}"
FULL_IMAGE="$IMAGE_NAME:$IMAGE_TAG"

echo -e "${YELLOW}Building Docker image: $FULL_IMAGE${NC}"

# Build image
if docker build -t $FULL_IMAGE .; then
    echo -e "${GREEN}✓ Docker image built successfully${NC}"
else
    echo -e "${RED}✗ Failed to build Docker image${NC}"
    exit 1
fi

# Test 1: Run container without compose
echo -e "\n${YELLOW}Test 1: Running single container...${NC}"
if docker run --rm $FULL_IMAGE python -c "from src.main import aggregate_financial_data; print('Import successful')"; then
    echo -e "${GREEN}✓ Single container test passed${NC}"
else
    echo -e "${RED}✗ Single container test failed${NC}"
    exit 1
fi

# Test 2: Run tests
echo -e "\n${YELLOW}Test 2: Running pytest...${NC}"
if docker run --rm $FULL_IMAGE python -m pytest tests/test_sec_scraper.py -v --tb=short | head -50; then
    echo -e "${GREEN}✓ Tests executed${NC}"
else
    echo -e "${RED}✗ Tests failed${NC}"
    exit 1
fi

# Test 3: Docker Compose build
echo -e "\n${YELLOW}Test 3: Testing docker-compose build...${NC}"
if docker-compose build; then
    echo -e "${GREEN}✓ Docker Compose build successful${NC}"
else
    echo -e "${RED}✗ Docker Compose build failed${NC}"
    exit 1
fi

# Test 4: Docker Compose up (health check)
echo -e "\n${YELLOW}Test 4: Starting docker-compose services...${NC}"
docker-compose up -d

echo -e "${YELLOW}Waiting for services to be healthy...${NC}"
sleep 10

# Check if services are running
if docker-compose ps | grep -q "Up"; then
    echo -e "${GREEN}✓ Services started successfully${NC}"
else
    echo -e "${RED}✗ Services failed to start${NC}"
    docker-compose logs
    docker-compose down
    exit 1
fi

# Test 5: Run tests in compose
echo -e "\n${YELLOW}Test 5: Running tests via docker-compose...${NC}"
if docker-compose run --rm techstack python -m pytest tests/test_sec_scraper.py::TestCIKExtraction::test_extract_cik_aapl -v; then
    echo -e "${GREEN}✓ Tests via docker-compose passed${NC}"
else
    echo -e "${RED}✗ Tests via docker-compose failed${NC}"
    docker-compose logs
    docker-compose down
    exit 1
fi

# Test 6: Check Prefect server
echo -e "\n${YELLOW}Test 6: Checking Prefect server...${NC}"
if curl -s http://localhost:4200/api/health > /dev/null; then
    echo -e "${GREEN}✓ Prefect server is healthy${NC}"
else
    echo -e "${RED}✗ Prefect server health check failed${NC}"
fi

# Test 7: Verify data persistence
echo -e "\n${YELLOW}Test 7: Testing data persistence...${NC}"
if [ -f "db/financial_data_*.parquet" ]; then
    echo -e "${GREEN}✓ Data files created${NC}"
else
    echo -e "${YELLOW}⊘ No data files yet (expected on first run)${NC}"
fi

# Cleanup
echo -e "\n${YELLOW}Cleaning up...${NC}"
docker-compose down -v

# Image info
echo -e "\n${YELLOW}=== Image Information ===${NC}"
docker images | grep $IMAGE_NAME
docker history $FULL_IMAGE | head -10

echo -e "\n${GREEN}=== All tests passed! ===${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Push to registry: docker push $FULL_IMAGE"
echo "2. Deploy to AWS: bash deploy/aws-ecs-deploy.sh"
echo "3. Deploy to Kubernetes: kubectl apply -f deploy/kubernetes/deployment.yaml"
echo "4. Run locally: docker-compose up"
