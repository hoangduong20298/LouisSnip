import requests
import time
import telebot
import threading
from datetime import datetime, timedelta
import logging

# Replace with your Telegram bot API token
API_TOKEN = '7117911467:AAECnzaC5ZgRqzrHOJwb49mx3bcZCaS-u2o'
bot = telebot.TeleBot(API_TOKEN)
bot.set_webhook()
CHANNEL_ID = '@louisgamblesmeme'  # or use channel ID as an integer
# GMGN API endpoint for top coins on Pump.fun buy
GMGN_API_URL = "https://gmgn.ai/defi/quotation/v1/pairs/sol/new_pair_ranks/1m?limit=100"

# Global variable to store the chat ID of the user who starts the bot
user_chat_id = None

# Dictionary to track the last alert time for each contract address
alerted_contracts = {}
user_chat_ids = []
# Setup logging
logging.basicConfig(filename='skipped_alerts.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@bot.message_handler(commands=['start'])
def start_bot(message):
    global user_chat_ids
    user_chat_id = message.chat.id

    if user_chat_id not in user_chat_ids:
        user_chat_ids.append(user_chat_id)
        print("Received /start command from chat ID: {}".format(user_chat_id))  # Debugging output
        bot.reply_to(message, "Bot started! You will receive alerts in this chat.")
    else:
        print("Chat ID {} has already started the bot.".format(user_chat_id))  # Debugging output
        bot.reply_to(message, "You have already started the bot. You will receive alerts in this chat.")


# Function to fetch data from the GMGN API
def fetch_data():
    try:
        response = requests.get(GMGN_API_URL)
        response.raise_for_status()
        data = response.json().get('data', {})

        # Combine all lists and include the source
        combined_data = [
            {**item, "source": "New Pool"} for item in data.get('new_pools', [])
        ] + [
            {**item, "source": "Burnts"} for item in data.get('burnts', [])
        ] + [
            {**item, "source": "Dexscreener Spents"} for item in data.get('dexscreener_spents', [])
        ]

        return combined_data

    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching data: {e}")
        return []

# Function to find the coin with the highest buy volume in the last 5 minutes
def find_highest_volume_coin(coins):
    if not coins:
        return None

    for coin in coins:
        # Log missing keys
        base_info = coin.get('base_token_info', {})
        if 'buy_volume_5m' not in base_info:
            logging.warning(f"Missing 'buy_volume_5m' in coin data: {base_info}")

    # Use the .get() method to handle missing keys and provide a default value of 0
    highest_volume_coin = max(
        coins,
        key=lambda coin: float(coin['base_token_info'].get('buy_volume_5m', 0)),
        default=None
    )
    return highest_volume_coin


def safe_float(value):
    try:
        return float(value)
    except ValueError:
        return 0.0



def send_alert(coin_data):
    base_token_info = coin_data['base_token_info']
    contract_address = base_token_info.get('address', 'N/A')
    burn_ratio = safe_float(base_token_info.get('burn_ratio', '0')) * 100
    top_10_holder_rate = safe_float(base_token_info.get('top_10_holder_rate', '0')) * 100
    creator_balance_usd = safe_float(coin_data.get('quote_reserve_usd', '0'))
    buy_volume = safe_float(base_token_info.get('buy_volume', '0'))
    sell_volume = safe_float(base_token_info.get('sell_volume', '0'))
    renounced_status = base_token_info.get('renounced', None)
    freeze_revoked_status = base_token_info.get('renounced_freeze_account', None)
    creator_balance_sol = coin_data.get('quote_reserve', 'N/A')
    transactions = base_token_info.get('swaps_24h', 0)
    source = coin_data.get('source', 'Unknown Source')  # Get the source of the coin
    price_change_percent5m = safe_float(base_token_info.get('price_change_percent5m', '0'))
    # Skip sending the alert if an alert has already been sent for this contract address within the past hour
    if contract_address in alerted_contracts:
        last_alert_time = alerted_contracts[contract_address]
        if datetime.now() - last_alert_time < timedelta(minutes=5):
           # logging.info(f"Skipped alert for {base_token_info['name']} ({base_token_info['symbol']}) as it was alerted recently.")
            return

    # Determine renounced and freeze revoked status
    renounced_status_str = "✅" if renounced_status else "❌"
    freeze_revoked_str = "✅" if freeze_revoked_status else "❌"

    # Determine if the dev wallet has enough money and a decent history
    dev_wallet_status = "🟢 Dev Wallet Has Enough Money" if float(creator_balance_usd) > 500 else "🔴 Dev Wallet Might Not Have Enough Money"
    wallet_history_status = "🟢 Wallet Has Decent History" if transactions > 50 else "🔴 Wallet Has Limited History"

    # Compile the alert message
    message = (
        f"🪙 **Token**: {base_token_info['name']} ({base_token_info['symbol']})\n\n"
        f"🧩 **CA**: {contract_address}\n\n"

        f"💡 **Market Cap**: ${float(base_token_info.get('market_cap', 0)):,}\n"
        f"💧 **Liquidity**: ${float(base_token_info.get('liquidity', 0)):,}\n"
        f"💰 **Token Price**: ${base_token_info.get('price', 'N/A')}\n"
        f"⛽️ **Pooled SOL**: {coin_data.get('quote_reserve', 'N/A')} SOL\n"
        f"💰 **Buy Volume**: ${buy_volume:,}\n"
        f"💰 **Sell Volume**: ${sell_volume:,}\n"
        f"🚀 **5m Change**: {price_change_percent5m:.2f}%\n"
        f"👥 **Holders**: {base_token_info.get('holder_count', 'N/A')}\n\n"
        f"🏦 **Top Holders rate**: {top_10_holder_rate:.2f}%\n\n"
        f"🔥 **Burn Ratio**: {burn_ratio:.2f}%\n"
        f"👤 **Renounced**: {renounced_status_str}\n"
        f"🗯️ **Freeze Revoked**: {freeze_revoked_str}\n\n"
        f"👨🏻‍💻 **Creator Info**:\n"
        f"  - **Balance SOL**: {creator_balance_sol}\n"
        f"  - **Balance USD**: ${float(creator_balance_usd):.2f}\n"
        f"  - **Transactions**: {transactions}\n"
        f"  - {dev_wallet_status}\n"
        f"  - {wallet_history_status}\n\n"
        f"📡 **Source Coins**: {source}\n\n"  # Include the source in the message
    )

        # Add the Fast Trade button for MEVX with a preview link name
    fast_trade_link = f"[MEVX🚀](https://mevx.io/solana/{contract_address})"
    message += f"{fast_trade_link}\n\n"


     # Check if social links exist and add them to the message
    social_links = base_token_info.get('social_links', {})
    if social_links:
        social_message = ""
        if "twitter_username" in social_links:
            social_message += f"🐦 [Twitter](https://twitter.com/{social_links['twitter_username']})\n"
        if "website" in social_links:
            social_message += f"🌐 [Website]({social_links['website']})\n"
        if "telegram" in social_links:
            social_message += f"📢 [Telegram]({social_links['telegram']})\n"

        message += f"🔗 **Social Links**:\n{social_message}"



    if CHANNEL_ID:
        try:
            bot.send_message(CHANNEL_ID, message, parse_mode='Markdown')
            # Update the last alert time for this contract address
            alerted_contracts[contract_address] = datetime.now()
        except telebot.apihelper.ApiException as e:
            logging.error("Error sending message: {}".format(e))
    else:
        logging.info("No channel ID is set. Alert not sent.")


# Main loop to fetch data every 1000ms and send alerts
def main():
    while True:
        coins = fetch_data()

        if coins:
            highest_volume_coin = find_highest_volume_coin(coins)
            if highest_volume_coin:
                base_token_info = highest_volume_coin['base_token_info']
                contract_address = base_token_info.get('address', 'N/A')
                # Print the coin details and send an alert
                print(f"🚀 High Volume Coin: {base_token_info['name']} ({base_token_info['symbol']}) | Volume: {base_token_info['buy_volume_1m']} | Price: {base_token_info['price']} | Market Cap: {base_token_info['market_cap']} | Contract Address: {contract_address}| Source: {highest_volume_coin.get('source', 'Unknown Source')}")
                send_alert(highest_volume_coin)

        # Wait for 1000 milliseconds before the next request
        time.sleep(1)

# Start the bot polling in a separate thread
threading.Thread(target=bot.polling, daemon=True).start()

if __name__ == "__main__":
    main()
