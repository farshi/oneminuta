#!/usr/bin/env python3
"""
OneMinuta Telegram Bot with Channel Integration
Supports auto-greeting new channel members and partner channel integration
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from telegram import Update, ChatMember
    from telegram.ext import (
        Application, 
        CommandHandler, 
        MessageHandler, 
        ChatMemberHandler,
        filters, 
        ContextTypes
    )
    from telegram.constants import ChatMemberStatus
except ImportError:
    print("❌ python-telegram-bot not installed. Installing now...")
    os.system("pip install python-telegram-bot")
    from telegram import Update, ChatMember
    from telegram.ext import (
        Application, 
        CommandHandler, 
        MessageHandler, 
        ChatMemberHandler,
        filters, 
        ContextTypes
    )
    from telegram.constants import ChatMemberStatus

from services.chatbot.chatbot_manager import OneMinutaChatbotManager
from services.analytics.channel_analytics import ChannelAnalytics, MemberEventType

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class OneMinutaChannelBot:
    def __init__(self, token: str, openai_api_key: str, storage_path: str = "./storage"):
        self.token = token
        self.storage_path = storage_path
        
        # Initialize OneMinuta chatbot
        self.chatbot = OneMinutaChatbotManager(storage_path, openai_api_key)
        
        # Initialize Channel Analytics
        self.analytics = ChannelAnalytics(storage_path)
        
        # Initialize Telegram bot
        self.application = Application.builder().token(token).build()
        self.setup_handlers()
        
        # Partner channels (to be configured)
        self.partner_channels = self.load_partner_channels()
    
    def load_partner_channels(self):
        """Load partner channel configurations"""
        # This can be loaded from config file or database
        return {
            # Channel ID: Channel Info
            # -1001234567890: {
            #     "name": "Phuket Properties",
            #     "welcome_template": "phuket_welcome",
            #     "auto_greet": True
            # }
        }
    
    def setup_handlers(self):
        """Setup command and message handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("reset", self.reset_command))
        self.application.add_handler(CommandHandler("stats", self.stats_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("channels", self.channels_command))
        self.application.add_handler(CommandHandler("join", self.simulate_join_command))
        self.application.add_handler(CommandHandler("analytics", self.analytics_command))
        
        # Channel member updates (for auto-greeting new members)
        self.application.add_handler(ChatMemberHandler(self.handle_member_update, ChatMemberHandler.CHAT_MEMBER))
        
        # Message handler for chatbot conversation
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
    
    async def handle_member_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle new members joining partner channels"""
        try:
            chat_member_update = update.chat_member
            chat = chat_member_update.chat
            user = chat_member_update.new_chat_member.user
            old_status = chat_member_update.old_chat_member.status
            new_status = chat_member_update.new_chat_member.status
            
            # Check if someone joined a partner channel
            if (chat.id in self.partner_channels and 
                old_status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED] and
                new_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.OWNER]):
                
                # Don't greet bots or the bot itself
                if user.is_bot or user.id == context.bot.id:
                    return
                
                channel_info = self.partner_channels[chat.id]
                
                # Track new member join in analytics
                await self.analytics.track_member_event(
                    channel_id=str(chat.id),
                    channel_name=chat.title or channel_info.get("name", "Unknown"),
                    user_id=str(user.id),
                    event_type=MemberEventType.JOINED,
                    username=user.username,
                    metadata={
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "is_premium": getattr(user, 'is_premium', False)
                    }
                )
                
                # Sync real member count after tracking event
                await self.analytics.sync_real_member_count(str(chat.id), context.bot)
                logger.info(f"Tracked new member join: {user.username or user.id} in {chat.title}")
                
                if channel_info.get("auto_greet", True):
                    await self.send_welcome_dm(user, chat, channel_info)
            
            # Track member leaving
            elif (chat.id in self.partner_channels and
                  old_status in [ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR] and
                  new_status in [ChatMemberStatus.LEFT, ChatMemberStatus.BANNED]):
                
                await self.analytics.track_member_event(
                    channel_id=str(chat.id),
                    channel_name=chat.title or "Unknown",
                    user_id=str(user.id),
                    event_type=MemberEventType.LEFT if new_status == ChatMemberStatus.LEFT else MemberEventType.BANNED,
                    username=user.username
                )
                
                # Sync real member count after tracking event
                await self.analytics.sync_real_member_count(str(chat.id), context.bot)
                logger.info(f"Tracked member leave: {user.username or user.id} from {chat.title}")
                    
        except Exception as e:
            logger.error(f"Error handling member update: {e}")
    
    async def send_welcome_dm(self, user, channel, channel_info):
        """Send personalized welcome DM to new channel member"""
        try:
            # Get user's first name or username
            user_name = user.first_name or user.username or "there"
            channel_name = channel_info.get("name", channel.title)
            
            # Create personalized welcome message using AI
            welcome_context = f"""
            User joined channel: {channel_name}
            User name: {user_name}
            Create a warm, professional welcome message that:
            1. Greets them by name
            2. Welcomes them to the channel
            3. Introduces OneMinuta as property search assistant
            4. Asks what they're looking for (villa, condo, apartment)
            5. Keep it brief and friendly
            6. End with a simple question to engage them
            """
            
            # Generate AI welcome message
            ai_welcome = await self.chatbot.generate_welcome_message(user.id, welcome_context)
            
            if not ai_welcome:
                # Fallback welcome message
                ai_welcome = f"""Hi {user_name}! 👋

Welcome to {channel_name}! 

I'm OneMinuta - your AI property assistant for Thailand. I help people find perfect condos, villas, and apartments.

What brings you to the property market today? Looking for something specific? 🏡"""

            # Send DM to user
            await self.application.bot.send_message(
                chat_id=user.id,
                text=ai_welcome
            )
            
            logger.info(f"Sent welcome DM to {user_name} ({user.id}) from channel {channel_name}")
            
        except Exception as e:
            logger.warning(f"Could not send welcome DM to {user.id}: {e}")
            # This is normal - user might not have started the bot yet
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        user_name = user.first_name or user.username or "there"
        
        welcome_msg = f"""Hi {user_name}! 🏠 Welcome to OneMinuta!

I'm your AI property assistant for Thailand. I help you find perfect properties quickly and easily.

🎯 **What I can do:**
• Find condos, villas, apartments for rent or sale
• Search by location, budget, bedrooms
• Support English and Russian
• Connect you with verified agents

🚀 **Quick start:**
Just tell me what you're looking for!

**Examples:**
• "I need a 2-bedroom condo in Phuket under 30k"
• "Looking for villa in Rawai for investment"
• "Ищу квартиру в Бангкоке для аренды"

**Commands:**
• /reset - Start over
• /stats - Your search history
• /channels - Partner channels
• /join - Test channel welcome (for demo)
• /help - More info

What can I help you find today? 🌴"""
        
        await update.message.reply_text(welcome_msg)
        
        # Reset conversation for clean start
        user_id = str(update.effective_user.id)
        await self.chatbot.reset_conversation(user_id)
        
        logger.info(f"User {user.username or user_id} started conversation")
    
    async def channels_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show partner channels information"""
        channels_msg = """🤝 **OneMinuta Partner Channels**

Find us in these verified property channels:

🏖️ **Phuket Properties** - @phuket_properties
🏙️ **Bangkok Condos** - @bangkok_condos  
🌴 **Koh Samui Villas** - @samui_villas
🏡 **Thailand Property Hub** - @thailand_property

💡 **Join these channels for:**
• Latest property listings
• Market insights
• Investment opportunities
• Direct agent contacts

When you join any partner channel, I'll automatically help you find what you're looking for! 🎯"""

        await update.message.reply_text(channels_msg)
    
    async def simulate_join_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Simulate joining OneMinuta Property channel for testing"""
        user = update.effective_user
        user_name = user.first_name or user.username or "there"
        
        await update.message.reply_text("🧪 **Testing Channel Join Experience...**")
        
        # Simulate the channel info
        channel_info = {
            "name": "OneMinuta Property Thailand",
            "welcome_template": "oneminuta_welcome",
            "auto_greet": True
        }
        
        # Create a mock channel object
        class MockChannel:
            def __init__(self):
                self.id = -1002875386834
                self.title = "OneMinuta Property Thailand"
        
        mock_channel = MockChannel()
        
        # Send the welcome DM (same as real channel join)
        try:
            await self.send_welcome_dm(user, mock_channel, channel_info)
            
            success_msg = f"""✅ **Simulated Channel Join Complete!**

🎯 **What happened:**
• You "joined" @oneminuta_property 
• Bot sent you a personalized welcome DM
• AI generated context-aware greeting
• Ready to start property conversation

This is exactly what happens when real users join your channel!

💡 **Try responding to the welcome message to test the full flow.**"""
            
            await update.message.reply_text(success_msg)
            
        except Exception as e:
            error_msg = f"""❌ **Test failed:** {e}

This usually means:
• Bot needs permission to send you messages
• You haven't started a conversation with the bot yet

💡 **Try:**
1. Send /start first
2. Then use /join again"""
            
            await update.message.reply_text(error_msg)
    
    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reset command"""
        user_id = str(update.effective_user.id)
        success = await self.chatbot.reset_conversation(user_id)
        
        if success:
            await update.message.reply_text("🔄 Your conversation has been reset. What are you looking for today?")
        else:
            await update.message.reply_text("❌ Failed to reset conversation. Please try again.")
        
        logger.info(f"User {update.effective_user.username or user_id} reset conversation")
    
    async def stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user_id = str(update.effective_user.id)
        stats = await self.chatbot.get_user_stats(user_id)
        
        if stats:
            stats_msg = f"""📊 Your OneMinuta Activity:
            
🗣️ **Messages:** {stats.get('message_count', 0)}
📍 **Current stage:** {stats.get('current_stage', 'Not started')}
⏰ **Session time:** {stats.get('session_duration', 'N/A')}
💾 **Data collected:** {len(stats.get('collected_data', {}))} items
📅 **Last active:** {stats.get('last_activity', 'N/A')}
🎯 **Properties viewed:** {stats.get('properties_viewed', 0)}"""
        else:
            stats_msg = "📊 No activity yet! Send me a message to start your property search."
        
        await update.message.reply_text(stats_msg)
    
    async def analytics_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Display channel analytics"""
        user = update.effective_user
        
        # Check if user is admin (you might want to restrict this)
        # For now, showing basic analytics to everyone
        
        try:
            # Get analytics for all partner channels
            if self.partner_channels:
                analytics_msg = "📊 **Channel Analytics Dashboard**\n\n"
                
                for channel_id, channel_info in self.partner_channels.items():
                    # First sync with real Telegram member count
                    await self.analytics.sync_real_member_count(str(channel_id), self.application.bot)
                    
                    # Get updated metrics
                    metrics = await self.analytics.get_channel_metrics(
                        str(channel_id), 
                        channel_info.get("name", "Unknown"),
                        self.application.bot
                    )
                    
                    # Format metrics
                    growth_emoji = "📈" if metrics.daily_growth_rate > 0 else "📉" if metrics.daily_growth_rate < 0 else "➡️"
                    health_emoji = "🟢" if metrics.channel_health_score > 70 else "🟡" if metrics.channel_health_score > 40 else "🔴"
                    
                    channel_stats = f"""**{channel_info.get('name', 'Channel')}**
{health_emoji} Health: {metrics.channel_health_score:.0f}/100
👥 Total Members: {metrics.total_members}
{growth_emoji} Growth Today: {metrics.new_members_today} joined, {metrics.left_members_today} left
📊 Growth Rate: {metrics.daily_growth_rate:.1f}% daily, {metrics.weekly_growth_rate:.1f}% weekly
🔥 Hot Leads: {metrics.hot_leads_generated}
⚡ Active Members: {metrics.active_members}

"""
                    analytics_msg += channel_stats
                
                # Add summary
                analytics_msg += """📈 **Growth Tips:**
• Best time to post: Check peak join hours
• Improve retention with engaging content
• Use /analytics regularly to track progress

🔗 **Partner Program:**
Earn commissions on property transactions!
Contact @oneminuta_partners to learn more."""
                
            else:
                analytics_msg = """📊 **No Analytics Available**

No partner channels configured yet.

**Want to track your channel?**
1. Add @oneminuta_bot as admin
2. Contact @oneminuta_partners
3. Start earning from your community!"""
            
            await update.message.reply_text(analytics_msg)
            
        except Exception as e:
            logger.error(f"Error getting analytics: {e}")
            await update.message.reply_text("❌ Error loading analytics. Please try again later.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_msg = """🤖 **OneMinuta Help Center**

**🎯 How to search:**
Just tell me what you want in natural language!

**📝 Examples:**
• "2-bedroom condo in Phuket under 25k"
• "Villa with pool in Rawai for sale"
• "Cheap apartment near BTS in Bangkok"
• "Investment property in Koh Samui"

**🌐 Languages:** English, русский

**📍 Locations:** Phuket, Bangkok, Pattaya, Koh Samui, Hua Hin, Chiang Mai

**🏡 Property Types:** Condos, Villas, Apartments, Houses, Land

**💰 Services:** Rent, Sale, Investment advice

**🚀 Commands:**
• `/start` - Begin new search
• `/reset` - Clear history  
• `/stats` - View your activity
• `/analytics` - Channel growth analytics
• `/channels` - Partner channels
• `/join` - Test channel join experience
• `/help` - This message

**Need human help?** I'll connect you with our verified agents! 👥"""
        
        await update.message.reply_text(help_msg)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular text messages"""
        user_id = str(update.effective_user.id)
        user_message = update.message.text
        username = update.effective_user.username or update.effective_user.first_name or user_id
        
        logger.info(f"Processing message from {username}: {user_message[:50]}...")
        
        try:
            # Send typing action
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
            
            # Process message through chatbot
            result = await self.chatbot.process_message(user_id, user_message)
            
            # Send response
            if result and result.get('reply'):
                await update.message.reply_text(result['reply'])
                
                logger.info(f"Response sent to {username}")
                
                # If conversation is complete, show next steps
                if result.get('session_complete'):
                    completion_msg = """✅ **Search Complete!**
                    
🎯 I've collected your requirements. Our verified agents will contact you within 24 hours with matching properties.

**What's next:**
📞 Agent will call/message you
📧 Receive property shortlist  
🏠 Schedule viewings
💬 Continue chatting anytime!

**Quick actions:**
• /start - New search
• /stats - View this search
• /channels - Join partner channels

Thank you for using OneMinuta! 🌴"""
                    await update.message.reply_text(completion_msg)
            else:
                # Fallback response
                await update.message.reply_text(
                    "I didn't quite catch that. Could you tell me more about what property you're looking for? 🏡"
                )
                
        except Exception as e:
            logger.error(f"Error processing message from {username}: {e}")
            await update.message.reply_text(
                "Sorry, I had a technical hiccup! Please try again or use /reset to start over. 🔧"
            )
    
    def add_partner_channel(self, channel_id: int, channel_info: dict):
        """Add a new partner channel"""
        self.partner_channels[channel_id] = channel_info
        logger.info(f"Added partner channel: {channel_info.get('name', channel_id)}")
    
    async def start_bot(self):
        """Start the bot"""
        logger.info("🤖 Starting OneMinuta Channel Bot...")
        logger.info(f"Bot token: {self.token[:10]}...")
        logger.info(f"Storage path: {self.storage_path}")
        logger.info(f"Partner channels: {len(self.partner_channels)}")
        
        # Start polling
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling()
        
        logger.info("✅ Bot started! Ready for channel integration")
        logger.info("🔗 Add bot to partner channels as admin to enable auto-greeting")
        logger.info("Press Ctrl+C to stop")
        
        # Keep running until interrupted
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
    
    async def stop_bot(self):
        """Stop the bot"""
        logger.info("Stopping bot...")
        await self.application.stop()

async def main():
    """Main function"""
    # Check environment variables
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    openai_key = os.getenv('OPENAI_API_KEY')
    storage_path = os.getenv('STORAGE_PATH', './storage')
    
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env file")
        return
    
    if not openai_key:
        print("❌ OPENAI_API_KEY not found in .env file")
        return
    
    print("🤖 OneMinuta Channel Integration Bot")
    print("=" * 50)
    print(f"📁 Storage: {storage_path}")
    print(f"🔑 OpenAI Model: {os.getenv('LLM_MODEL', 'gpt-4o-mini')}")
    print(f"🤝 Channel Integration: Enabled")
    print("=" * 50)
    
    # Create and start bot
    bot = OneMinutaChannelBot(bot_token, openai_key, storage_path)
    
    # Add your OneMinuta Property channel
    bot.add_partner_channel(-1002875386834, {
        "name": "OneMinuta Property Thailand",
        "welcome_template": "oneminuta_welcome",
        "auto_greet": True
    })
    
    try:
        await bot.start_bot()
    except KeyboardInterrupt:
        print("\n🛑 Stopping bot...")
        await bot.stop_bot()
        print("✅ Bot stopped")

if __name__ == "__main__":
    asyncio.run(main())