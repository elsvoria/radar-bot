import asyncio
import json
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from apscheduler.schedulers.asyncio import AsyncIOScheduler

import db
import scraper_tk

# Şifre kasasını yüklüyoruz
load_dotenv()

# BOT TOKEN'I GİZLİ DOSYADAN ÇEKİYORUZ
TOKEN = os.getenv("TELEGRAM_TOKEN")

bot = Bot(token=TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler()

# ... (KODUN GERİ KALANI BURADAN İTİBAREN AYNEN DEVAM EDECEK) ...

# --- YARDIMCI FONKSİYONLAR ---
def fiyat_hesapla(platform_sayisi, gun_sayisi):
    if gun_sayisi == 1 and platform_sayisi < 4:
        return 0 
        
    if platform_sayisi == 4:
        vip_fiyatlar = {1: 150, 3: 250, 7: 500, 10: 700, 30: 1500}
        if gun_sayisi in vip_fiyatlar: return vip_fiyatlar[gun_sayisi]
        if gun_sayisi <= 6: return gun_sayisi * 120
        if gun_sayisi <= 14: return gun_sayisi * 90
        return gun_sayisi * 60

    tekil_fiyatlar = {3: 100, 7: 200, 10: 250, 30: 500}
    if gun_sayisi in tekil_fiyatlar:
        return tekil_fiyatlar[gun_sayisi] * platform_sayisi
    
    if gun_sayisi <= 6: birim_fiyat = 40
    elif gun_sayisi <= 14: birim_fiyat = 30
    else: birim_fiyat = 20
    return (gun_sayisi * birim_fiyat) * platform_sayisi

def get_platform_keyboard(selected_platforms):
    btn_ig = "✅ Instagram" if "ig" in selected_platforms else "📷 Instagram"
    btn_tk = "✅ TikTok" if "tk" in selected_platforms else "🎵 TikTok"
    btn_tw = "✅ Twitter (X)" if "tw" in selected_platforms else "🐦 Twitter (X)"
    btn_wa = "✅ WhatsApp" if "wa" in selected_platforms else "💬 WhatsApp"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_ig, callback_data="plat_ig"),
         InlineKeyboardButton(text=btn_tk, callback_data="plat_tk")],
        [InlineKeyboardButton(text=btn_tw, callback_data="plat_tw"),
         InlineKeyboardButton(text=btn_wa, callback_data="plat_wa")],
        [InlineKeyboardButton(text="Next ➡", callback_data="plat_next")]
    ])

# --- DURUM MAKİNESİ (FSM) ---
class RadarFlow(StatesGroup):
    platform_select = State()
    get_link_ig = State()
    get_link_tk = State()
    get_link_tw = State()
    get_link_wa = State()
    duration_select = State()
    custom_duration = State()
    checkout = State()
    promo_code = State()

# --- 1. BAŞLANGIÇ ---
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await state.update_data(selected_platforms=[])
    
    keyboard = get_platform_keyboard([])
    welcome_text = (
        "🎯 *Welcome to Radar Bot!*\n\n"
        "I can track all movements of target accounts (public or private) in real-time.\n"
        "Please select the platforms you want to track:"
    )
    await message.answer(welcome_text, reply_markup=keyboard, parse_mode="Markdown")
    await state.set_state(RadarFlow.platform_select)

