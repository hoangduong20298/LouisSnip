import requests
import time
import telebot
import threading
from datetime import datetime, timedelta
import logging
import json
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import tls_client
# Replace with your Telegram bot API token
API_TOKEN = '7204915612:AAHiF3fqBoHgnplJFDWpv1v2MseOFik0MsE'
bot = telebot.TeleBot(API_TOKEN)
bot.set_webhook()
CHANNEL_ID = '@louisgamblesmeme'  # or use channel ID as an integer
# GMGN API endpoint for top coins on Pump.fun buy

# Global variable to store the chat ID of the user who starts the bot
user_chat_id = None

# Dictionary to track the last alert time for each contract address
alerted_contracts = {}
user_chat_ids = []
# Setup logging
logging.basicConfig(filename='skipped_alerts.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Function to fetch data from the GMGN API
def get_top_pumping_tokens(limit):
    limit = min(50, max(1, limit))
    GMGN_API_URL = f"https://gmgn.ai/defi/quotation/v1/rank/sol/pump?limit={limit}&orderby=progress&direction=desc&pump=true"
    try:
        headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:101.0) Gecko/20100101 Firefox/101.0',
        }
        s = tls_client.Session(
        client_identifier="okhttp4_android_7",random_tls_extension_order=True
        )
        response = s.get(GMGN_API_URL,headers=headers)
            #print(response)
            #response.raise_for_status()
        if response.status_code == 200:
            data = response.json()

            if isinstance(data, dict) and 'data' in data:
                if isinstance(data['data'], dict):
                    for key, value in data['data'].items():
                        if isinstance(value, list):
                            return value
                    print("No list found in the 'data' dictionary")
                else:
                    print(f"'data' value is not a dict, it's a {type(data['data'])}")
            else:
                print("Unexpected data format in the API response")
        else:
            print(f"Request failed with status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data: {e}")
        return []
        
        # except HTTPStatusError as e:
        #     print(f"API request failed with status code: {e.response.status_code}")
        #     return []
        # except httpx.RequestError as e:
        #     print(f"An error occurred while fetching data: {e}")
        #     return []
        # except json.JSONDecodeError as e:
        #     print(f"Error decoding JSON response: {e}")
        #     print("Raw response content:")
        #     print(response.text)
        #     return []


def safe_float(value):
    if value is not None:
        result = float(value)
    else:
        result = 0.0
    return result



