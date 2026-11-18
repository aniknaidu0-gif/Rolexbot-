import os
import re
import time
import threading
from datetime import datetime, timezone, timedelta
from flask import Flask
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions

TOKEN = os.environ.get("TOKEN")
bot = telebot.TeleBot(TOKEN, parse_mode="HTML")
app = Flask(__name__)

# বাংলাদেশ টাইমজোন (UTC+6)
BD_TZ = timezone(timedelta(hours=6))

TARGET_GROUP_ID = None
ADMIN_ID = None
BOT_ACTIVE = True
jobs = {}
msg_to_job = {}
sprinter_stats = {}
clip_data = {"numbers": [], "idx": 0}
custom_timer_wait = {}
job_counter = 1022
last_report_date = ""

@app.route('/')
def home():
    return "Bot is alive and running 24/7!"

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

def get_bd_now():
    return datetime.now(BD_TZ)

def get_keyboard(job_id):
    kb = InlineKeyboardMarkup(row_width=4)
    kb.add(
        InlineKeyboardButton("🟢 Done", callback_data=f"done_{job_id}"),
        InlineKeyboardButton("🔵 No E", callback_data=f"noe_{job_id}"),
        InlineKeyboardButton("🔴 Serv", callback_data=f"serv_{job_id}"),
        InlineKeyboardButton("🔔 OTP", callback_data=f"otp_{job_id}")
    )
    kb.add(
        InlineKeyboardButton("🚀 Start", callback_data=f"start_{job_id}"),
        InlineKeyboardButton("⏳ Tim", callback_data=f"tim_{job_id}"),
        InlineKeyboardButton("⚡ Prob", callback_data=f"prob_{job_id}"),
        InlineKeyboardButton("💬 Chat", callback_data=f"chat_{job_id}")
    )
    kb.add(
        InlineKeyboardButton("📁 Orig", callback_data=f"orig_{job_id}"),
        InlineKeyboardButton("👁️ Shov", callback_data=f"shov_{job_id}"),
        InlineKeyboardButton("📋 Clip", callback_data=f"clip_{job_id}"),
        InlineKeyboardButton("🗑️ Dele", callback_data=f"dele_{job_id}")
    )
    kb.add(
        InlineKeyboardButton("📊 Graph", callback_data=f"graph_{job_id}")
    )
    return kb

def format_post(job_id):
    j = jobs[job_id]
    total = len(j["numbers"])
    idx = j["current_idx"]

    if not j.get("reacted", False):
        lock_banner = "🔒 <b>[REACT TO UNLOCK]</b> মেসেজে রিঅ্যাক্ট দিন\n"
    else:
        lock_banner = ""

    if j.get("waiting", False) and idx < total:
        current_num = f"⏳ Waiting ({j['timer_label']})..."
        current_pos = f"{idx + 1:02d}"
    elif idx < total:
        current_num = f"<code>{j['numbers'][idx]}</code>"
        current_pos = f"{idx + 1:02d}"
    else:
        current_num = "ALL COMPLETED ✅"
        current_pos = f"{total:02d}"
    
    done_c = j["done"]
    noe_c = j["noe"]
    serv_c = j["serv"]
    rem_c = max(0, total - (done_c + noe_c + serv_c))
    
    timer_text = f"🟢 ON ({j['timer_label']})" if j["timer_sec"] > 0 else "🔴 OFF"
    status_header = "⚡ UPDATED" if (done_c + noe_c + serv_c) > 0 else "🆕 NEW WORK"

    text = (
        f"{lock_banner}"
        f"🔵 <b>SPEED WORK #{job_id}</b>\n"
        f"{status_header}\n"
        f"<code>{j['code']}</code>\n"
        f"<code>{j['password']}</code>\n"
        f"<code>{j['extra']}</code>\n\n"
        f"🗓️ Date: {j['date']}\n"
        f"🏃 Received by: {j['receiver']}\n"
        f"⏳ Timer: {timer_text}\n"
        f"📦 Total : {total}\n"
        f"🎯 Current 🔵 {current_pos} ➔\n"
        f"{current_num}\n"
        f"📊 🟢 {done_c} | 🔵 {noe_c} | 🔴 {serv_c} | 🟣 {rem_c}"
    )

    if j.get("show_list", False):
        lines = []
        for i, num in enumerate(j["numbers"]):
            st = j["statuses"][i]
            lines.append(f"{i+1:02d}. <code>{num}</code> {st}")
        text += "\n\n👁️ <b>All Numbers:</b>\n" + "\n".join(lines)

    return text