# --- 2. PLATFORM SEÇİMİ ---
@dp.callback_query(StateFilter(RadarFlow.platform_select))
async def platform_handler(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    selected = data.get('selected_platforms', [])

    if callback.data == "plat_next":
        if not selected:
            await callback.answer("Please select at least one platform!", show_alert=True)
            return
        
        if "ig" in selected:
            await callback.message.edit_text("🔗 Send the *Instagram* username or profile link of the target:", parse_mode="Markdown")
            await state.set_state(RadarFlow.get_link_ig)
        elif "tk" in selected:
            await callback.message.edit_text("🔗 Send the *TikTok* username or profile link of the target:", parse_mode="Markdown")
            await state.set_state(RadarFlow.get_link_tk)
        elif "tw" in selected:
            await callback.message.edit_text("🔗 Send the *Twitter (X)* username or profile link of the target:", parse_mode="Markdown")
            await state.set_state(RadarFlow.get_link_tw)
        elif "wa" in selected:
            await callback.message.edit_text("🔗 Send the *WhatsApp* number of the target:", parse_mode="Markdown")
            await state.set_state(RadarFlow.get_link_wa)
        return

    plat_code = callback.data.split("_")[1]
    if plat_code in selected:
        selected.remove(plat_code)
    else:
        selected.append(plat_code)
        
    await state.update_data(selected_platforms=selected)
    new_keyboard = get_platform_keyboard(selected)
    await callback.message.edit_reply_markup(reply_markup=new_keyboard)
    await callback.answer()

# --- 3. LİNK TOPLAMA ---
@dp.message(StateFilter(RadarFlow.get_link_ig))
async def process_ig_link(message: Message, state: FSMContext):
    data = await state.get_data()
    selected = data['selected_platforms']
    await state.update_data(target_ig=message.text)
    
    if "tk" in selected:
        await message.answer("🔗 Send the *TikTok* username or profile link of the target:", parse_mode="Markdown")
        await state.set_state(RadarFlow.get_link_tk)
    elif "wa" in selected:
        await message.answer("🔗 Send the *WhatsApp* number of the target:", parse_mode="Markdown")
        await state.set_state(RadarFlow.get_link_wa)
    else:
        await ask_for_duration(message, state)

@dp.message(StateFilter(RadarFlow.get_link_tk))
async def process_tk_link(message: Message, state: FSMContext):
    data = await state.get_data()
    selected = data['selected_platforms']
    
    # Kullanıcı link gönderdiyse kullanıcı adını ayıklıyoruz
    username = message.text.split("/")[-1].replace("@", "").split("?")[0]
    await state.update_data(target_tk=username)
    
    if "tw" in selected:
        await message.answer("🔗 Send the *Twitter (X)* username or profile link of the target:", parse_mode="Markdown")
        await state.set_state(RadarFlow.get_link_tw)
    elif "wa" in selected:
        await message.answer("🔗 Send the *WhatsApp* number of the target:", parse_mode="Markdown")
        await state.set_state(RadarFlow.get_link_wa)
    else:
        await ask_for_duration(message, state)

# --- 4. SÜRE SEÇİMİ VE CHECKOUT ---
async def ask_for_duration(message: Message, state: FSMContext):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 Day (Free Trial)", callback_data="dur_1")],
        [InlineKeyboardButton(text="3 Days (-33%)", callback_data="dur_3"),
         InlineKeyboardButton(text="7 Days (-42%)", callback_data="dur_7")],
        [InlineKeyboardButton(text="10 Days (-50%)", callback_data="dur_10"),
         InlineKeyboardButton(text="30 Days (-66% VIP)", callback_data="dur_30")],
        [InlineKeyboardButton(text="Unlimited (Lifetime)", callback_data="dur_999"),
         InlineKeyboardButton(text="Custom", callback_data="dur_custom")],
        [InlineKeyboardButton(text="🔙 Back", callback_data="back_to_platforms")]
    ])
    text = "⏳ How long should this target stay on the Radar?"
    if isinstance(message, CallbackQuery):
        await message.message.edit_text(text, reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)
    await state.set_state(RadarFlow.duration_select)

@dp.callback_query(StateFilter(RadarFlow.duration_select))
async def duration_handler(callback: CallbackQuery, state: FSMContext):
    if callback.data == "back_to_platforms":
        data = await state.get_data()
        selected = data.get('selected_platforms', [])
        keyboard = get_platform_keyboard(selected)
        await callback.message.edit_text("🎯 Please select the platforms you want to track:", reply_markup=keyboard)
        await state.set_state(RadarFlow.platform_select)
        await callback.answer()
        return

    if callback.data == "dur_custom":
        await callback.message.edit_text("✍️ Please enter the number of days you want to track:")
        await state.set_state(RadarFlow.custom_duration)
        return

    gun_str = callback.data.split("_")[1]
    gun = 999 if gun_str == "999" else int(gun_str)
    await checkout_olustur(callback.message, state, gun)
    await callback.answer()

