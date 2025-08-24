import requests
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
import time
import random
import string

# ========= CONFIG ==========
BOT_TOKEN = "8475956861:AAG-iu70jwNeSO6wq_2Qm3ibfA9ttJFdKUE"
ADMIN_ID =   8120431402 # Replace with your Telegram ID
LOG_CHANNEL = -4891137292  # Optional log channel, 0 if unused
# ===========================

bot = telebot.TeleBot(BOT_TOKEN)

# ---------------------------
# Storage (in-memory)
user_credits = {}        # user_id -> credits
blocked_users = set()    # blocked users
admins = {ADMIN_ID}      # admin user_ids
redeem_codes = {
    "FREE1H": {"credits": 1, "used_by": []},
    "FREE24H": {"credits": 24, "used_by": []},
}

# Referral system
referrals = {}           # user_id -> list of referred user_ids
user_refcode = {}        # user_id -> referral code
refcode_to_user = {}     # referral code -> user_id
MAX_REF = 10
REF_CREDIT = 1

# ---------------------------
# Utility functions
def log_action(text):
    if LOG_CHANNEL != 0:
        try:
            bot.send_message(LOG_CHANNEL, text, parse_mode="HTML")
        except:
            pass

def add_credits(user_id, credits):
    user_credits[user_id] = user_credits.get(user_id, 0) + credits

def generate_refcode(length=6):
    while True:
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
        if code not in refcode_to_user:
            return code

def handle_referral(user_id, start_msg):
    parts = start_msg.text.strip().split()
    if len(parts) == 2:
        refcode = parts[1].upper()
        referrer_id = refcode_to_user.get(refcode)
        if referrer_id and referrer_id != user_id:
            user_refs = referrals.get(referrer_id, [])
            if len(user_refs) < MAX_REF and user_id not in user_refs:
                user_refs.append(user_id)
                referrals[referrer_id] = user_refs
                add_credits(referrer_id, REF_CREDIT)
                log_action(f"🪙 Referral: User {user_id} referred by {referrer_id}, +{REF_CREDIT} credit")
                bot.send_message(referrer_id, f"🎉 You earned {REF_CREDIT} credit! Total referrals: {len(user_refs)}/{MAX_REF}")

# ---------------------------
# API Functions
def vehicle_lookup(rc):
    url = f"https://rc-info-j4tnx.onrender.com/rc={rc}"
    try:
        res = requests.get(url, timeout=10).json()
    except:
        return "❌ Error contacting Vehicle API"
    if "result1" not in res:
        return "❌ No data found"
    r = res["result1"]
    text = f"""🚗 <b>Vehicle Info</b>

🔑 RC: {r.get('rc_number')}
👤 Owner: {r.get('owner_name')}
👨‍👦 Father: {r.get('father_name')}
🚘 Model: {r.get('model_name')}
🏷 Maker: {r.get('maker_model')}
📅 Reg Date: {r.get('registration_date')}
🏦 Financier: {r.get('financier_name')}
🛢 Fuel: {r.get('fuel_type')} ({r.get('fuel_norms')})
📝 Ins No: {r.get('insurance_no')}
📅 Ins Exp: {r.get('insurance_expiry')}
🧾 PUC: {r.get('puc_no')} (upto {r.get('puc_upto')})
🏠 Address: {r.get('address')}
📞 Phone: {r.get('phone')}
"""
    return text

def imei_lookup(no):
    url = f"https://emei-api-j4tnx.vercel.app/no={no}"
    try:
        res = requests.get(url, timeout=10).json()
    except:
        return "❌ Error contacting IMEI API"
    if res.get("status") != "success":
        return "❌ No data found"
    hdr = res["data"]["header"]
    text = f"""📱 <b>IMEI Info</b>

📲 Brand: {hdr.get('brand')}
🔑 Model: {hdr.get('model')}
🔢 IMEI: {hdr.get('imei')}
🖼 Photo: {hdr.get('photo')}
"""
    for item in res["data"]["items"]:
        if item["role"] == "item":
            text += f"\n🔹 {item['title']}: {item['content']}"
    return text

def pincode_lookup(pin):
    url = f"https://pincode-info-j4tnx.vercel.app/pincode={pin}"
    try:
        res = requests.get(url, timeout=10).json()
    except:
        return "❌ Error contacting PIN API"
    if res.get("Status") != "Success":
        return "❌ No data found"
    po = res["PostOffice"][0]
    text = f"""📮 <b>Pincode Info</b>

🏷 Pincode: {po.get('Pincode')}
🏠 Area: {po.get('Name')}
🏢 District: {po.get('District')}
🌍 State: {po.get('State')}
📦 Branch: {po.get('BranchType')}
✅ Delivery: {po.get('DeliveryStatus')}
"""
    return text

def mobile_lookup(number):
    url = f"https://osintapi.store/cutieee/api.php?key=jerry&type=mobile&term={number}"
    try:
        res = requests.get(url, timeout=10).json()
    except:
        return "❌ Error contacting Mobile API"
    if not res:
        return "❌ No data found"
    text = f"📞 <b>Mobile Lookup</b>\n\n"
    for item in res:
        text += f"""👤 Name: {item.get('name')}
👨‍👦 Father: {item.get('father_name')}
🏠 Address: {item.get('address')}
📞 Mobile: {item.get('mobile')}
📲 Alt Mobile: {item.get('alt_mobile')}
🌐 Circle: {item.get('circle')}
🆔 ID Number: {item.get('id_number')}
📧 Email: {item.get('email') or 'N/A'}
--------------------------
"""
    return text