def update_main_message(jid, chat_id, msg_id):
    try:
        bot.edit_message_text(
            format_post(jid),
            chat_id=chat_id,
            message_id=msg_id,
            reply_markup=get_keyboard(jid)
        )
    except Exception:
        pass

def unlock_next_number(jid, chat_id, msg_id):
    if jid in jobs:
        jobs[jid]["waiting"] = False
        update_main_message(jid, chat_id, msg_id)

def generate_full_report():
    now_str = get_bd_now().strftime("%Y-%m-%d %I:%M %p")
    if not jobs:
        return f"📊 <b>DAILY WORK REPORT</b>\n🗓️ {now_str}\n\nআজকে কোনো কাজের ডাটা নেই।"

    report_lines = [f"📊 <b>DAILY FULL WORK REPORT</b>\n🗓️ {now_str}\n{'='*26}"]
    total_all = 0
    total_done = 0
    total_noe = 0
    total_serv = 0

    report_lines.append("\n📌 <b>কোড-ওয়াইজ হিসাব (Code-wise):</b>")
    for jid, j in jobs.items():
        tot = len(j["numbers"])
        rem = max(0, tot - (j["done"] + j["noe"] + j["serv"]))
        total_all += tot
        total_done += j["done"]
        total_noe += j["noe"]
        total_serv += j["serv"]
        report_lines.append(
            f"🔹 <b>#{jid}</b> (Code: <code>{j['code']}</code>)\n"
            f"   👤 {j['receiver']} | মোট: {tot}\n"
            f"   🟢 Done: {j['done']} | 🔵 No E: {j['noe']} | 🔴 Serv: {j['serv']} | 🟣 বাকি: {rem}"
        )

    report_lines.append("\n🏃 <b>স্প্রিন্টার-ওয়াইজ হিসাব (Sprinter-wise):</b>")
    if sprinter_stats:
        for sp, st in sprinter_stats.items():
            report_lines.append(
                f"• <b>{sp}</b> ➔ 🟢 Done: {st['done']} | 🔵 No E: {st['noe']} | 🔴 Serv: {st['serv']}"
            )
    else:
        report_lines.append("• এখনো কেউ কাজ সম্পন্ন করেনি।")

    total_rem = max(0, total_all - (total_done + total_noe + total_serv))
    report_lines.append(
        f"\n{'='*26}\n📈 <b>সর্বমোট সারসংক্ষেপ:</b>\n"
        f"📦 মোট নম্বর: {total_all}\n"
        f"🟢 মোট Done: {total_done}\n"
        f"🔵 মোট No Entry: {total_noe}\n"
        f"🔴 মোট Server Prob: {total_serv}\n"
        f"🟣 মোট বাকি: {total_rem}"
    )
    return "\n".join(report_lines)

# রাত ১২:০০টার অটোমেটিক রিপোর্ট চেকার
def midnight_report_scheduler():
    global last_report_date
    while True:
        try:
            now = get_bd_now()
            today_str = now.strftime("%Y-%m-%d")
            if now.hour == 0 and now.minute == 0 and last_report_date != today_str:
                last_report_date = today_str
                rep = generate_full_report()
                if ADMIN_ID:
                    bot.send_message(ADMIN_ID, rep)
                if TARGET_GROUP_ID:
                    bot.send_message(TARGET_GROUP_ID, rep)
        except Exception:
            pass
        time.sleep(20)