@dp.message(StateFilter(RadarFlow.custom_duration))
async def custom_duration_handler(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Please enter numbers only.")
        return
    gun = int(message.text)
    await checkout_olustur(message, state, gun)

async def checkout_olustur(message, state: FSMContext, gun: int):
    data = await state.get_data()
    platformlar = data['selected_platforms']
    plat_sayisi = len(platformlar)
    
    fiyat = fiyat_hesapla(plat_sayisi, gun)
    await state.update_data(gun_sayisi=gun, fiyat=fiyat)
    
    hedef_kisi = data.get('target_tk') or data.get('target_ig') or data.get('target_wa') or data.get('target_tw')
    plat_isimleri = ", ".join([p.upper() for p in platformlar])
    
    ozet_metni = (
        f"📊 *Summary:*\n\n"
        f"🎯 *Target:* @{hedef_kisi}\n"
        f"📱 *Platforms:* {plat_isimleri}\n"
        f"⏳ *Duration:* {gun} Days\n"
        f"💰 *Total Price:* {fiyat} Stars"
    )
    
    if fiyat == 0:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Start Free Trial", callback_data="start_free_trial")]
        ])
    else:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"⭐️ Pay with {fiyat} Stars", callback_data="pay_now")],
            [InlineKeyboardButton(text="🎟 Use Promo Code", callback_data="use_promo")]
        ])
    
    if isinstance(message, Message):
        await message.answer(ozet_metni, reply_markup=keyboard, parse_mode="Markdown")
    else: 
        await message.edit_text(ozet_metni, reply_markup=keyboard, parse_mode="Markdown")
    
    await state.set_state(RadarFlow.checkout)

# Kayıt Tamamlama Yardımcı Fonksiyonu
async def kayit_tamamla(user_id: int, state: FSMContext):
    data = await state.get_data()
    gun = data.get('gun_sayisi', 1)
    platforms = data.get('selected_platforms', [])
    
    # 1. Kullanıcıyı ve aboneliği kaydet
    db.add_subscription(user_id, gun, platforms)
    
    # 2. Takip edilen hedefleri kaydet
    if 'target_tk' in data:
        db.add_target(user_id, data['target_tk'], "tiktok")
        
    await state.clear()

