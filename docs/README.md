# Documentation

Welcome to the GPTMarket Generator documentation. These guides will help you deploy and integrate the service.

## Guides

| Guide | Description |
|-------|-------------|
| [Deployment](DEPLOYMENT.md) | Deploy to production with Dokploy, configure Temporal, set up authentication |
| [Next.js Integration](NEXTJS_INTEGRATION.md) | Connect your Next.js app on Vercel to trigger workflows |

## Quick Links

- [Main README](../README.md) - Project overview and quick start

## Architecture

```
┌─────────────────┐                    ┌─────────────────────────────┐
│   Your App      │                    │   GPTMarket Generator       │
│   (Next.js)     │                    │                             │
└────────┬────────┘                    │  ┌─────────────────────┐    │
         │                             │  │ Temporal Server     │    │
         │ gRPC                        │  └──────────┬──────────┘    │
         ▼                             │             │               │
┌─────────────────┐                    │  ┌──────────▼──────────┐    │
│  Temporal       │◄──────────────────►│  │ Workers             │    │
│  Connection     │                    │  │ - AI Generation     │    │
└─────────────────┘                    │  │ - Video Processing  │    │
                                       │  └─────────────────────┘    │
                                       └─────────────────────────────┘
```

## Getting Help

1. Check the relevant guide above
2. Review the [main README](../README.md) for common commands
3. Open an issue on GitHub