@bot.message_handler(commands=['start'])
def start_cmd(message):
    global ADMIN_ID
    if message.chat.type == 'private':
        ADMIN_ID = message.from_user.id
        status = "🟢 চালু (ON)" if BOT_ACTIVE else "🔴 বন্ধ (OFF)"
        bot.reply_to(
            message,
            f"✅ <b>Rolexbot Admin Panel</b>\n"
            f"বর্তমান অবস্থা: <b>{status}</b>\n\n"
            "📌 <b>প্রয়োজনীয় কমান্ডসমূহ:</b>\n"
            "• <code>/setgroup</code> — গ্রুপে গিয়ে এটি লিখলে গ্রুপ সেট হবে\n"
            "• <code>/botoff</code> — বটের কাজ সাময়িকভাবে বন্ধ করতে\n"
            "• <code>/boton</code> — বট আবার চালু করতে\n"
            "• <code>/report</code> — যেকোনো সময় পুরো রিপোর্ট দেখতে\n"
            "• <code>/clip</code> — নিচে ১০০-১৫০টি নম্বর দিয়ে ক্লিপ লিস্ট সেভ করতে"
        )

@bot.message_handler(commands=['botoff'])
def bot_off_cmd(message):
    global BOT_ACTIVE, ADMIN_ID
    if message.chat.type == 'private':
        ADMIN_ID = message.from_user.id
        BOT_ACTIVE = False
        bot.reply_to(message, "🔴 <b>বট অফ (OFF) করা হয়েছে!</b>\nএখন গ্রুপে বা ইনবক্সে কোনো কাজ গ্রহণ করা হবে না। আবার চালু করতে <code>/boton</code> লিখুন।")

@bot.message_handler(commands=['boton'])
def bot_on_cmd(message):
    global BOT_ACTIVE, ADMIN_ID
    if message.chat.type == 'private':
        ADMIN_ID = message.from_user.id
        BOT_ACTIVE = True
        bot.reply_to(message, "🟢 <b>বট অন (ON) করা হয়েছে!</b>\nএখন থেকে সব কাজ স্বাভাবিকভাবে চলবে।")

@bot.message_handler(commands=['report'])
def manual_report_cmd(message):
    if message.chat.type == 'private':
        bot.reply_to(message, generate_full_report())

@bot.message_handler(commands=['setgroup'])
def set_group(message):
    global TARGET_GROUP_ID, ADMIN_ID
    if message.chat.type in ['group', 'supergroup']:
        TARGET_GROUP_ID = message.chat.id
        ADMIN_ID = message.from_user.id
        bot.reply_to(message, f"✅ গ্রুপ এবং অ্যাডমিন সফলভাবে সেট হয়েছে!\nGroup ID: <code>{TARGET_GROUP_ID}</code>")
    else:
        bot.reply_to(message, "⚠️ কমান্ডটি আপনার গ্রুপের ভেতরে গিয়ে লিখুন!")

@bot.message_handler(commands=['clip'])
def set_clip(message):
    global ADMIN_ID
    if message.chat.type != 'private':
        return
    ADMIN_ID = message.from_user.id
    raw = message.text.replace('/clip', '').strip()
    nums = [line.strip() for line in raw.split('\n') if line.strip()]
    if not nums:
        bot.reply_to(message, "⚠️ <code>/clip</code> লিখে নিচের লাইনে নম্বরগুলো দিন।")
        return
    clip_data["numbers"] = nums
    clip_data["idx"] = 0
    bot.reply_to(message, f"📋 মোট <b>{len(nums)}</b> টি নম্বর Clip-এ সেভ হয়েছে!")

# গ্রুপে রিঅ্যাক্ট দিলে আনলক হওয়ার সিস্টেম
@bot.message_reaction_handler()
def handle_reaction(reaction):
    if not BOT_ACTIVE:
        return
    msg_id = reaction.message_id
    chat_id = reaction.chat.id
    if msg_id in msg_to_job and reaction.new_reaction:
        jid = msg_to_job[msg_id]
        if jid in jobs and not jobs[jid].get("reacted", False):
            jobs[jid]["reacted"] = True
            if reaction.user:
                jobs[jid]["receiver"] = f"Sprinter {reaction.user.first_name}"
            update_main_message(jid, chat_id, msg_id)

