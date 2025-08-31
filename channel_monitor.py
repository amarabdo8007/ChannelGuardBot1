"""
Channel Monitor Module
Monitors channel activities and member changes
"""

import logging
from datetime import datetime
from telegram import ChatMember, Update
from telegram.ext import ContextTypes

class ChannelMonitor:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.monitored_events = []
    
    def is_member_ban(self, old_status, new_status):
        """Check if a member status change represents a ban"""
        ban_transitions = [
            ('member', 'kicked'),
            ('restricted', 'kicked'),
            ('left', 'kicked')
        ]
        return (old_status, new_status) in ban_transitions
    
    def is_admin_action(self, chat_member_update):
        """Check if the update was performed by an admin"""
        return chat_member_update.from_user is not None
    
    def log_member_change(self, chat_id, user_id, old_status, new_status, admin_id=None):
        """Log member status changes"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'chat_id': chat_id,
            'user_id': user_id,
            'old_status': old_status,
            'new_status': new_status,
            'admin_id': admin_id,
            'event_type': 'member_change'
        }
        
        self.monitored_events.append(event)
        self.logger.info(f"Member status change logged: {event}")
        
        # Keep only recent events (last 1000)
        if len(self.monitored_events) > 1000:
            self.monitored_events = self.monitored_events[-1000:]
    
    def get_recent_bans(self, chat_id, limit=10):
        """Get recent ban events for a specific chat"""
        ban_events = [
            event for event in self.monitored_events
            if (event['chat_id'] == chat_id and 
                event['new_status'] == 'kicked' and
                event['old_status'] in ['member', 'restricted'])
        ]
        
        # Sort by timestamp (most recent first)
        ban_events.sort(key=lambda x: x['timestamp'], reverse=True)
        return ban_events[:limit]
    
    def get_admin_ban_count(self, admin_id, chat_id, hours=24):
        """Get the number of bans performed by an admin in the last X hours"""
        from datetime import datetime, timedelta
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        ban_count = 0
        for event in self.monitored_events:
            event_time = datetime.fromisoformat(event['timestamp'])
            if (event['admin_id'] == admin_id and 
                event['chat_id'] == chat_id and
                event['new_status'] == 'kicked' and
                event_time > cutoff_time):
                ban_count += 1
        
        return ban_count
    
    def is_suspicious_activity(self, admin_id, chat_id):
        """Check if an admin is showing suspicious banning behavior"""
        recent_bans = self.get_admin_ban_count(admin_id, chat_id, hours=1)
        
        # Consider it suspicious if more than 5 bans in 1 hour
        return recent_bans > 5
    
    async def handle_chat_member_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle chat member updates (join/leave/status changes)"""
        try:
            if not update.chat_member:
                return
                
            chat_member = update.chat_member
            user = chat_member.from_user
            chat = update.effective_chat
            
            if not user or not chat:
                return
            
            old_status = chat_member.old_chat_member.status if chat_member.old_chat_member else "unknown"
            new_status = chat_member.new_chat_member.status if chat_member.new_chat_member else "unknown"
            
            # Log the member change
            self.log_member_change(
                chat_id=chat.id,
                user_id=user.id, 
                old_status=old_status,
                new_status=new_status,
                admin_id=chat_member.from_user.id if chat_member.from_user else None
            )
            
            # Monitor admin changes
            if new_status in ["administrator", "creator"]:
                self.logger.info(f"✅ {user.full_name} تم ترقيته لأدمن في {chat.title}")
            elif old_status in ["administrator", "creator"] and new_status in ["member", "left", "kicked"]:
                self.logger.info(f"❌ {user.full_name} تم إزالته من الأدمن في {chat.title}")
            elif self.is_member_ban(old_status, new_status):
                self.logger.warning(f"🚫 {user.full_name} تم حظره في {chat.title}")
                
        except Exception as e:
            self.logger.error(f"Error handling chat member update: {e}")
