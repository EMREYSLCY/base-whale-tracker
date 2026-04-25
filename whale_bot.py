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
        receipt = await w3.eth.get_transaction_receipt(tx_hash)
        return receipt
    except Exception:
        return None

async def scan_latest_block():
    print("Searching for the latest block on Base network (ASYNC MODE)...")
    latest_block_number = await w3.eth.block_number
    print(f"Latest block found: {latest_block_number}")
    
    block = await w3.eth.get_block(latest_block_number, full_transactions=True)
    tx_count = len(block.transactions)
    
    print(f"Block {latest_block_number} contains {tx_count} transactions.")
    print("Fetching transaction details in PARALLEL. Brace yourself...\n")
    
    start_time = time.time()
    whale_count = 0
    
    tasks = [fetch_receipt(tx.hash) for tx in block.transactions]
    receipts = await asyncio.gather(*tasks)
    
    for receipt in receipts:
        if receipt is None:
            continue
            
        for log in receipt.logs:
            if log.address.lower() == USDC_ADDRESS.lower() and log.topics[0].hex() == TRANSFER_SIG:
                amount = int(log.data.hex(), 16)
                
                if amount >= WHALE_THRESHOLD:
                    actual_amount = amount / (10 ** 6)
                    print(f"🚨 WHALE DETECTED! Amount: {actual_amount:,.2f} USDC")
                    print(f"🔗 Tx Hash: {receipt.transactionHash.hex()}\n")
                    whale_count += 1
            
    end_time = time.time()
    print(f"Scan complete! Total {whale_count} whale transactions found.")
    print(f"🚀 Time elapsed: {end_time - start_time:.2f} seconds")

async def main():
    if await w3.is_connected():
        print("🟢 Successfully connected to Base network (Async)!")
        await scan_latest_block()
    else:
        print("🔴 Failed to connect to Base network. Check your RPC URL.")

if __name__ == "__main__":
    asyncio.run(main())