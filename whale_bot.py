import time
import asyncio
from web3 import AsyncWeb3, AsyncHTTPProvider

BASE_RPC_URL = "https://mainnet.base.org"
w3 = AsyncWeb3(AsyncHTTPProvider(BASE_RPC_URL))

USDC_ADDRESS = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
TRANSFER_SIG = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
WHALE_THRESHOLD = 100_000 * (10 ** 6)

async def fetch_receipt(tx_hash):
    try:
        return await w3.eth.get_transaction_receipt(tx_hash)
    except Exception:
        return None

async def scan_block(block_number):
    print(f"Scanning Block: {block_number}")
    block = await w3.eth.get_block(block_number, full_transactions=True)
    
    tasks = [fetch_receipt(tx.hash) for tx in block.transactions]
    receipts = await asyncio.gather(*tasks)
    
    whale_found = 0
    for receipt in receipts:
        if not receipt: continue
        for log in receipt.logs:
            if log.address.lower() == USDC_ADDRESS.lower() and log.topics[0].hex() == TRANSFER_SIG:
                amount = int(log.data.hex(), 16)
                if amount >= WHALE_THRESHOLD:
                    actual_amount = amount / (10 ** 6)
                    print(f"🚨 WHALE DETECTED! Block: {block_number} | Amount: {actual_amount:,.2f} USDC")
                    print(f"🔗 https://basescan.org/tx/{receipt.transactionHash.hex()}\n")
                    whale_found += 1
    return whale_found

async def main():
    if not await w3.is_connected():
        print("🔴 Connection Failed!")
        return

    print("🟢 24/7 Whale Tracker Started on Base Network...")
    last_scanned_block = await w3.eth.block_number
    
    while True:
        try:
            current_block = await w3.eth.block_number
            
            if current_block > last_scanned_block:
                for block_to_scan in range(last_scanned_block + 1, current_block + 1):
                    await scan_block(block_to_scan)
                    last_scanned_block = block_to_scan
            else:
                await asyncio.sleep(5)
                
        except Exception as e:
            print(f"⚠️ Error: {e}")
            await asyncio.sleep(10)

if __name__ == "__main__":
    asyncio.run(main())