# booking_bot_simple.py

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class BookingBot:
    def __init__(self, token: str, admin_chat_id: str):
        self.token = token
        self.admin_chat_id = admin_chat_id
        self.data_file = "booking_data.json"
        self.log_file = "booking_logs.json"

        # Load existing data
        self.users_data = self.load_data()
        self.logs = self.load_logs()

        # User states for conversation flow
        self.user_states = {}

    def load_data(self) -> Dict[str, Any]:
        """Load user booking data from JSON file"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading data: {e}")
        return {}

    def save_data(self):
        """Save user booking data to JSON file"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.users_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving data: {e}")

    def load_logs(self) -> list:
        """Load booking logs from JSON file"""
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading logs: {e}")
        return []

    def save_logs(self):
        """Save booking logs to JSON file"""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(self.logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving logs: {e}")

    def add_log_entry(self, user_id: str, username: str, full_name: str,
                      change: str, total: int, status: str) -> str:
        """Add entry to booking logs"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = {
            "timestamp": timestamp,
            "user_id": user_id,
            "username": username,
            "full_name": full_name,
            "change": change,
            "total": total,
            "status": status
        }

        self.logs.append(log_entry)
        self.save_logs()
        return timestamp

    async def send_admin_notification(self, context: ContextTypes.DEFAULT_TYPE,
                                      notification_type: str, user_data: Dict, details: Dict):
        """Send notification to admin"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if notification_type == "new":
            message = (
                f"📦 <b>Nayi Booking!</b>\n"
                f"👤 User: {details['full_name']} ({details['username']})\n"
                f"🔢 Sets: {details['sets']}\n"
                f"🕒 {timestamp}"
            )
        elif notification_type == "edit":
            message = (
                f"🔄 <b>Booking Edit Hui!</b>\n"
                f"👤 User: {details['full_name']} ({details['username']})\n"
                f"🔢 Pehle: {details['before']} → Abhi: {details['after']}\n"
                f"🕒 {timestamp}"
            )
        elif notification_type == "cancel":
            message = (
                f"❌ <b>Booking Cancel Hui!</b>\n"
                f"👤 User: {details['full_name']} ({details['username']})\n"
                f"🔢 Pehle: {details['sets']} sets\n"
                f"🕒 {timestamp}"
            )

        try:
            await context.bot.send_message(
                chat_id=self.admin_chat_id,
                text=message,
                parse_mode='HTML'
            )
        except Exception as e:
            logger.error(f"Error sending admin notification: {e}")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_message = (
            "<b>Namaste! 🙏 Main aapka booking bot hoon.</b>\n\n"
            "<b>Available Commands:</b>\n"
            "📦 /book - Nayi booking karein\n"
            "✏️ /edit_book - Apni existing booking edit karein\n"
            "❌ /cancel_booking - Apni booking cancel karein\n\n"
            "Koi bhi command ka use karke shuru karein!"
        )

        await update.message.reply_text(welcome_message, parse_mode='HTML')

    async def book_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /book command"""
        user_id = str(update.effective_user.id)
        username = f"@{update.effective_user.username}" if update.effective_user.username else "No username"
        full_name = update.effective_user.full_name or "Unknown"

        # Check if user provided sets directly
        if context.args:
            try:
                sets = int(context.args[0])
                if sets <= 0:
                    await update.message.reply_text("Kripya positive number mein sets enter karein. Example: <code>/book 5</code>", parse_mode='HTML')
                    return

                # Process booking
                await self.process_booking(update, context, user_id, username, full_name, sets)
                return

            except ValueError:
                await update.message.reply_text("Kripya number mein value enter karein. Example: <code>/book 5</code>", parse_mode='HTML')
                return

        # Ask for number of sets
        self.user_states[user_id] = {
            'action': 'booking',
            'username': username,
            'full_name': full_name
        }

        await update.message.reply_text("Kitne sets book karne hain? (Example: <code>1</code>)", parse_mode='HTML')

    async def process_booking(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                            user_id: str, username: str, full_name: str, sets: int):
        """Process new booking"""
        # Update user data
        self.users_data[user_id] = {
            "username": username,
            "full_name": full_name,
            "sets": sets,
            "status": "active"
        }
        self.save_data()

        # Add log entry
        timestamp = self.add_log_entry(user_id, username, full_name, f"+{sets}", sets, "Booked")

        # Send admin notification
        await self.send_admin_notification(
            context, "new",
            self.users_data[user_id],
            {"full_name": full_name, "username": username, "sets": sets}
        )

        # Confirm to user
        confirmation_message = (
            f"✔️ <b>Aapki booking confirm ho gayi hai!</b>\n"
            f"📦 Total Sets: <b>{sets}</b>\n"
            f"🕒 Booking Time: {timestamp}\n\n"
            f"✅ Admin ko notify kar diya gaya hai."
        )

        await update.message.reply_text(confirmation_message, parse_mode='HTML')

        # Clear user state
        if user_id in self.user_states:
            del self.user_states[user_id]

    async def edit_book_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /edit_book command"""
        user_id = str(update.effective_user.id)
        username = f"@{update.effective_user.username}" if update.effective_user.username else "No username"
        full_name = update.effective_user.full_name or "Unknown"

        # Check if user has existing booking
        if user_id not in self.users_data or self.users_data[user_id].get("status") != "active":
            await update.message.reply_text(
                "Aapne abhi tak koi active booking nahi ki hai. Kripya <code>/book</code> command ka use karein.", parse_mode='HTML'
            )
            return

        current_sets = self.users_data[user_id]["sets"]

        # Check if change value provided directly
        if context.args:
            try:
                change = int(context.args[0])
                await self.process_edit_booking(update, context, user_id, username, full_name, change)
                return
            except ValueError:
                await update.message.reply_text("Sahi format mein batayein. Example: <code>/edit_book +2</code> ya <code>/edit_book -1</code>", parse_mode='HTML')
                return

        # Show current booking and ask for change
        keyboard = [
            [
                InlineKeyboardButton("+1", callback_data="edit_+1"),
                InlineKeyboardButton("-1", callback_data="edit_-1")
            ],
            [
                InlineKeyboardButton("+2", callback_data="edit_+2"),
                InlineKeyboardButton("-2", callback_data="edit_-2")
            ],
            [
                InlineKeyboardButton("Khud Type Karein", callback_data="edit_manual")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = (
            f"Aapne abhi <b>{current_sets}</b> set(s) book kiye hain.\n"
            f"Kitne sets add ya remove karne hain?\n"
            f"(+ve for add, -ve for remove)\n"
            f"Example: <code>+2</code> or <code>-1</code>"
        )

        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')

        # Set user state
        self.user_states[user_id] = {
            'action': 'editing',
            'username': username,
            'full_name': full_name
        }

    async def process_edit_booking(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                 user_id: str, username: str, full_name: str, change: int):
        """Process booking edit"""
        current_sets = self.users_data[user_id]["sets"]
        new_total = current_sets + change

        if new_total < 0:
            # Determine whether to use update.message.reply_text or update.callback_query.edit_message_text
            reply_func = update.message.reply_text if hasattr(update, 'message') else update.callback_query.edit_message_text
            await reply_func("Error: Total sets 0 se kam nahi ho sakte hain.")
            return

        # Update user data
        self.users_data[user_id]["sets"] = new_total
        self.save_data()

        # Add log entry
        timestamp = self.add_log_entry(
            user_id, username, full_name,
            f"{'+' if change > 0 else ''}{change}",
            new_total, "Edited"
        )

        # Send admin notification
        await self.send_admin_notification(
            context, "edit",
            self.users_data[user_id],
            {
                "full_name": full_name,
                "username": username,
                "before": current_sets,
                "after": new_total
            }
        )

        # Confirm to user
        confirmation_message = (
            f"✔️ <b>Booking Update Ho Gayi!</b>\n"
            f"Pehle: <b>{current_sets}</b> set(s)\n"
            f"Change: <b>{'Add' if change > 0 else 'Remove'} {abs(change)}</b> set(s)\n"
            f"✅ Ab Total: <b>{new_total}</b> set(s)\n"
            f"🕒 {timestamp}"
        )

        # Determine whether to use update.message.reply_text or update.callback_query.edit_message_text
        reply_func = update.message.reply_text if hasattr(update, 'message') else update.callback_query.edit_message_text
        await reply_func(confirmation_message, parse_mode='HTML')

        # Clear user state
        if user_id in self.user_states:
            del self.user_states[user_id]

    async def cancel_booking_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cancel_booking command"""
        user_id = str(update.effective_user.id)
        username = f"@{update.effective_user.username}" if update.effective_user.username else "No username"
        full_name = update.effective_user.full_name or "Unknown"

        # Check if user has active booking
        if user_id not in self.users_data or self.users_data[user_id].get("status") != "active":
            await update.message.reply_text("Aapki koi active booking nahi hai.")
            return

        current_sets = self.users_data[user_id]["sets"]

        # Show confirmation buttons
        keyboard = [
            [
                InlineKeyboardButton("✅ Haan, Cancel Karein", callback_data="cancel_yes"),
                InlineKeyboardButton("❌ Nahi, Mat Karein", callback_data="cancel_no")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        message = (
            f"Aap apni <b>{current_sets}</b> sets ki booking cancel karna chahte hain?\n"
            f"⚠️ Yah action undo nahi ho sakta hai!"
        )

        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='HTML')

        # Set user state
        self.user_states[user_id] = {
            'action': 'cancelling',
            'username': username,
            'full_name': full_name,
            'sets': current_sets
        }

    async def summary_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /summary command (Admin only)"""
        user_id = str(update.effective_user.id)

        # Check if user is admin
        if user_id != self.admin_chat_id.replace('-', ''):
            await update.message.reply_text("❌ Yeh command sirf Admin ke liye hai!")
            return

        # Generate summary
        active_bookings = []
        cancelled_bookings = []
        total_active_sets = 0

        for uid, data in self.users_data.items():
            full_name = data.get('full_name', 'Unknown')
            username = data.get('username', 'No username')
            display_name = f"{full_name} (<a href='tg://user?id={uid}'>{username}</a>)"

            if data['status'] == 'active':
                active_bookings.append(f"👤 {display_name} - <b>{data['sets']}</b> sets")
                total_active_sets += data['sets']
            else:
                cancelled_bookings.append(f"❌ {display_name} - Cancelled (Pehle: {data.get('sets_before_cancel', 'N/A')} sets)")

        summary_text = "📋 <b>Booking Summary:</b>\n\n"

        if active_bookings:
            summary_text += "<b>🚀 Active Bookings:</b>\n" + "\n".join(active_bookings)
        else:
            summary_text += "No active bookings available.\n"

        if cancelled_bookings:
            summary_text += "\n\n<b>🗑️ Cancelled Bookings:</b>\n" + "\n".join(cancelled_bookings)

        summary_text += f"\n\n<b>Total Active Sets: {total_active_sets}</b>"

        await update.message.reply_text(summary_text, parse_mode='HTML', disable_web_page_preview=True)


    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline button callbacks"""
        query = update.callback_query
        user_id = str(query.from_user.id)
        data = query.data

        await query.answer() # Acknowledge the callback query

        if user_id not in self.user_states:
            await query.edit_message_text("Session expire ho gaya hai. Kripya command fir se try karein.")
            return

        user_state = self.user_states[user_id]
        username = user_state['username']
        full_name = user_state['full_name']

        if data.startswith("edit_"):
            if data == "edit_manual":
                await query.edit_message_text("Kitne sets add ya remove karne hain? (Example: <code>+2</code> or <code>-1</code>)", parse_mode='HTML')
            else:
                # Handle edit booking buttons
                change = int(data.replace("edit_", ""))
                await self.process_edit_booking(query, context, user_id, username, full_name, change)

        elif data == "cancel_yes":
            # Handle booking cancellation confirmation
            await self.process_cancel_booking(query, context, user_id, username, full_name)

        elif data == "cancel_no":
            # Handle booking cancellation rejection
            await query.edit_message_text("✅ Aapki booking bani rahegi. Cancel nahi hui.")
            if user_id in self.user_states:
                del self.user_states[user_id]

    async def process_edit_booking_callback(self, query, context: ContextTypes.DEFAULT_TYPE,
                                      user_id: str, username: str, full_name: str, change: int):
        """Process edit booking from callback"""
        current_sets = self.users_data[user_id]["sets"]
        new_total = current_sets + change

        if new_total < 0:
            await query.edit_message_text("Error: Total sets 0 se kam nahi ho sakta.")
            return

        # Update user data
        self.users_data[user_id]["sets"] = new_total
        self.save_data()

        # Add log entry
        timestamp = self.add_log_entry(
            user_id, username, full_name,
            f"{'+' if change > 0 else ''}{change}",
            new_total, "Edited"
        )

        # Send admin notification
        await self.send_admin_notification(
            context, "edit",
            self.users_data[user_id],
            {
                "full_name": full_name,
                "username": username,
                "before": current_sets,
                "after": new_total
            }
        )

        # Update message
        confirmation_message = (
            f"✔️ <b>Booking Update Ho Gayi!</b>\n"
            f"Pehle: <b>{current_sets}</b> set(s)\n"
            f"Change: <b>{'Add' if change > 0 else 'Remove'} {abs(change)}</b> set(s)\n"
            f"✅ Ab Total: <b>{new_total}</b> set(s)\n"
            f"🕒 {timestamp}"
        )

        await query.edit_message_text(confirmation_message, parse_mode='HTML')

        # Clear user state
        if user_id in self.user_states:
            del self.user_states[user_id]

    async def process_cancel_booking(self, query, context: ContextTypes.DEFAULT_TYPE,
                               user_id: str, username: str, full_name: str):
        """Process booking cancellation"""
        current_sets = self.users_data[user_id]["sets"]

        # Update user data
        self.users_data[user_id]["status"] = "cancelled"
        self.users_data[user_id]["sets_before_cancel"] = current_sets # Store sets before cancelling
        self.users_data[user_id]["sets"] = 0 # Set current sets to 0
        self.save_data()

        # Add log entry
        timestamp = self.add_log_entry(
            user_id, username, full_name,
            f"-{current_sets}", 0, "Cancelled"
        )

        # Send admin notification
        await self.send_admin_notification(
            context, "cancel",
            self.users_data[user_id],
            {
                "full_name": full_name,
                "username": username,
                "sets": current_sets
            }
        )

        # Update message
        confirmation_message = (
            f"❌ <b>Aapki booking cancel ho gayi hai.</b>\n"
            f"🕒 {timestamp}\n\n"
            f"✅ Admin ko notify kar diya gaya hai."
        )

        await query.edit_message_text(confirmation_message, parse_mode='HTML')

        # Clear user state
        if user_id in self.user_states:
            del self.user_states[user_id]

    async def handle_text_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text messages (for booking quantity input)"""
        user_id = str(update.effective_user.id)

        if user_id not in self.user_states:
            await update.message.reply_text(
                "Kripya pehle koi command use karein, jaise:\n"
                "<code>/book</code>, <code>/edit_book</code>, ya <code>/cancel_booking</code>", parse_mode='HTML'
            )
            return

        user_state = self.user_states[user_id]

        if user_state['action'] == 'booking':
            # Handle booking quantity input
            try:
                sets = int(update.message.text.strip())
                if sets <= 0:
                    await update.message.reply_text("Kripya positive number mein sets bataye.")
                    return

                await self.process_booking(
                    update, context, user_id,
                    user_state['username'], user_state['full_name'], sets
                )

            except ValueError:
                await update.message.reply_text("Sahi Number bataye.")

        elif user_state['action'] == 'editing':
            # Handle edit value input
            try:
                change_text = update.message.text.strip()
                change = int(change_text)

                await self.process_edit_booking(
                    update, context, user_id,
                    user_state['username'], user_state['full_name'], change
                )

            except ValueError:
                await update.message.reply_text("Sahi format mein batayein. Example: <code>+2</code> or <code>-1</code>", parse_mode='HTML')

    async def error_handler(self, update: object, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Exception while handling an update: {context.error}")
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "Kuch error ho gaya hai! Kripya dobara try karein ya admin se contact karein."
            )

    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /reset command (Admin only)"""
        user_id = str(update.effective_user.id)

        # Check admin
        if user_id != self.admin_chat_id.replace("-", ""):
            await update.message.reply_text("❌ Yeh command sirf Admin hi use kar sakte hain!")
            return

        # Confirmation for reset
        keyboard = [
            [
                InlineKeyboardButton("✅ Haan, Reset Karein", callback_data="reset_confirm"),
                InlineKeyboardButton("❌ Nahi, Cancel Karein", callback_data="reset_cancel")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "⚠️ <b>Kya aap sabhi bookings reset karna chahte hain?</b>\n"
            "Yah action saari data mita dega aur undo nahi ho sakta.",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

        # Set user state for reset confirmation
        self.user_states[user_id] = {'action': 'reset_confirmation'}
            # --- Custom Message Command (Username se) ---
    async def send_message_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Admin ko custom message bhejne ka command (username se)."""
        admin_id = str(update.effective_user.id)

        # Check karein ki command admin ne hi use kiya hai
        if admin_id != self.admin_chat_id.replace("-", ""):
            await update.message.reply_text("❌ Yeh command sirf Admin hi use kar sakte hain!")
            return

        # Check karein ki command mein username aur message provide kiya gaya hai
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Sahi format use karein: <code>/send_message &lt;username&gt; &lt;You msg&gt;</code>\n"
                "Example: <code>/send_message @example_user Hello!</code>",
                parse_mode='HTML'
            )
            return

        target_username_input = context.args[0].lower() # Input username ko lowercase mein convert karein
        message_text = " ".join(context.args[1:])
        
        target_user_id = None
        found_user_data = None

        # users_data mein username se user ID dhoondein
        for user_id, user_data in self.users_data.items():
            stored_username = user_data.get('username')
            if stored_username and stored_username.lower() == target_username_input:
                target_user_id = user_id
                found_user_data = user_data
                break # Pehla match milte hi ruk jayenge

        if not target_user_id:
            await update.message.reply_text(
                f"❌ User <b>{target_username_input}</b> nahi mila. Kripya sahi username enter karein ya confirm karein ki us user ne bot se pehle interact kiya hai.",
                parse_mode='HTML'
            )
            logger.warning(f"Admin {admin_id} tried to send message to unknown username: {target_username_input}")
            return

        try:
            # User ko message bhejein
            await context.bot.send_message(
                chat_id=target_user_id,
                text=message_text,
                parse_mode='HTML' # Agar aap HTML formatting support karna chahte hain
            )
            await update.message.reply_text(f"✔️ Message user <b>{target_username_input}</b> (ID: {target_user_id}) ko bhej diya gaya hai.", parse_mode='HTML')
            logger.info(f"Admin {admin_id} sent custom message to user {target_username_input} (ID: {target_user_id}).")

        except Exception as e:
            await update.message.reply_text(f"❌ Message bhejte waqt error aaya: {e}\nKripya user ID check karein ya message mein koi invalid HTML tag na ho.", parse_mode='HTML')
            logger.error(f"Error sending custom message to {target_username_input} (ID: {target_user_id}): {e}")

    # --- End of Custom Message Command (Username se) ---



    # --- End of Naya Custom Message Command ---


    async def reset_confirmation_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle reset confirmation callback"""
        query = update.callback_query
        user_id = str(query.from_user.id)
        data = query.data

        await query.answer()

        if user_id not in self.user_states or self.user_states[user_id].get('action') != 'reset_confirmation':
            await query.edit_message_text("Session expired ya invalid action. Kripya <code>/reset</code> command fir se try karein.")
            return

        if data == "reset_confirm":
            # Reset all data
            self.users_data = {}
            self.logs = []
            self.save_data()
            self.save_logs()

            await query.edit_message_text(
                "🔁 <b>Sabhi bookings reset kar di gayi hain!</b>\n"
                "Ab nayi bookings ki ja sakti hain.",
                parse_mode='HTML'
            )
            logger.info(f"Admin {user_id} reset all booking data.")
        elif data == "reset_cancel":
            await query.edit_message_text("✅ Reset process cancel kar diya gaya hai.")

        if user_id in self.user_states:
            del self.user_states[user_id]
            
            

    def run(self):
        """Start the bot"""
        # Create application
        application = Application.builder().token(self.token).build()

        # Add handlers
        application.add_handler(CommandHandler("start", self.start_command))
        application.add_handler(CommandHandler("book", self.book_command))
        application.add_handler(CommandHandler("edit_book", self.edit_book_command))
        application.add_handler(CommandHandler("cancel_booking", self.cancel_booking_command))
        application.add_handler(CommandHandler("summary", self.summary_command))
        application.add_handler(CommandHandler("reset", self.reset_command))
        
        # Naya Command Handler add kiya gaya hai
        application.add_handler(CommandHandler("send_message", self.send_message_command))
        # --- End of Naya Command Handler ---

        application.add_handler(CallbackQueryHandler(self.button_callback, pattern="^(edit_|cancel_)"))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text_message))
        application.add_handler(CallbackQueryHandler(self.reset_confirmation_callback, pattern="^reset_"))
        application.add_error_handler(self.error_handler)


        logger.info("Bot started successfully!")
        print("🚀 Booking Bot is running...")
        print("Commands available: /book, /edit_book, /cancel_booking, /summary, /reset (Admin only)")
        # Naya Command bhi print karein
        print("Admin Commands: /summary, /reset, /send_message <user_id> <message>")

        # Start polling
        application.run_polling()

    

# --- BOT KO YAHAN RUN KAREIN ---

if __name__ == '__main__':
    # >>>>>>>>>>>>>>> YAHAN APNA BOT TOKEN AUR ADMIN CHAT ID DALEIN <<<<<<<<<<<<<<<
    # BotFather se mila hua token
    BOT_TOKEN = "7455285894:AAHc8rcRE7xe9Vda2SkjhureaqA49yynxjQ" # Example: "1234567890:ABCDEFGHIJ-KLMNOPQRSTUVWXYZabcdefghij"

    # Jis chat ID par admin notifications chahiye (apni khud ki chat ID ya group ID)
    # Chat ID pata karne ke liye Telegram par @RawDataBot ko message karein.
    ADMIN_CHAT_ID = "5168899073" # Example: "123456789" (private chat) or "-1234567890123" (group chat)

    # Validate ki values provide ki gayi hain
    if BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN_HERE" or not BOT_TOKEN:
        print("ERROR: Kripya 'BOT_TOKEN' ki value ko apne actual Telegram bot token se badlein.")
        exit(1)
    if ADMIN_CHAT_ID == "YOUR_ADMIN_CHAT_ID_HERE" or not ADMIN_CHAT_ID:
        print("ERROR: Kripya 'ADMIN_CHAT_ID' ki value ko apne actual admin chat ID se badlein.")
        exit(1)

    # Bot ko initialize aur run karein
    bot = BookingBot(BOT_TOKEN, ADMIN_CHAT_ID)
    bot.run()

     