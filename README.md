# ShotURL v3.0

Optimized screenshot capture service with FastAPI + Playwright.

## Optimal Configuration (Production)

**Resources:** 3GB RAM / 3 CPU cores
**Performance:** ~25s for 10 simultaneous requests (-50% vs baseline)
**Architecture:** Docker + Browser context pre-warming

### Quick Start

```bash
# 1. Configure the VM (VirtualBox)
VBoxManage modifyvm "shoturl" --memory 3072 --cpus 3

# 2. Start with Docker
docker-compose up -d

# 3. Verify the healthcheck
curl http://localhost:8000/api/health
```

### Docker Configuration

```yaml
MAX_CONCURRENT_BROWSERS: 3
PREWARM_COUNT: 3
BROWSER_TIMEOUT: 12s
PAGE_LOAD_TIMEOUT: 7s
```

## Features

- Full-page + viewport screenshot
- DOM and metadata extraction
- Network capture (HTTP requests)
- Smart Redis cache (optional)
- Browser context pre-warming
- Multi-device (desktop/tablet/phone)

## API Endpoints

### POST /api/capture
Complete capture with screenshot, DOM, network, metadata.

**Parameters:**
- `url` (string, required): URL to capture
- `device` (string, optional): desktop/tablet/phone
- `fullpage` (boolean, optional): Full-page screenshot
- `wait_for_selector` (string, optional): Wait for a CSS selector
- `delay` (int, optional): Delay before capture (ms)

**Example:**
```bash
curl -X POST http://localhost:8000/api/capture \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "device": "desktop", "fullpage": true}'
```

### GET /api/health
Healthcheck + system metrics.

## Tests and Benchmarks

50 configurations tested (RAM: 1-4GB, CPU: 1-6 cores).

**Top 3 configurations:**
1. 4GB/6CPU/6browsers/3prewarm = 20.82s (absolute champion)
2. 3GB/6CPU/3browsers/3prewarm = 21.35s (best value ratio)
3. 3GB/3CPU/3browsers/3prewarm = ~25s (recommended for production)

See `RAPPORT_FINAL.md` for complete analysis.

## Documentation

- `RAPPORT_FINAL.md` - Complete analysis of 50 tests
- `docs/` - Detailed technical documentation
- `tests/` - Test scripts and CSV results

## Architecture

```
FastAPI (async)
 Browser Pool (Playwright)
    Pre-warm contexts (hot standby)
    Dynamic context creation
 Smart Redis Cache (optional)
    Skip cache for dynamic pages
 Semaphore-based concurrency control
```

**Bottleneck:** Chrome rendering (75-80% of total time)
**Priority optimization:** Chrome args, not the Python backend

## Technical Stack

- **Backend:** FastAPI + Uvicorn (async)
- **Browser:** Playwright (Chromium)
- **Cache:** Redis (optional)
- **Container:** Docker
- **Frontend:** React + TypeScript + Vite

## Future Improvements

1. Optimized Chrome args based on site type (-20-30%)
2. HTTP/2 Server Push (-5-10%)
3. AVIF/WebP screenshots (-30-50% bandwidth)
4. Horizontal scaling with load balancer

## License

MIT

## Author

xGuatx - Guatx Company
