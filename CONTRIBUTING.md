# Contributing

## Setup Development Environment

```bash
# Clone and install
git clone <repo>
cd TechStack
uv sync

# Verify installation
uv run pytest tests/ -v
```

## Code Style

```bash
# Format code
uv run black src/ tests/

# Lint and fix
uv run ruff check --fix src/ tests/

# Type check
uv run mypy src/
```

## Before Committing

```bash
# Run all checks
uv run black src/ tests/
uv run ruff check --fix src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-report=term-missing
```

## Testing

- Add tests for new features in `tests/`
- Keep tests focused and isolated (mock external APIs)
- Aim for 80%+ coverage on modified files
- Run `uv run pytest tests/ -v` before pushing

## Project Structure

- `src/` - Source code (workflows, analytics, data handling)
- `tests/` - Test suite (unit, integration, end-to-end)
- `db/` - Data storage (Parquet files, cached data)
- `docs/` - Documentation
- `config.csv` - Configuration (user edits, not committed)

## Adding New Features

1. Create feature branch: `git checkout -b feature/my-feature`
2. Add implementation in appropriate `src/` module
3. Add tests in `tests/test_*.py`
4. Update documentation if needed
5. Run full test suite: `uv run pytest tests/ --cov=src`
6. Commit with clear message: `git commit -m "Add: description of changes"`
7. Create pull request

## Common Modules

- **analytics_flows.py** - Portfolio analysis workflows
- **portfolio_flows.py** - Financial data aggregation
- **portfolio_prices.py** - Price fetching
- **portfolio_technical.py** - Technical indicators
- **xbrl.py** - SEC XBRL data
- **parquet_db.py** - Data storage
- **cache.py** - Caching layer

## Code Guidelines

- Use type hints: `def fetch_price(ticker: str) -> float:`
- Add docstrings to public functions
- Handle exceptions gracefully
- Log important operations
- Use Prefect tasks for workflow code

## Debugging

```bash
# Run with verbose output
uv run pytest tests/ -vv --tb=long

# Run with print statements
uv run pytest tests/ -s

# Drop into debugger
# Add: import pdb; pdb.set_trace()
uv run pytest tests/ --pdb
```

## Performance

- Use Parquet for data storage (faster than CSV)
- Cache API responses (configured in `cache.py`)
- Batch requests when possible
- Profile with: `uv run pytest tests/ --durations=10`

## Questions?

See [Documentation Index](INDEX.md) or [API Reference](API.md)
