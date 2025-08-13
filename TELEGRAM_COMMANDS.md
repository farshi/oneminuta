# Telegram Analytics Commands

## Using the CLI

All analytics operations are now available through a single CLI command: `./telegram_analytics`

## Quick Start

```bash
# 1. First-time authentication
make telegram-auth

# 2. Analyze channels (last 3 days)
make telegram-analyze

# 3. List hot clients
make telegram-list
```

## Available Commands

### Authentication
```bash
./telegram_analytics auth                  # Interactive authentication
./telegram_analytics auth --phone +1234... # With phone number
```

### Analysis
```bash
./telegram_analytics analyze               # Analyze last 3 days
./telegram_analytics analyze --days 7      # Analyze last 7 days
./telegram_analytics analyze --channels @channel1 @channel2
```

### Testing
```bash
./telegram_analytics test access          # Test channel access
./telegram_analytics test filter          # Test message filtering
./telegram_analytics test performance     # Test performance
./telegram_analytics test all            # Run all tests
```

### Monitoring
```bash
./telegram_analytics monitor              # Continuous monitoring
./telegram_analytics monitor --duration 300  # Monitor for 5 minutes
```

### Debugging
```bash
./telegram_analytics debug                # Debug all channels
./telegram_analytics debug --channel @phuketgid
./telegram_analytics debug --limit 20     # Check 20 messages
```

### Client Management
```bash
./telegram_analytics list                 # List hot clients (score >= 60)
./telegram_analytics list --min-score 80  # Only very hot clients
./telegram_analytics list --limit 5       # Top 5 clients
```

### Cleanup
```bash
./telegram_analytics clean                # Clean analytics data
./telegram_analytics clean --keep-sessions # Keep auth sessions
```

## Using Make Commands

For convenience, all commands are also available through Make:

```bash
make telegram-auth          # Authenticate
make telegram-analyze       # Analyze (3 days)
make telegram-analyze-week  # Analyze (7 days)
make telegram-monitor       # Real-time monitor
make telegram-debug         # Debug messages
make telegram-list          # List hot clients
make telegram-test-all      # Run all tests
make telegram-clean         # Clean storage
```

## Examples

### Daily Analysis Workflow
```bash
# Morning analysis
make telegram-analyze
make telegram-list

# Check specific channel
./telegram_analytics debug --channel @phuketgid

# Clean up old data
make telegram-clean
```

### Testing Workflow
```bash
# Test everything
make telegram-test-all

# Test specific component
./telegram_analytics test access
./telegram_analytics test filter
```

### Production Workflow
```bash
# One-time setup
make telegram-auth

# Daily cron job
0 9 * * * cd /path/to/oneminuta && ./telegram_analytics analyze --days 1
0 21 * * * cd /path/to/oneminuta && ./telegram_analytics list --min-score 70

# Weekly cleanup
0 0 * * 0 cd /path/to/oneminuta && ./telegram_analytics clean
```

## Performance Considerations

- For large channels, use smaller day ranges: `--days 1` or `--days 2`
- Run analysis during off-peak hours to avoid rate limits
- Use `clean` regularly to prevent storage bloat
- Monitor operations may consume more resources - use `--duration` to limit

## Troubleshooting

| Issue | Command to Fix |
|-------|---------------|
| Authentication issues | `./telegram_analytics auth` |
| Test channel access | `./telegram_analytics test access` |
| Debug filtering | `./telegram_analytics debug` |
| Clean corrupted data | `./telegram_analytics clean` |