import os
import time
import asyncio
import requests
from dotenv import load_dotenv
from web3 import AsyncWeb3, AsyncHTTPProvider

load_dotenv()

BASE_RPC_URL = os.getenv("BASE_RPC_URL")
w3 = AsyncWeb3(AsyncHTTPProvider(BASE_RPC_URL))

USDC_CONTRACTS = [
    "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913".lower(),
    "0xd9aAEc86B65D86f6A7B5B1b0c42FFA531710b6CA".lower()
]
TRANSFER_SIG = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

WHALE_THRESHOLD = 100_000 * (10 ** 6)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    try:
        requests.post(url, json=payload)
    except Exception:
        pass

async def fetch_receipt(tx_hash):
    try:
        return await w3.eth.get_transaction_receipt(tx_hash)
    except Exception:
        return None

async def scan_block(block_number):
    block = await w3.eth.get_block(block_number, full_transactions=True)
    tx_count = len(block.transactions)
    print(f"📡 Scanning Block: {block_number} | {tx_count} transactions...")
    
    tasks = [fetch_receipt(tx.hash) for tx in block.transactions]
    receipts = []
    
    chunk_size = 15
    for i in range(0, len(tasks), chunk_size):
        chunk = tasks[i:i + chunk_size]
        chunk_results = await asyncio.gather(*chunk)
        receipts.extend(chunk_results)
        await asyncio.sleep(0.2)
    
    whale_found = 0
    for receipt in receipts:
        if not receipt: continue
        for log in receipt.logs:
            if len(log.topics) > 0:
                topic0 = log.topics[0].hex()
                
                if log.address.lower() in USDC_CONTRACTS and topic0 == TRANSFER_SIG:
                    try:
                        amount = int(log.data.hex(), 16)
                        if amount >= WHALE_THRESHOLD:
                            actual_amount = amount / (10 ** 6)
                            tx_hash_str = receipt.transactionHash.hex()
                            
                            print(f"\n🚨 WHALE DETECTED! Amount: {actual_amount:,.2f} USDC\n")
                            
                            tg_msg = (
                                f"🐋 <b>BASE WHALE ALERT!</b>\n\n"
                                f"💰 <b>Amount:</b> {actual_amount:,.2f} USDC\n"
                                f"📦 <b>Block:</b> {block_number}\n"
                                f"🔗 <a href='https://basescan.org/tx/{tx_hash_str}'>View on Basescan</a>"
                            )
                            send_telegram_message(tg_msg)
                            whale_found += 1
                    except Exception:
                        continue
    return whale_found

async def main():
    if not await w3.is_connected():
        print("🔴 Connection Failed! Check your .env file.")
        return

    print("🟢 Tracker Started (Alchemy)...")
    send_telegram_message("🟢 <b>Scanner Active!</b>\nHunting for whales over 100k USDC...")
    
    last_scanned_block = await w3.eth.block_number
    
    while True:
        try:
            current_block = await w3.eth.block_number
            if current_block > last_scanned_block:
                for block_to_scan in range(last_scanned_block + 1, current_block + 1):
                    await scan_block(block_to_scan)
                    last_scanned_block = block_to_scan
            else:
                await asyncio.sleep(2)
        except Exception as e:
            print(f"⚠️ Error: {e}")
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())