# জয়েন রিকোয়েস্ট অ্যাপ্রুভ সিস্টেম
@bot.chat_join_request_handler()
def handle_join_req(req):
    user = req.from_user
    chat_id = req.chat.id
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Approve", callback_data=f"app_{chat_id}_{user.id}"),
        InlineKeyboardButton("❌ Decline", callback_data=f"dec_{chat_id}_{user.id}")
    )
    target = ADMIN_ID if ADMIN_ID else chat_id
    bot.send_message(
        target,
        f"🔔 <b>নতুন জয়েন রিকোয়েস্ট!</b>\n👤 নাম: {user.first_name}\n🆔 ID: <code>{user.id}</code>\nগ্রুপে ঢোকার অনুমতি দেবেন?",
        reply_markup=kb
    )

@bot.message_handler(func=lambda m: m.from_user.id in custom_timer_wait)
def handle_custom_timer_input(message):
    uid = message.from_user.id
    jid, chat_id, msg_id, prompt_msg_id = custom_timer_wait.pop(uid)
    try:
        mins = float(message.text.strip())
        if mins <= 0 or mins > 60:
            raise ValueError()
        secs = int(round(mins * 60))
        label = f"{mins:g} Min"
        if jid in jobs:
            jobs[jid]["timer_sec"] = secs
            jobs[jid]["timer_label"] = label
            update_main_message(jid, chat_id, msg_id)
        try:
            bot.delete_message(chat_id, message.message_id)
            bot.delete_message(chat_id, prompt_msg_id)
        except Exception:
            pass
    except Exception:
        bot.reply_to(message, "⚠️ সঠিক সংখ্যা দিন (যেমন: <code>2</code> বা <code>2.5</code> বা <code>4</code>)।")

@bot.message_handler(func=lambda m: m.chat.type == 'private')
def handle_input(message):
    global job_counter, TARGET_GROUP_ID, ADMIN_ID
    ADMIN_ID = message.from_user.id
    if not BOT_ACTIVE:
        bot.reply_to(message, "🔴 বট বর্তমানে অফ (OFF) আছে। চালু করতে <code>/boton</code> লিখুন।")
        return
    if not TARGET_GROUP_ID:
        bot.reply_to(message, "⚠️ আগে আপনার গ্রুপে বটটিকে যোগ করে সেখানে <code>/setgroup</code> লিখুন!")
        return

    lines = [line.strip() for line in message.text.strip().split('\n') if line.strip()]
    if len(lines) < 3:
        bot.reply_to(message, "⚠️ কমপক্ষে কোড, পাসওয়ার্ড এবং একটি নম্বর দিন।")
        return

    clean_code = re.sub(r'^(BD|bd|বিডি)\s*', '', lines[0]).strip()
    password = lines[1]
    
    if re.match(r'^(\+?88)?01[3-9]\d{8}$', lines[2]):
        extra = "GP CODE"
        numbers = lines[2:]
    else:
        extra = lines[2]
        numbers = lines[3:]

    if not numbers:
        bot.reply_to(message, "⚠️ কোনো ফোন নম্বর পাওয়া যায়নি!")
        return

    job_counter += 1
    jid = job_counter
    now_str = get_bd_now().strftime("%Y-%m-%d %I:%M %p")

    jobs[jid] = {
        "code": clean_code,
        "password": password,
        "extra": extra,
        "date": now_str,
        "receiver": "Waiting...",
        "reacted": False,
        "timer_sec": 0,
        "timer_label": "OFF",
        "waiting": False,
        "chat_open": False,
        "show_list": False,
        "numbers": numbers,
        "statuses": ["🟣"] * len(numbers),
        "current_idx": 0,
        "done": 0,
        "noe": 0,
        "serv": 0
    }

    sent = bot.send_message(TARGET_GROUP_ID, format_post(jid), reply_markup=get_keyboard(jid))
    jobs[jid]["msg_id"] = sent.message_id
    msg_to_job[sent.message_id] = jid
    bot.reply_to(message, f"✅ মোট <b>{len(numbers)}</b> টি নম্বরসহ কাজটি গ্রুপে পাঠানো হয়েছে! (ID: #{jid})")

