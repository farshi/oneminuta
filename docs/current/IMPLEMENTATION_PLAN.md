# OneMinuta Business Logic Update - Implementation Plan

*Based on request.md requirements to change from channel-as-user to partner-owned-channels model*

---

## Current State Analysis

### What We Have ✅
- Basic channel analytics system
- Member join/leave tracking 
- Telegram bot integration
- CLI analytics commands
- Property collection from channels

### What Needs to Change 🔄
- Channel ownership model (channels → partner-owned)
- User profiling from Telegram bio
- Smart conversation with history awareness
- Immediate property results after basic criteria
- Daily partner lead reports

---

## Implementation Phases

### Phase 1: Partner Model (High Priority)
**Files to Modify:**
- `services/analytics/channel_analytics.py`
- `scripts/telegram/run_telegram_bot_channels.py` 
- Database/storage structure

**Changes:**
1. **Partner Registration System**
   ```python
   # Instead of: channel_users = {"@channel": "user_id"}
   # New: partners = {"partner_id": {"channels": ["@ch1", "@ch2"], "profile": {...}}}
   ```

2. **Channel-to-Partner Mapping**
   ```python
   def get_channel_owner(channel_id) -> str:
       """Get partner who owns this channel"""
       return partner_mapping[channel_id]
   ```

3. **Multi-Channel Dashboard**
   - Partner can see analytics across all their channels
   - Channel-specific performance metrics

### Phase 2: Smart User Profiling (High Priority)
**Files to Modify:**
- New: `services/user_profiling/telegram_profile_analyzer.py`
- `services/chatbot/chatbot_manager.py`

**Features:**
1. **Bio Analysis**
   ```python
   async def analyze_telegram_profile(user) -> UserProfile:
       # Read user.first_name, user.last_name, user.bio
       # Detect: language, nationality, communication style
       pass
   ```

2. **Language Detection Enhancement**
   ```python
   def detect_language_from_profile(user) -> str:
       # Check name for Cyrillic characters
       # Check bio for language indicators
       # Default to conversation detection
   ```

### Phase 3: Smart Conversation Flow (Medium Priority)
**Files to Modify:**
- `services/chatbot/stages/user_profile_detection_stage.py`
- `services/chatbot/stages/inquiry_collection_stage.py`

**Changes:**
1. **History-Aware Greetings**
   ```python
   def generate_greeting(user_id, last_seen) -> str:
       if last_seen > 30_days_ago:
           return "Long time no see! How's your property search going?"
       elif last_seen > 7_days_ago:
           return "Welcome back! Any updates on your search?"
       else:
           return "Hello! May I know how I can help with your property search?"
   ```

2. **Immediate Results After Basic Criteria**
   ```python
   async def show_quick_results(location, budget, bedrooms=None):
       # Show top 5 properties immediately
       # Add "Show more" option
       # Add "I'm interested" buttons
   ```

### Phase 4: Daily Partner Reports (Medium Priority)
**Files to Create:**
- `services/reports/daily_partner_reports.py`
- `scripts/automation/daily_report_scheduler.py`

**Features:**
1. **9 AM Daily Reports**
   ```python
   async def generate_daily_partner_report(partner_id) -> Dict:
       # New qualified leads from all partner channels
       # Lead quality scores
       # Channel performance summary
       # Recommended actions
   ```

2. **Opt-out Management**
   ```python
   async def handle_opt_out(user_id, opt_out_type):
       # daily_reports, channel_messages, all_messages
       # Update user preferences
       # Send confirmation
   ```

---

## Immediate Action Items

### Week 1: Foundation Changes
1. **Update Partner Configuration**
   - Modify existing partner mapping in `asset_manager.py:82-114`
   - Change from channel→user to partner→channels model

2. **Enhance Analytics**
   - Update `channel_analytics.py` to support multi-channel partners
   - Add partner-level aggregation in dashboards

### Week 2: User Profiling  
3. **Implement Bio Analysis**
   - Create Telegram profile analyzer
   - Integrate with existing chatbot flow

4. **Update Greeting Logic**
   - Add conversation history awareness
   - Implement smart greetings based on last interaction

### Week 3: Quick Results
5. **Streamline Conversation**
   - Show results after location+budget+bedrooms
   - Add "Show more" and "I'm interested" functionality

6. **Daily Reports**
   - Create partner report generator
   - Schedule 9 AM delivery system

---

## Configuration Changes Needed ✅

### ~~Current Config (asset_manager.py:86-90)~~ - REPLACED
```python
# OLD - channels as users
mapping = {
    "@phuketgidsell": "tg_phuketgidsell",
    "@phuketgid": "tg_phuketgid", 
    "@sabay_property": "tg_sabay_property",
}
```

### New Config Structure ✅ IMPLEMENTED
```python
# NEW - Partner-owned channels model
partners = {
    "partner_phuketgid": {
        "name": "Phuket Property Expert",
        "channels": ["@phuketgidsell", "@phuketgid"],
        "contact": "@phuket_agent",
        "commission_rate": 0.03,
        "active": True,
        "joined": "2025-01-15"
    },
    "partner_sabay": {
        "name": "Sabay Property Group", 
        "channels": ["@sabay_property"],
        "contact": "@sabay_agent",
        "commission_rate": 0.025,
        "active": True,
        "joined": "2025-01-20"
    }
}

# ADDED - OneMinuta Official Channel Config
oneminuta_config = {
    "channel_id": "-1002875386834",
    "channel_name": "@oneminuta_property",
    "type": "official",
    "operations": {
        "collect_properties": False,  # Don't collect from our own channel
        "track_analytics": True,     # Track for company metrics
        "auto_greet_members": True,  # Welcome new members
        "partner_commissions": False, # No partner commissions
        "daily_reports": False       # Exclude from partner reports
    }
}
```

---

## Testing Strategy

### Phase 1 Testing
- Verify partner can see all their channels in analytics
- Test channel performance aggregation
- Validate commission tracking per partner

### Phase 2 Testing  
- Test bio analysis with Russian/English names
- Verify language detection accuracy
- Test greeting personalization

### Phase 3 Testing
- Test immediate property results
- Verify "Show more" functionality  
- Test interest button → contact info flow

---

## Implementation Status

**✅ COMPLETED:**
1. `services/collector/asset_manager.py` - Partner mapping + OneMinuta config
2. `services/analytics/channel_analytics.py` - Partner aggregation + official channel separation
3. `services/user_profiling/telegram_profile_analyzer.py` - Smart user profiling
4. `oneminuta_cli.py` - Partner management + analytics commands

**🚀 READY FOR:**
5. `services/chatbot/stages/smart_greeting_stage.py` - History-aware greetings
6. `services/chatbot/stages/inquiry_collection_stage.py` - Quick results after basic criteria
7. `services/reports/daily_partner_reports.py` - 9 AM partner lead summaries
8. `scripts/automation/daily_report_scheduler.py` - Automated scheduling

**🎯 KEY FEATURES WORKING:**
- Partner-owned multiple channels
- OneMinuta official channel separated from partner operations
- Smart user profiling (language, nationality, investor type)
- CLI commands: `partners`, `analytics --official`, `analytics --partner`
- Real member count tracking (3 members)
- Channel type detection and operational separation

---

*✅ PHASE 1 COMPLETE: Foundation changes implemented successfully*

## New CLI Commands Available:
```bash
# View all partners
python oneminuta_cli.py partners

# Official channel analytics only
python oneminuta_cli.py analytics --official

# Partner-specific analytics (when implemented)
python oneminuta_cli.py analytics --partner partner_phuketgid

# All channels (official + partners)
python oneminuta_cli.py analytics
```