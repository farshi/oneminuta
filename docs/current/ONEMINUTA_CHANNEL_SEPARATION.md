# OneMinuta Official Channel Configuration ✅

## Overview

OneMinuta now has proper separation between the **official company channel** and **partner channels**, with different operational rules for each.

---

## Configuration Summary

### 🏢 OneMinuta Official Channel
- **Channel ID**: `-1002875386834`
- **Channel Name**: `@oneminuta_property` 
- **Purpose**: Company brand channel, member acquisition
- **Type**: `official`

### 🤝 Partner Channels
- **Phuket Property Expert**: `@phuketgidsell`, `@phuketgid`
- **Sabay Property Group**: `@sabay_property`
- **Purpose**: Partner property listings and lead generation
- **Type**: `partner`

---

## Operational Differences

| Operation | OneMinuta Official | Partner Channels |
|-----------|-------------------|------------------|
| **Collect Properties** | ❌ No (avoid self-collection) | ✅ Yes (partner listings) |
| **Track Analytics** | ✅ Yes (company metrics) | ✅ Yes (partner reports) |
| **Auto-greet Members** | ✅ Yes (welcome new users) | ✅ Yes (lead generation) |
| **Partner Commissions** | ❌ No (company owned) | ✅ Yes (partner revenue) |
| **Daily Reports** | ❌ No (internal channel) | ✅ Yes (9 AM summaries) |

---

## Business Logic Implementation

### Channel Type Detection
```python
# Automatic detection
asset_manager.get_channel_type("@oneminuta_property")  # → "official"
asset_manager.get_channel_type("@phuketgid")          # → "partner"
asset_manager.get_channel_type("@unknown")            # → "unknown"
```

### Operations Control
```python
# Property collection (partners only)
asset_manager.should_collect_from_channel("@oneminuta_property")  # → False
asset_manager.should_collect_from_channel("@phuketgid")           # → True

# Analytics tracking (both)
asset_manager.should_track_analytics("@oneminuta_property")       # → True
asset_manager.should_track_analytics("@phuketgid")                # → True
```

---

## CLI Commands

### View All Partners
```bash
python oneminuta_cli.py partners
```
Shows all configured partners and their channels.

### Official Channel Analytics Only
```bash
python oneminuta_cli.py analytics --official
```
Shows OneMinuta company channel performance (brand reach, member growth).

### All Channels Combined
```bash
python oneminuta_cli.py analytics
```
Shows combined analytics but separates official vs partner metrics.

### Partner-Specific Analytics (Future)
```bash
python oneminuta_cli.py analytics --partner partner_phuketgid
```
Will show analytics for specific partner's channels only.

---

## Analytics Separation

### Official Channel Metrics
- **Brand Reach**: Total members following OneMinuta
- **Engagement Rate**: Reactions/comments on posts
- **Bot Conversions**: How many channel members start using bot
- **No Commission Tracking**: Company owned, no partner fees

### Partner Channel Metrics  
- **Lead Generation**: Hot/warm leads per channel
- **Commission Potential**: Estimated revenue from leads
- **Member Quality**: Lead conversion rates
- **Growth Performance**: Which channels generate most leads

---

## Technical Implementation

### Files Modified
1. **`services/collector/asset_manager.py`**
   - Added OneMinuta official channel config
   - Added channel type detection methods
   - Added operational control methods

2. **`services/analytics/channel_analytics.py`**
   - Separated official vs partner dashboard generation
   - Added channel type tracking in metrics
   - Excluded official channel from partner reports

3. **`oneminuta_cli.py`**
   - Added `--official` flag for analytics
   - Enhanced dashboard display with channel types
   - Added partner-specific analytics preparation

---

## Verification Tests

### ✅ Configuration Working
- OneMinuta official channel properly configured
- Partner channels correctly mapped
- Channel type detection accurate

### ✅ Operational Separation
- No property collection from official channel  
- Analytics tracked for all channels
- Partner commissions only apply to partner channels

### ✅ CLI Commands
- `partners` command shows all configured partners
- `analytics --official` shows OneMinuta channel only
- Channel types displayed in analytics dashboard

---

## Next Steps

1. **Daily Partner Reports**: 9 AM summaries excluding official channel
2. **Smart Conversation**: History-aware greetings using official vs partner context
3. **Lead Attribution**: Track which channel generated each lead
4. **Commission Tracking**: Calculate partner earnings excluding official channel activity

---

*This separation ensures OneMinuta's official channel is used for brand building while partner channels focus on lead generation and revenue sharing.*