# ---------------------------
# Start Handler with referral
@bot.message_handler(commands=["start"])
def send_welcome(message):
    if message.from_user.id in blocked_users:
        bot.send_message(message.chat.id, "❌ You are blocked.")
        return

    uid = message.from_user.id
    if uid not in user_refcode:
        code = generate_refcode()
        user_refcode[uid] = code
        refcode_to_user[code] = uid

    handle_referral(uid, message)

    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("📞 Mobile Lookup", callback_data="mobile"),
        InlineKeyboardButton("🚗 Vehicle Lookup", callback_data="vehicle"),
        InlineKeyboardButton("📱 IMEI Lookup", callback_data="imei"),
        InlineKeyboardButton("📮 PIN Lookup", callback_data="pin"),
        InlineKeyboardButton("🎟 Redeem Code", callback_data="redeem"),
        InlineKeyboardButton("📩 Support", callback_data="support"),
        InlineKeyboardButton("👤 Profile", callback_data="profile"),
        InlineKeyboardButton("🛠 Admin", callback_data="admin")
    )
    bot.send_message(message.chat.id, f"🤖 Welcome! Select an option:\nYour referral code: {user_refcode[uid]}\nShare to earn credits!", reply_markup=markup)

# ---------------------------
# Callback Handler
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call: CallbackQuery):
    cid = call.message.chat.id
    if cid in blocked_users:
        bot.answer_callback_query(call.id, "❌ You are blocked.")
        return

    if call.data == "vehicle":
        bot.send_message(cid, "🚗 Send vehicle RC number:")
        bot.register_next_step_handler(call.message, handle_vehicle)
    elif call.data == "imei":
        bot.send_message(cid, "📱 Send IMEI number:")
        bot.register_next_step_handler(call.message, handle_imei)
    elif call.data == "pin":
        bot.send_message(cid, "📮 Send Pincode:")
        bot.register_next_step_handler(call.message, handle_pin)
    elif call.data == "mobile":
        bot.send_message(cid, "📞 Send Mobile Number:")
        bot.register_next_step_handler(call.message, handle_mobile)
    elif call.data == "redeem":
        bot.send_message(cid, "🎟 Enter your code:")
        bot.register_next_step_handler(call.message, handle_redeem)
    elif call.data == "profile":
        uid = call.from_user.id
        credits = user_credits.get(uid, 0)
        refs = len(referrals.get(uid, []))
        code = user_refcode.get(uid)
        bot.send_message(cid, f"👤 Profile\nCredits: {credits}\nReferrals: {refs}\nYour code: {code}")
    elif call.data == "admin":
        if cid in admins:
            bot.send_message(cid, "🛠 Admin panel:\n/approve <id> <credits>\n/add <id> <credits>\n/block <id>\n/unblock <id>\n/gen <users> <credits>\n/users")
        else:
            bot.send_message(cid, "❌ You are not admin.")

# ---------------------------
# Redeem handler
def handle_redeem(msg):
    uid = msg.from_user.id
    code = msg.text.strip().upper()
    if code in redeem_codes:
        if uid in redeem_codes[code]["used_by"]:
            bot.send_message(uid, "❌ You already used this code.")
        else:
            redeem_codes[code]["used_by"].append(uid)
            add_credits(uid, redeem_codes[code]["credits"])
            bot.send_message(uid, f"✅ Code applied! You got {redeem_codes[code]['credits']} credits.")
            log_action(f"🎟 Redeem: User {uid} used code {code}")
    else:
        bot.send_message(uid, "❌ Invalid code.")

# ---------------------------
# Admin commands
@bot.message_handler(commands=["approve","add","block","unblock","gen","users"])
def admin_cmd(msg):
    if msg.from_user.id not in admins:
        bot.reply_to(msg, "❌ Not authorized.")
        return
    parts = msg.text.split()
    cmd = parts[0][1:]
    if cmd == "approve" or cmd == "add":
        if len(parts) < 3:
            bot.reply_to(msg, "Usage: /add <user_id> <credits>")
            return
        uid = int(parts[1])
        credits = int(parts[2])
        add_credits(uid, credits)
        bot.reply_to(msg, f"✅ Added {credits} credits to {uid}")
    elif cmd == "block":
        if len(parts) < 2:
            bot.reply_to(msg, "Usage: /block <user_id>")
            return
        uid = int(parts[1])
        blocked_users.add(uid)
        bot.reply_to(msg, f"✅ User {uid} blocked")
    elif cmd == "unblock":
        if len(parts) < 2:
            bot.reply_to(msg, "Usage: /unblock <user_id>")
            return
        uid = int(parts[1])
        blocked_users.discard(uid)
        bot.reply_to(msg, f"✅ User {uid} unblocked")
    elif cmd == "gen":
        if len(parts) < 3:
            bot.reply_to(msg, "Usage: /gen <count> <credits>")
            return
        count = int(parts[1])
        credits = int(parts[2])
        for _ in range(count):
            code = ''.join(random.choices(string.ascii_uppercase+string.digits, k=6))
            redeem_codes[code] = {"credits": credits, "used_by":[]}
        bot.reply_to(msg, f"✅ Generated {count} codes with {credits} credits each")
    elif cmd == "users":
        text = "📋 Users & credits:\n"
        for uid, credit in user_credits.items():
            text += f"{uid}: {credit}\n"
        bot.reply_to(msg, text)

# ---------------------------
# Run Bot
while True:
    try:
        bot.polling(none_stop=True)
    except Exception as e:
        print("Bot error:", e)
        time.sleep(5)