# --- 5. ÖDEME VE PROMOSYON İŞLEMLERİ ---
@dp.callback_query(StateFilter(RadarFlow.checkout), F.data == "pay_now")
async def process_pay_now(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    fiyat = data['fiyat']
    gun = data['gun_sayisi']
    
    prices = [LabeledPrice(label=f"{gun} Days Premium Tracking", amount=fiyat)]
    await bot.send_invoice(
        chat_id=callback.message.chat.id,
        title="Radar Bot Premium",
        description=f"Real-time tracking and instant notifications for {gun} days.",
        payload=f"premium_payment_{gun}",
        provider_token="", 
        currency="XTR",
        prices=prices
    )
    await callback.answer()

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(message: Message, state: FSMContext):
    await kayit_tamamla(message.from_user.id, state)
    await message.answer("✅ Payment successful! Premium activated. Targets are now being monitored in real-time.")

@dp.callback_query(StateFilter(RadarFlow.checkout), F.data == "use_promo")
async def ask_promo(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("🎟 Please enter your promo code:")
    await state.set_state(RadarFlow.promo_code)

@dp.message(StateFilter(RadarFlow.promo_code))
async def check_promo(message: Message, state: FSMContext):
    if message.text.lower() == "deneme":
        await kayit_tamamla(message.from_user.id, state)
        await message.answer("✅ Promo code accepted! 1-Day Trial started. Target is now being monitored.")
    else:
        await message.answer("❌ Invalid code. Please try again.")

@dp.callback_query(StateFilter(RadarFlow.checkout), F.data == "start_free_trial")
async def start_free_trial(callback: CallbackQuery, state: FSMContext):
    await kayit_tamamla(callback.from_user.id, state)
    await callback.message.edit_text("✅ 1-day free trial started! Target is now being monitored.")

# --- 6. PANEL KOMUTU (TAKİP EDİLENLERİ LİSTELEME) ---
@dp.message(Command("panel"))
async def cmd_panel(message: Message):
    user_id = message.from_user.id
    response = db.supabase.table("targets").select("*").eq("user_id", user_id).eq("status", "active").execute()
    targets = response.data
    
    if not targets:
        await message.answer("⚙️ *Your Panel*\n\nYou are not tracking any targets currently.", parse_mode="Markdown")
        return
        
    text = "⚙️ *Active Tracked Targets:*\n\n"
    keyboard_buttons = []
    
    for t in targets:
        text += f"• @{t['target_username']} ({t['platform'].upper()})\n"
        keyboard_buttons.append([InlineKeyboardButton(text=f"❌ Stop tracking @{t['target_username']}", callback_data=f"stop_{t['id']}")])
        
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    await message.answer(text, reply_markup=keyboard, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("stop_"))
async def stop_tracking(callback: CallbackQuery):
    target_id = int(callback.data.split("_")[1])
    db.supabase.table("targets").update({"status": "cancelled"}).eq("id", target_id).execute()
    await callback.message.edit_text("✅ Target removed from tracking list.")
    await callback.answer()

# --- 7. OTOMATİK TARAMA & BİLDİRİM DÖNGÜSÜ (SCHEDULER) ---
async def check_targets_job():
    """Her 10 dakikada bir veritabanındaki hedefleri kontrol eder ve fark varsa Telegram'a bildirim atar."""
    print("🔄 Scheduled check starting...")
    targets = db.supabase.table("targets").select("*").eq("status", "active").execute().data
    
    for t in targets:
        user_id = t["user_id"]
        username = t["target_username"]
        platform = t["platform"]
        
        if platform == "tiktok":
            # Scraper ile güncel repostları çekiyoruz
            current_reposts = scraper_tk.fetch_reposts_data(username)
            if not current_reposts:
                continue
                
            # Veritabanında kayıtlı olan repostları alıyoruz
            db_reposts = db.supabase.table("reposts").select("video_url").eq("target_username", username).execute().data
            existing_urls = [r["video_url"] for r in db_reposts]
            
            # YENİ REPOSTLAR
            for post in current_reposts:
                url = post.get("pageUrl")
                if url and url not in existing_urls:
                    # Supabase'e ekle
                    db.supabase.table("reposts").insert({
                        "target_username": username,
                        "video_url": url,
                        "title": post.get("title", ""),
                        "author_username": post.get("authorUsername", ""),
                        "status": "active"
                    }).execute()
                    
                    # Kullanıcıya Telegram Bildirimi Gönder
                    msg = (
                        f"🚨 *NEW REPOST DETECTED!*\n\n"
                        f"👤 *Target:* @{username}\n"
                        f"🎬 *Original Author:* @{post.get('authorUsername')}\n"
                        f"📝 *Caption:* {post.get('title')}\n\n"
                        f"🔗 [Watch Video]({url})"
                    )
                    try:
                        await bot.send_message(chat_id=user_id, text=msg, parse_mode="Markdown")
                    except Exception as e:
                        print(f"Failed to send notification to {user_id}: {e}")

# --- ANA ÇALIŞTIRMA DÖNGÜSÜ ---
async def main():
    print("Radar Bot is running with Scheduler...")
    # Scheduler: 10 dakikada bir otomatik çalışır
    scheduler.add_job(check_targets_job, 'interval', minutes=10)
    scheduler.start()
    await start_web()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

from aiohttp import web

async def health(request):
    return web.Response(text="ok")

async def start_web():
    app = web.Application()
    app.router.add_get("/", health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", 10000)))
    await site.start()