def send_alert(token):
    """
    Formats the token information for display.

    Args:
    token (dict): A dictionary containing token information

    Returns:
    str: A formatted string with token details
    """
    created_time = datetime.fromtimestamp(token.get('created_timestamp', 0))
    time_difference = datetime.now() - created_time
    minutes = time_difference.total_seconds() // 60
    seconds = time_difference.total_seconds() % 60
    # Format the age as '5m3s'
    age = f"{int(minutes)}m{int(seconds)}s"
    last_trade_time = datetime.fromtimestamp(token.get('last_trade_timestamp', 0)).strftime('%Y-%m-%d %H:%M:%S')
    contract_address = token.get('address', 'N/A')
    creator_balance = token.get('creator_balance', 'N/A')
    creator_token_balance = token.get('creator_token_balance', 'N/A')
    swaps = float(token.get('swaps_1m', 'N/A'))
    volume = float(token.get('volume_1m', 0))  # Use 0 as the default to avoid errors with 'N/A'
    # Calculate the number of fire emojis
    fire_count = int(volume // 1000)
    # Generate the fire emoji string
    fire = '🔥' * fire_count
    # Example output
     #print(fire)
     #print(f"{fire} volume {volume}")
    # Skip sending the alert if an alert has already been sent for this contract address within the past hour
    if contract_address in alerted_contracts:
        last_alert_time = alerted_contracts[contract_address]
        if datetime.now() - last_alert_time < timedelta(minutes=3):
           # logging.info(f"Skipped alert for {base_token_info['name']} ({base_token_info['symbol']}) as it was alerted recently.")
            return

    message= (
            f"{fire}\n"
            f"CA: {contract_address}\n"
            f"Symbol: {token.get('symbol', 'N/A')}\n"
            f"Name: {token.get('name', 'N/A')}\n"
            f"Price: ${safe_float(token.get('price', 'N/A')):.8f}\n"
            f"Market Cap: ${safe_float(token.get('usd_market_cap', 'N/A')):,.2f}\n"
            f"Age: {age}\n"
            f"Progress: {safe_float(token.get('progress', 'N/A')):.2%}\n"
            f"Holder Count: {token.get('holder_count', 'N/A')}\n"
            f"**Top Holders rate**: {safe_float(token.get('top_10_holder_rate')):.2f}%\n\n"
            f"Volume (1h): ${safe_float(token.get('volume_1h', 'N/A')):,.2f}\n"
            f"Price Change (5m): {safe_float(token.get('price_change_percent5m', 'N/A'))}%\n"
            f"--------------------\n"
            f"👨🏻‍💻 **Creator Info**:\n"
            f"  - **Token**: {creator_token_balance}\n"
            f"  - **Balance SOL**: {float(creator_balance):.2f} SOL\n"
            f"--------------------\n"
            #f"[MEVX🚀](https://mevx.io/solana/{contract_address}?ref=louishd)\n\n"
            f"--------------------\n"
            f"🌐Website: {token.get('website', 'N/A')}\n"
            f"🐦Twitter: {token.get('twitter', 'N/A')}\n"
            f"📢Telegram: {token.get('telegram', 'N/A')}\n"
            f"--------------------\n")
        # Determine if the dev wallet has enough money and a decent history
    url_Mevx= f"https://mevx.io/solana/{contract_address}?ref=louishd"
    url_ST= f"https://t.me/SolTradingBot?start={contract_address}-rtTFIhoCo"
    # Add the Fast Trade button for MEVX with a preview link name
    btn_markup=InlineKeyboardMarkup([
        [InlineKeyboardButton(text='MevX 🚀', url=url_Mevx)],[InlineKeyboardButton(text='STBOT 🚀', url=url_ST)],
    ])
    #message+=btnGr

    if CHANNEL_ID:
        try:
            bot.send_message(CHANNEL_ID, message, parse_mode='Markdown', disable_web_page_preview=True,reply_markup=btn_markup)
            # Update the last alert time for this contract address
            alerted_contracts[contract_address] = datetime.now()
        except telebot.apihelper.ApiException as e:
            print("Error sending message: {}".format(e))
    else:
        print("No channel ID is set. Alert not sent.")

# Function to find the coin with the highest buy volume in the last 5 minutes
def find_highest_volume_coin(coins):
    if not coins:
        return 0

    for coin in coins:
        # Log missing keys
        if 'volume_1m' not in coin:
            continue
         #   print(f"Missing 'volume_1m' in coin data: {coins}")

    # Use the .get() method to handle missing keys and provide a default value of 0
        highest_volume_coin = max(
            coins,
            key=lambda coin: safe_float(coin.get('volume_1m', 0)),
            default=0
        )
        return highest_volume_coin

# Main loop to fetch data every 1000ms and send alerts
def main():
    while True:
        coins = get_top_pumping_tokens(10)
        if coins:
            highest_volume_coin = find_highest_volume_coin(coins)
            if highest_volume_coin:
                contract_address = highest_volume_coin.get('address', 'N/A')
                # Print the coin details and send an alert
                print(f"🚀 High Volume Coin: {highest_volume_coin['name']} ({highest_volume_coin['symbol']}) | Volume: {highest_volume_coin['volume_1m']} | Price: {highest_volume_coin['price']} | Market Cap: {highest_volume_coin['usd_market_cap']} | Contract Address: {contract_address}| Source: {highest_volume_coin.get('source', 'Unknown Source')}")
                send_alert(highest_volume_coin)

        # Wait for 1000 milliseconds before the next request
        time.sleep(5)

# Start the bot polling in a separate thread
threading.Thread(target=bot.polling, daemon=True).start()

if __name__ == "__main__":
    main()