@bot.callback_query_handler(func=lambda call: True)
def handle_buttons(call):
    if not BOT_ACTIVE:
        bot.answer_callback_query(call.id, "🔴 বট বর্তমানে Admin কর্তৃক অফ (OFF) রাখা হয়েছে!", show_alert=True)
        return

    parts = call.data.split('_')
    action = parts[0]

    if action in ["app", "dec"]:
        chat_id = int(parts[1])
        uid = int(parts[2])
        try:
            if action == "app":
                bot.approve_chat_join_request(chat_id, uid)
                bot.edit_message_text(f"✅ ইউজার (<code>{uid}</code>) গ্রুপে অ্যাপ্রুভ করা হয়েছে!", call.message.chat.id, call.message.message_id)
            else:
                bot.decline_chat_join_request(chat_id, uid)
                bot.edit_message_text(f"❌ ইউজার (<code>{uid}</code>) রিকোয়েস্ট বাতিল করা হয়েছে।", call.message.chat.id, call.message.message_id)
        except Exception as e:
            bot.answer_callback_query(call.id, f"⚠️ এরর: {e}", show_alert=True)
        return

    if action in ["clipnext", "clipprev", "clipclose"]:
        if action == "clipclose":
            bot.delete_message(call.message.chat.id, call.message.message_id)
            return
        if not clip_data["numbers"]:
            bot.answer_callback_query(call.id, "⚠️ Clip-এ কোনো নম্বর নেই!", show_alert=True)
            return
        if action == "clipnext":
            clip_data["idx"] = (clip_data["idx"] + 1) % len(clip_data["numbers"])
        elif action == "clipprev":
            clip_data["idx"] = (clip_data["idx"] - 1) % len(clip_data["numbers"])
        
        idx = clip_data["idx"]
        total_c = len(clip_data["numbers"])
        num = clip_data["numbers"][idx]
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("⏮️ Prev", callback_data="clipprev_0"),
            InlineKeyboardButton("⏭️ Next Clip", callback_data="clipnext_0"),
            InlineKeyboardButton("❌ Close", callback_data="clipclose_0")
        )
        bot.edit_message_text(
            f"📋 <b>CLIPBOARD ({idx+1}/{total_c})</b>\nএক চাপে কপি করুন:\n<code>{num}</code>",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=kb
        )
        bot.answer_callback_query(call.id)
        return

    jid = int(parts[1])
    if jid not in jobs:
        bot.answer_callback_query(call.id, "⚠️ এই কাজের ডাটা পাওয়া যায়নি।", show_alert=True)
        return

    j = jobs[jid]
    sprinter_name = f"Sprinter {call.from_user.first_name}"

    # অ্যাডমিন বাটন (Chat ও Delete) বাদে বাকি সব বাটনের জন্য রিঅ্যাক্ট বাধ্যতামূলক
    if action not in ["chat", "dele", "graph"] and not j.get("reacted", False):
        bot.answer_callback_query(
            call.id,
            "🔒 কাজ শুরু করতে আগে এই মেসেজটিতে একটি রিঅ্যাক্ট (❤️ বা 👍) দিন!",
            show_alert=True
        )
        return

    if action == "tim":
        kb = InlineKeyboardMarkup(row_width=2)
        kb.add(
            InlineKeyboardButton("⏱️ 2.5 Min (আড়াই মিনিট)", callback_data=f"settim150_{jid}"),
            InlineKeyboardButton("⏱️ 3 Min (৩ মিনিট)", callback_data=f"settim180_{jid}"),
            InlineKeyboardButton("✏️ Custom Time", callback_data=f"settimcust_{jid}"),
            InlineKeyboardButton("🔴 Timer OFF", callback_data=f"settim0_{jid}")
        )
        bot.send_message(
            call.message.chat.id,
            f"⏳ <b>Timer সেট করুন (#{jid}):</b>\nযেকোনো একটি সময় বেছে নিন:",
            reply_markup=kb
        )
        bot.answer_callback_query(call.id)
        return

    if action.startswith("settim"):
        val = action.replace("settim", "")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass

        if val == "150":
            j["timer_sec"] = 150
            j["timer_label"] = "2.5 Min"
            bot.answer_callback_query(call.id, "⏱️ টাইমার ২.৫ মিনিট সেট হয়েছে!")
        elif val == "180":
            j["timer_sec"] = 180
            j["timer_label"] = "3 Min"
            bot.answer_callback_query(call.id, "⏱️ টাইমার ৩ মিনিট সেট হয়েছে!")
        elif val == "0":
            j["timer_sec"] = 0
            j["timer_label"] = "OFF"
            j["waiting"] = False
            bot.answer_callback_query(call.id, "🔴 টাইমার বন্ধ করা হয়েছে!")
        elif val == "cust":
            prompt = bot.send_message(
                call.message.chat.id,
                f"✏️ <b>{call.from_user.first_name}</b>, কত মিনিট টাইমার দেবেন তা লিখুন (যেমন: <code>2</code> বা <code>2.5</code>):"
            )
            custom_timer_wait[call.from_user.id] = (jid, call.message.chat.id, j["msg_id"], prompt.message_id)
            bot.answer_callback_query(call.id)
            return

        update_main_message(jid, call.message.chat.id, j["msg_id"])
        return

    if action == "start":
        j["receiver"] = sprinter_name
        bot.answer_callback_query(call.id, f"🚀 {sprinter_name} কাজ শুরু করেছেন!")
    elif action in ["done", "noe", "serv"]:
        if j.get("waiting", False):
            bot.answer_callback_query(call.id, f"⏳ টাইমার চলছে! {j['timer_label']} পূর্ণ হলে পরের নম্বর আসবে।", show_alert=True)
            return
        if j["current_idx"] < len(j["numbers"]):
            if sprinter_name not in sprinter_stats:
                sprinter_stats[sprinter_name] = {"done": 0, "noe": 0, "serv": 0}

            if action == "done":
                j["statuses"][j["current_idx"]] = "🟢"
                j["done"] += 1
                sprinter_stats[sprinter_name]["done"] += 1
            elif action == "noe":
                j["statuses"][j["current_idx"]] = "🔵"
                j["noe"] += 1
                sprinter_stats[sprinter_name]["noe"] += 1
            elif action == "serv":
                j["statuses"][j["current_idx"]] = "🔴"
                j["serv"] += 1
                sprinter_stats[sprinter_name]["serv"] += 1

            j["current_idx"] += 1
            j["receiver"] = sprinter_name

            if j["timer_sec"] > 0 and j["current_idx"] < len(j["numbers"]):
                j["waiting"] = True
                t = threading.Timer(j["timer_sec"], unlock_next_number, args=(jid, call.message.chat.id, call.message.message_id))
                t.daemon = True
                t.start()
                bot.answer_callback_query(call.id, f"⏳ {j['timer_label']} পর পরের নম্বর শো করবে!")
            else:
                bot.answer_callback_query(call.id, "✅ আপডেট হয়েছে!")
        else:
            bot.answer_callback_query(call.id, "✅ সব নম্বর শেষ!", show_alert=True)
            return
    elif action == "shov":
        j["show_list"] = not j.get("show_list", False)
        bot.answer_callback_query(call.id, "👁️ লিস্ট পরিবর্তন করা হয়েছে।")
    elif action == "chat":
        if ADMIN_ID and call.from_user.id != ADMIN_ID:
            bot.answer_callback_query(call.id, "⛔ শুধুমাত্র Admin চ্যাট অন/অফ করতে পারবেন!", show_alert=True)
            return
        j["chat_open"] = not j["chat_open"]
        try:
            perms = ChatPermissions(can_send_messages=j["chat_open"])
            bot.set_chat_permissions(call.message.chat.id, perms)
            st_msg = "🔓 গ্রুপ চ্যাট সবার জন্য খোলা হয়েছে!" if j["chat_open"] else "🔒 গ্রুপ চ্যাট বন্ধ (শুধু Admin) করা হয়েছে!"
            bot.answer_callback_query(call.id, st_msg, show_alert=True)
        except Exception as e:
            bot.answer_callback_query(call.id, f"⚠️ চ্যাট লক করতে বটকে Admin পারমিশন দিন! ({e})", show_alert=True)
        return
    elif action == "clip":
        if not clip_data["numbers"]:
            bot.answer_callback_query(call.id, "⚠️ Clip খালি! বটের ইনবক্সে /clip লিখে নম্বর পাঠান।", show_alert=True)
            return
        idx = clip_data["idx"]
        total_c = len(clip_data["numbers"])
        num = clip_data["numbers"][idx]
        kb = InlineKeyboardMarkup()
        kb.add(
            InlineKeyboardButton("⏮️ Prev", callback_data="clipprev_0"),
            InlineKeyboardButton("⏭️ Next Clip", callback_data="clipnext_0"),
            InlineKeyboardButton("❌ Close", callback_data="clipclose_0")
        )
        bot.send_message(
            call.message.chat.id,
            f"📋 <b>CLIPBOARD ({idx+1}/{total_c})</b>\nএক চাপে কপি করুন:\n<code>{num}</code>",
            reply_markup=kb
        )
        bot.answer_callback_query(call.id)
        return
    elif action == "dele":
        if ADMIN_ID and call.from_user.id != ADMIN_ID:
            bot.answer_callback_query(call.id, "⛔ শুধুমাত্র Admin ডিলিট করতে পারবেন!", show_alert=True)
            return
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.answer_callback_query(call.id, "🗑️ ডিলিট করা হয়েছে।")
        return
    elif action == "orig":
        all_nums = "\n".join(j["numbers"])
        bot.answer_callback_query(call.id, "📁 Original লিস্ট পাঠানো হচ্ছে...")
        bot.send_message(call.message.chat.id, f"📁 <b>Original List (#{jid}):</b>\n<code>{all_nums}</code>")
        return
    elif action == "graph":
        bot.answer_callback_query(
            call.id,
            f"📊 রিপোর্ট #{jid}:\n🟢 Done: {j['done']}\n🔵 No Entry: {j['noe']}\n🔴 Server: {j['serv']}\nমোট: {len(j['numbers'])}",
            show_alert=True
        )
        return
    else:
        bot.answer_callback_query(call.id, f"🔔 {action.upper()} ({sprinter_name})")
        return

    update_main_message(jid, call.message.chat.id, call.message.message_id)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    threading.Thread(target=midnight_report_scheduler, daemon=True).start()
    while True:
        try:
            bot.infinity_polling(
                timeout=30,
                long_polling_timeout=25,
                allowed_updates=["message", "callback_query", "chat_join_request", "message_reaction"]
            )
        except Exception:
            time.sleep(3)

@bot.message_handler(commands=['update'])
def self_update_cmd(message):
    if message.chat.type == 'private' and (not ADMIN_ID or message.from_user.id == ADMIN_ID):
        if message.reply_to_message and message.reply_to_message.document:
            file_info = bot.get_file(message.reply_to_message.document.file_id)
            downloaded = bot.download_file(file_info.file_path)
            with open("bot.py", "wb") as f:
                f.write(downloaded)
            bot.reply_to(message, "✅ নতুন কোড সেভ হয়েছে! বট রিস্টার্ট হচ্ছে...")
            os._exit(0)
        else:
            bot.reply_to(message, "⚠️ নতুন কোড ফাইলটি পাঠিয়ে সেটিতে রিপ্লাই দিয়ে <code>/update</code> লিখুন।")
