TEXTS = {
    "welcome": (
        "Welcome <b>{name}</b>! 👋\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "🚀 <b>Autopost bot creator platform</b>\n\n"
        "📋 <b>Your bot features:</b>\n"
        "• 🔄 Auto-posting — from 5 min to 1 hour\n"
        "• ⏰ Flexible intervals: 5m, 15m, 30m, 1 hour\n"
        "• 📣 Private, groups, channels or all\n"
        "• 📢 Mass broadcast\n"
        "• 📋 Mandatory channel subscription\n"
        "• 📊 Full statistics\n"
        "• 🎛️ Professional admin panel\n"
        "• 💬 Auto & quick replies\n\n"
        "🤖 Create a bot <b>under your name</b> — all messages from @your_bot\n\n"
        "⭐ <b>Monthly subscription</b> — start now 👇"
    ),
    "choose_language": "🌐 Choose language / اختر اللغة:",
    "language_saved": "✅ Language saved",
    "btn_create": "🤖 Create autopost bot",
    "btn_create_free": "🤖 Create bot for free",
    "btn_my_bots": "📋 My bots",
    "btn_language": "🌐 Language",
    "btn_admin": "⚙️ Admin panel",
    "btn_back": "◀️ Back",
    "btn_pay_stars": "⭐ {price} Stars",
    "btn_pay_crypto": "💵 {price} · {days} days",
    "btn_crypto_trc20": "💵 {price}",
    "btn_crypto_admin": "📩 Send screenshot to @sftsfdrtghbot",
    "btn_cryptobot_usdt": "💵 {price}",
    "btn_cryptobot_pay": "💵 Pay {price} via @CryptoBot",
    "btn_wallet_usdt": "💵 {price}",
    "btn_renew": "🔄 Renew subscription",
    "btn_open_bot": "🚀 Open your bot",
    "create_intro": (
        "<b>Create a separate bot</b>\n━━━━━━━━━━━━━━━━\n\n"
        "1️⃣ @BotFather → /newbot → name your bot\n"
        "2️⃣ Copy the token\n"
        "3️⃣ Choose payment:\n"
        "   • ⭐ <b>{price}</b> Stars\n"
        "   • 💵 <b>{crypto_usdt}</b>\n"
        "   • Duration: <b>{days}</b> days\n"
        "4️⃣ Send the token here\n\n"
        "✅ Independent bot — all messages from @your_bot"
    ),
    "create_free_intro": (
        "<b>Create bot for free</b>\n━━━━━━━━━━━━━━━━\n\n"
        "1️⃣ @BotFather → /newbot\n"
        "2️⃣ Copy token and send it here\n"
        "3️⃣ Duration: <b>{days}</b> days\n\n"
        "✅ Your bot will start immediately!"
    ),
    "crypto_choose_wallet": (
        "💵 <b>USDT payment</b>\n"
        "Duration: <b>{days}</b> days\n\n"
        "💵 <b>Price:</b> {usdt_price}\n\n"
        "1️⃣ Pay USDT (TRC20 or TON network — choose in your wallet)\n"
        "2️⃣ Send payment screenshot to bot:\n"
        "🤖 <b>@{admin}</b>\n\n"
        "After admin confirms — send your @BotFather token here."
    ),
    "crypto_wallet_trc20": (
        "💵 <b>USDT</b>\n"
        "Price: <b>{price}</b> | {days} days\n\n"
        "<code>{wallet}</code>\n\n"
        "⚠️ Send USDT only (TRC20 or TON — choose network in your wallet)!\n\n"
        "After payment send screenshot to bot:\n"
        "🤖 <b>@{admin}</b>\n\n"
        "After admin confirms — send your @BotFather token here."
    ),
    "wallet_choose_currency": (
        "👛 <b>Pay via Telegram Wallet</b>\n"
        "Duration: <b>{days}</b> days\n\n"
        "💵 <b>USDT:</b> {usdt_price}\n\n"
        "Tap the button below — payment opens in Wallet.\n"
        "Network (TRC20 / TON) is chosen in your wallet.\n"
        "After payment you will be asked for your @BotFather token."
    ),
    "wallet_pay_ready": (
        "👛 <b>Ready to pay</b>\n"
        "Amount: <b>{price}</b> | {days} days\n\n"
        "Tap the button below — only your Telegram account can pay.\n"
        "Access is granted automatically after payment."
    ),
    "wallet_order_desc": "Autopost bot subscription {days} days",
    "cryptobot_invoice_desc": "Autopost bot · {days} days · {price}",
    "wallet_pay_not_configured": "Wallet Pay is not configured yet. Use Stars or contact admin.",
    "wallet_pay_price_error": "Invalid crypto price in admin settings.",
    "cryptobot_choose_currency": (
        "💵 <b>Pay via @CryptoBot</b>\n"
        "Duration: <b>{days}</b> days\n\n"
        "💵 <b>Price:</b> {usdt_price}\n\n"
        "Tap the button below — payment opens in @CryptoBot.\n"
        "Network (TRC20 / TON) is chosen in @CryptoBot wallet.\n"
        "Access is granted automatically after payment."
    ),
    "cryptobot_pay_ready": (
        "💵 <b>Ready to pay</b>\n"
        "Amount: <b>{price}</b> | {days} days\n\n"
        "Tap the button below to pay in @CryptoBot.\n"
        "After payment you will be asked for your @BotFather token."
    ),
    "cryptobot_not_configured": "Crypto Pay is not configured. Use Stars or contact admin.",
    "grant_access_notify": (
        "✅ <b>Access granted!</b>\n\n"
        "Send your bot <b>token</b> from @BotFather\n"
        "Duration: <b>{days}</b> days"
    ),
    "send_token": (
        "✅ Payment received!\n\n"
        "Send your bot <b>token</b> from @BotFather\n"
        "(the name you chose there will be shown to everyone)"
    ),
    "token_invalid": "❌ Invalid token. Copy the full token from @BotFather.",
    "token_exists": "❌ This token is already registered.",
    "bot_start_failed": "❌ Bot saved but failed to start. Restart the platform or contact support.",
    "pending_token_hint": "⏳ <b>Payment waiting for token</b> — send your @BotFather token here.",
    "bot_created": (
        "✅ <b>Your bot is live!</b>\n\n"
        "🤖 @{username}\n"
        "📛 {name}\n"
        "📅 Valid until: <b>{date}</b>\n"
        "⏳ Remaining: <b>{days}</b> days\n\n"
        "Open your bot — admin panel and posting are there."
    ),
    "bot_needs_token": "needs BotFather token",
    "my_bots_empty": "You have no bots yet. Create your first one!",
    "my_bots_title": "<b>My bots</b>\n━━━━━━━━━━━━━━━━",
    "bot_line_active": "✅ @{username} ({name}) — {days} days left",
    "bot_line_offline": "⚠️ @{username} ({name}) — offline (auto-restarting)",
    "bot_line_expired": "❌ @{username} ({name}) — expired",
    "renew_intro": (
        "Renew @{username}\n"
        "Price: <b>{price}⭐</b> for <b>{days}</b> days"
    ),
    "renew_success": "✅ Renewed! @{username} — valid until {date}",
    "reminder_expiry": (
        "⚠️ <b>Your bot subscription expires soon!</b>\n\n"
        "🤖 {bot}\n"
        "⏳ Remaining: <b>{days}</b> days\n\n"
        "Renew for <b>{price}⭐</b> or the bot will stop."
    ),
    "admin_title": "<b>Admin panel</b>\n━━━━━━━━━━━━━━━━",
    "admin_hub_title": "<b>⚙️ Platform admin</b>\n━━━━━━━━━━━━━━━━",
    "admin_billing_title": "<b>💳 Payments & subscriptions</b>\n━━━━━━━━━━━━━━━━",
    "admin_section_features": "📋 Bot features",
    "admin_section_billing": "💳 Payments & plans",
    "admin_section_ops": "🎛️ Network control",
    "admin_btn_free_on": "🆓 Free mode ON",
    "admin_btn_paid_on": "💳 Paid mode ON",
    "admin_btn_stars_price": "💰 Stars price",
    "admin_btn_usdt_price": "💵 USDT price (CryptoBot)",
    "admin_btn_duration": "📅 Duration (all payments)",
    "admin_btn_grant": "👤 Grant access",
    "admin_btn_stars_balance": "⭐ Stars balance",
    "admin_btn_purchases": "📊 Purchases",
    "admin_features_text": (
        "<b>📋 What each clone bot includes</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "🔄 <b>Auto-posting</b> — from 5 min to 1 hour\n"
        "⏰ Flexible intervals: 5m, 15m, 30m, 1 hour\n"
        "📣 Targets: private chats, groups, channels or all\n"
        "📢 Mass broadcast to subscribers\n"
        "📋 Mandatory channel subscription\n"
        "📊 Full statistics panel\n"
        "🎛️ Professional admin panel per bot\n"
        "💬 Auto & quick replies\n\n"
        "<i>Each owner manages their bot from inside @their_bot.\n"
        "Platform admin controls payments, all clones, and network broadcasts.</i>"
    ),
    "admin_ops_intro": (
        "<b>🎛️ Network control</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "Manage all clone bots from one place:\n"
        "• Stop / start any bot\n"
        "• Broadcast to all subscribers or groups\n"
        "• Set auto-reply for all bots\n"
        "• View full network statistics"
    ),
    "admin_btn_network_stats": "📊 Network statistics",
    "admin_btn_manage_bots": "🤖 Manage clone bots",
    "admin_btn_broadcast_all": "📢 Broadcast — all",
    "admin_btn_broadcast_private": "👤 Broadcast — private only",
    "admin_btn_broadcast_groups": "👥 Broadcast — groups only",
    "admin_btn_auto_reply": "💬 Auto-reply (all bots)",
    "admin_btn_start_all": "▶️ Start all bots",
    "admin_btn_broadcast_one_bot": "📢 Broadcast — one bot",
    "admin_bc_pick_bot": (
        "<b>📢 Broadcast to one bot</b>\n"
        "Choose the clone bot:"
    ),
    "admin_bc_pick_audience": (
        "<b>📢 @{username}</b>\n"
        "Choose audience:"
    ),
    "admin_bc_prompt_one": "Sending via <b>@{username}</b> only.",
    "admin_bc_no_bots": "No clone bots available.",
    "admin_btn_stop_all": "⛔ Stop all bots",
    "admin_network_stats": (
        "<b>📊 Network statistics</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "🤖 Total bots: <b>{total_bots}</b>\n"
        "✅ Active: <b>{active_bots}</b> | 🟢 Running: <b>{running_bots}</b>\n"
        "⛔ Disabled: <b>{disabled_bots}</b> | ❌ Expired: <b>{expired_bots}</b>\n\n"
        "👤 Private subscribers: <b>{total_users}</b>\n"
        "👥 Groups/channels: <b>{total_groups}</b>\n"
        "🔄 Autopost ON: <b>{autopost_enabled}</b> bots\n"
        "💬 Auto-replies total: <b>{auto_replies_total}</b>"
    ),
    "admin_bots_list_title": "<b>🤖 Clone bots</b> ({count})\n━━━━━━━━━━━━━━━━",
    "admin_bot_line": "• @{username} — {status} (#{bot_id})",
    "admin_bot_detail": (
        "<b>🤖 @{username}</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "📛 {name}\n"
        "👤 Owner: <code>{owner_id}</code>\n"
        "📅 Days left: <b>{days}</b>\n"
        "Status: <b>{status}</b>"
    ),
    "admin_bot_status_running": "🟢 Running",
    "admin_bot_status_stopped": "🔴 Stopped",
    "admin_bot_status_disabled": "⛔ Disabled",
    "admin_btn_disable_bot": "⛔ Disable bot",
    "admin_btn_enable_bot": "✅ Enable bot",
    "admin_btn_start_bot": "▶️ Start bot",
    "admin_btn_restart_bot": "🔄 Restart bot",
    "admin_bot_stopped": "Bot disabled and stopped",
    "admin_bot_started": "Bot enabled and started",
    "admin_bot_start_failed": "Could not start bot — check token/logs",
    "admin_bot_restarted": "Bot restarted",
    "admin_started_all": "Started {count} bot(s)",
    "admin_stopped_all": "Stopped {count} bot(s)",
    "admin_bc_prompt_all": (
        "📢 <b>Broadcast to ALL</b> (private + groups)\n"
        "Across every active clone bot.\n\n"
        "Send your message now (text, photo, video...)"
    ),
    "admin_bc_prompt_private": (
        "👤 <b>Broadcast to PRIVATE subscribers</b>\n"
        "Only users who wrote to each clone bot.\n\n"
        "Send your message now"
    ),
    "admin_bc_prompt_groups": (
        "👥 <b>Broadcast to GROUPS</b>\n"
        "All groups/channels where clone bots are added.\n\n"
        "Send your message now"
    ),
    "admin_bc_no_content": "❌ Unsupported content. Send text or media.",
    "admin_bc_sending": "⏳ Sending broadcast across all bots...",
    "admin_bc_done": (
        "✅ <b>Broadcast done</b>\n\n"
        "🤖 Bots used: {bots}\n"
        "🎯 Targets: {targets}\n"
        "✅ Sent: {sent} | 🚫 Blocked: {blocked} | ❌ Failed: {failed}"
    ),
    "admin_ar_title": "<b>💬 Global auto-replies</b>\n━━━━━━━━━━━━━━━━",
    "admin_ar_empty": "No auto-replies yet.",
    "admin_ar_tap_hint": "Tap <b>➕ Add</b> to create one.",
    "admin_ar_list_hint": "Tap a button below to edit:",
    "admin_ar_list_line": "{num}. <b>{trigger}</b> → {reply}",
    "admin_ar_item_detail": (
        "<b>💬 Auto-reply</b>\n"
        "━━━━━━━━━━━━━━━━\n\n"
        "🔑 <b>Trigger:</b> <code>{trigger}</code>\n"
        "💬 <b>Reply:</b>\n{reply}"
    ),
    "admin_btn_ar_edit_reply": "✏️ Edit reply text",
    "admin_btn_ar_edit_trigger": "🔑 Edit trigger word",
    "admin_btn_ar_delete": "🗑 Delete",
    "admin_ar_edit_reply_prompt": (
        "✏️ <b>Edit reply</b> for «<code>{trigger}</code>»\n\n"
        "Current:\n{reply}\n\n"
        "Send the new reply text:"
    ),
    "admin_ar_edit_trigger_prompt": (
        "🔑 <b>Edit trigger</b>\n\n"
        "Current: <code>{trigger}</code>\n\n"
        "Send the new trigger word:"
    ),
    "admin_ar_updated": "✅ Reply updated for «{trigger}» ({bots} bots)",
    "admin_ar_trigger_updated": "✅ Trigger updated to «{trigger}» ({bots} bots)",
    "admin_ar_deleted": "🗑 Deleted «{trigger}»",
    "admin_btn_ar_add": "➕ Add auto-reply",
    "admin_btn_ar_sync": "🔄 Sync to all bots",
    "admin_btn_ar_clear": "🗑 Clear all auto-replies",
    "admin_ar_trigger_prompt": "Send the <b>trigger word</b> (users type this):",
    "admin_ar_reply_prompt": "Now send the <b>auto-reply text</b>:",
    "admin_ar_saved": "✅ Added «{trigger}» to {bots} bot(s)",
    "admin_ar_synced": "Synced {rules} rule(s) to {bots} bot(s)",
    "admin_ar_cleared": "Cleared auto-replies on {bots} bot(s)",
    "admin_ar_failed": "❌ Failed — try again",
    "admin_stats": (
        "👥 Users: {users}\n"
        "🤖 Bots: {total_bots} (active: {active_bots})\n"
        "⭐ Today: {today_stars} | Total: {total_stars}"
    ),
    "admin_set_price_prompt": (
        "💰 <b>Change price</b>\n\n"
        "Current price: <b>{price}⭐</b>\n\n"
        "Send the new price in Stars only.\n"
        "Example: <code>150</code>"
    ),
    "admin_set_duration_prompt": (
        "📅 <b>Change subscription duration</b>\n\n"
        "Current duration: <b>{days}</b> days ({months} month(s))\n\n"
        "Send days or months.\n"
        "Examples: <code>30</code> or <code>1m</code> (one month)"
    ),
    "admin_current_plan": "💳 Current: <b>{price}⭐</b> / <b>{days}</b> days ({months} month(s))",
    "admin_price_saved": "✅ Price saved: <b>{price}⭐</b> / {days} days ({months} month(s))",
    "admin_duration_saved": "✅ Duration saved: <b>{days}</b> days ({months} month(s)) — price: {price}⭐",
    "admin_invalid_price": "❌ Send a valid price number, e.g. <code>100</code>",
    "admin_invalid_duration": "❌ Send days or months, e.g. <code>30</code> or <code>2m</code>",
    "admin_stars_title": "<b>⭐ Stars balance</b>\n━━━━━━━━━━━━━━━━",
    "admin_stars_db": "📊 In bot DB: today {today}⭐ | total {total}⭐",
    "admin_stars_owner": "👤 Finance owner: <code>{owner_id}</code>",
    "admin_stars_telegram": "💰 Telegram bot balance: <b>{balance}⭐</b>",
    "admin_stars_recent": "Recent deposits:",
    "admin_stars_api_error": "⚠️ Could not fetch Telegram balance: {error}",
    "admin_stars_hint": (
        "\n<i>Stars are on @Ni_iF7Fibot balance\n"
        "BotFather → /mybots → Balance (owner only)</i>"
    ),
    "admin_denied": "⛔ You don't have admin access",
    "admin_mode_paid": "💳 Mode: <b>Paid</b>",
    "admin_mode_free": "🆓 Mode: <b>Free</b>",
    "admin_mode_switched_free": "🆓 Free mode enabled — restored {count} bot(s)",
    "admin_mode_switched_paid": "💳 Paid mode enabled — revoked {count} bots",
    "admin_crypto_plan": "💵 CryptoBot: <b>{usdt_price}</b> (Stars price is separate)",
    "admin_crypto_usdt_prompt": (
        "💵 <b>USDT price</b>\n\n"
        "Current: <b>{price}</b>\n"
        "Send amount only or with USDT.\n"
        "Examples: <code>25</code> or <code>25 USDT</code>"
    ),
    "admin_crypto_usdt_saved": "✅ USDT price saved: {price}",
    "admin_invalid_crypto_price": "❌ Invalid price. Example: <code>25</code> or <code>25 USDT</code>",
    "admin_grant_prompt": (
        "👤 <b>Grant access</b>\n\n"
        "Send <b>Telegram ID</b> or <b>@username</b>\n"
        "Example: <code>929743223</code> or <code>@username</code>"
    ),
    "admin_grant_not_found": "❌ User not found. Send a valid ID or @username.",
    "admin_grant_done": "✅ Access granted to <code>{user_id}</code> — {days} days",
    "admin_recent": "<b>Recent purchases</b>",
    "payment_line": "• {name} — {amount}⭐ / {days}d — {bot}",
    "invoice_title": "Autopost bot subscription",
    "invoice_desc": "Separate bot for {days} days",
}
