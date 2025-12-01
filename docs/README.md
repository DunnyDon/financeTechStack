# Documentation Guide

This directory contains all project documentation. Start here to find what you need.

## Quick Start

- **[PORTFOLIO_FLOWS.md](PORTFOLIO_FLOWS.md)** - Main portfolio flows documentation
- **[PORTFOLIO_FLOWS_QUICK_REFERENCE.md](PORTFOLIO_FLOWS_QUICK_REFERENCE.md)** - Quick reference guide

## Core Documentation

### Portfolio Analysis System
- **[PORTFOLIO_ANALYSIS.md](PORTFOLIO_ANALYSIS.md)** - Portfolio analytics and analysis framework
- **[PORTFOLIO_FLOWS.md](PORTFOLIO_FLOWS.md)** - Prefect workflows for data aggregation and analysis
- **[PORTFOLIO_FLOWS_IMPLEMENTATION.md](PORTFOLIO_FLOWS_IMPLEMENTATION.md)** - Technical implementation details

### Testing & Quality
- **[TESTING.md](TESTING.md)** - Comprehensive testing guide
- **[BUILD_AND_TEST_REPORT.md](BUILD_AND_TEST_REPORT.md)** - Latest test results
- **[CODE_REVIEW.md](CODE_REVIEW.md)** - Code review notes and findings

### Infrastructure & Deployment
- **[DOCKER.md](DOCKER.md)** - Docker setup and containerization
- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)** - Deployment verification steps

### Configuration & Setup
- **[ALPHA_VANTAGE_SETUP.md](ALPHA_VANTAGE_SETUP.md)** - Alpha Vantage API configuration
- **[DATA_MERGE.md](DATA_MERGE.md)** - Data merging and aggregation guide

### Data & Analysis
- **[METRICS_SUMMARY.md](METRICS_SUMMARY.md)** - Key metrics and calculations
- **[STRUCTURE.md](STRUCTURE.md)** - Project structure overview

### Distributed Computing (Advanced)
- **[DASK_COILED_QUICK_REFERENCE.md](DASK_COILED_QUICK_REFERENCE.md)** - Quick reference for Dask/Coiled
- **[DASK_COILED_RECOMMENDATIONS.md](DASK_COILED_RECOMMENDATIONS.md)** - Recommendations and best practices

### Project Reports
- **[COMPLETION_REPORT.md](COMPLETION_REPORT.md)** - Project completion status
- **[PORTFOLIO_COMPLETION_REPORT.md](PORTFOLIO_COMPLETION_REPORT.md)** - Portfolio feature completion
- **[PORTFOLIO_FLOWS_COMPLETION_REPORT.md](PORTFOLIO_FLOWS_COMPLETION_REPORT.md)** - Portfolio flows completion
- **[PORTFOLIO_FLOWS_FILE_INDEX.md](PORTFOLIO_FLOWS_FILE_INDEX.md)** - File index for portfolio flows
- **[IMPROVEMENTS_CHECKLIST.md](IMPROVEMENTS_CHECKLIST.md)** - Enhancement checklist
- **[PROJECT_SUMMARY.md](PROJECT_SUMMARY.md)** - Executive project summary
- **[REVIEW_SUMMARY.md](REVIEW_SUMMARY.md)** - Review findings summary

## Common Tasks

### Run Tests
```bash
python -m pytest tests/ -v
```

### Start Prefect Server
```bash
prefect server start
```

### Run Portfolio Analysis
```bash
uv run python src/portfolio_main.py
```

### View Docker Status
```bash
docker-compose ps
```

## Directory Structure

```
TechStack/
├── src/                 # Main source code
├── tests/              # Test files and validation scripts
├── docs/               # Documentation (you are here)
├── db/                 # Database and data files
├── deploy/             # Deployment scripts
├── scripts/            # Utility scripts
├── docker/             # Docker-related files
└── README.md           # Main project README
```

## Contributing

When adding new documentation:
1. Keep it in the `docs/` folder
2. Link it in this README
3. Use clear, descriptive titles
4. Include a table of contents for long documents

## Last Updated

November 30, 2025

See individual files for their specific update dates.
