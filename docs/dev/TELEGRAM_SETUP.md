# 📱 Telegram Setup for 5-Day Historical Analysis

Your OneMinuta analytics system can now analyze messages from the **last 5 days** (or any period) from your Telegram channels. Here's how to set it up:

## 🔑 Step 1: One-Time Authentication

Run this **once** to authenticate with Telegram:

```bash
python authenticate_telegram.py
```

**What it asks for:**
1. **Phone number** (international format): `+1234567890`
2. **Verification code** sent to your Telegram app

**Result:** Creates `oneminuta_session.session` file for future use.

## 🚀 Step 2: Analyze Your Channels

Once authenticated, you can run these commands:

### **Analyze Last 5 Days:**
```bash
python -m services.analytics.cli monitor --analyze-history --days-back 5
```

### **Analyze Last 7 Days:**
```bash
python -m services.analytics.cli monitor --analyze-history --days-back 7
```

### **Analyze Last 30 Days:**
```bash
python -m services.analytics.cli monitor --analyze-history --days-back 30
```

### **Limit Messages + Time Period:**
```bash
# Last 3 days, max 500 messages per channel
python -m services.analytics.cli monitor --analyze-history --days-back 3 --history-limit 500
```

## 📊 Your Channels Being Analyzed

The system will analyze these channels:
- `@phuketgidsell` - English speakers
- `@phuketgid` - English speakers  
- `@sabay_property` - Russian speakers

## 🔥 What It Finds

**Hot Clients Examples:**
- "Looking for villa in Rawai, budget 6M THB, cash ready!" → **Score: 87/100**
- "Срочно ищу студию в Паттайе до $50k" → **Score: 92/100**
- "Need 2br condo near beach, can view this weekend" → **Score: 78/100**

## 📈 View Results

**List Hot Clients:**
```bash
python -m services.analytics.cli hot-clients --min-score 70 --verbose
```

**Generate Report:**
```bash
python -m services.analytics.cli report --save
```

**Analyze Specific Client:**
```bash
python -m services.analytics.cli analyze user123 --username @property_hunter
```

## 🎯 Expected Output

```
🔥 HOT CLIENTS (Score >= 70)
1. 🔥 user_12345 | Score: 92 | Buying | Budget: $150,000 | Phuket
   Intent confidence: 0.95 | Urgency: urgent | Lang: en
   Signals: 💰 Financing 🏠 Viewing 📞 Contact

2. ⚡ user_67890 | Score: 78 | Renting | Pattaya
   Intent confidence: 0.82 | Urgency: high | Lang: ru
   Signals: 🏠 Viewing 📞 Contact
```

## 🔧 Troubleshooting

**"Please enter phone number" appears:**
- You need to run `python authenticate_telegram.py` first

**"Channel not found" errors:**
- Channel might be private or username changed
- Check channel exists: `@phuketgidsell`, `@phuketgid`, `@sabay_property`

**"Database locked" errors:**
- Multiple sessions running - wait a moment and try again
- Delete old session files: `rm -f *.session` and re-authenticate

**No messages found:**
- Channels might have no activity in the specified time period
- Try increasing `--days-back` parameter
- Check if bot has access to read channel history

## 📅 Date Range Examples

| Command | Time Period | Use Case |
|---------|-------------|----------|
| `--days-back 1` | Last 24 hours | Daily hot leads |
| `--days-back 3` | Last 3 days | Weekend activity |
| `--days-back 7` | Last week | Weekly analysis |
| `--days-back 30` | Last month | Monthly trends |

## 🚨 Real-Time Monitoring

After historical analysis, start real-time monitoring:

```bash
python -m services.analytics.cli monitor
```

This will:
- ✅ Analyze new messages as they arrive
- 🚨 Generate alerts for hot clients
- 📊 Update analytics in real-time

## 📊 Success Metrics

**What indicates successful analysis:**
- `✅ Found X messages from last 5 days`
- `🔥 Hot client detected: @username (Score: 85/100)`
- `📊 Analyzed Y messages from @channel`

**Expected results from active channels:**
- 50-200 messages per week per channel
- 5-15% hot clients (score ≥ 70)
- 1-3% burning clients (score ≥ 85)

## 🎯 Next Steps

1. **Run authentication**: `python authenticate_telegram.py`
2. **Test 5-day analysis**: `python -m services.analytics.cli monitor --analyze-history --days-back 5`
3. **Check results**: `python -m services.analytics.cli hot-clients`
4. **Set up real-time monitoring**: `python -m services.analytics.cli monitor`
5. **Integrate with your CRM**: Use JSON APIs for client data