from web3 import Web3, AsyncWeb3
import json
import os
from dotenv import load_dotenv
from eth_account import Account
import time
import asyncio
from typing import List, Dict, Tuple
import argparse

# 加载环境变量
load_dotenv()

# 连接到 BSC
BSC_RPC = "https://bsc-dataseed.binance.org/"
w3 = Web3(Web3.HTTPProvider(BSC_RPC))
# 异步 web3
w3_async = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(BSC_RPC))

# Token ABI
TOKEN_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "account", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"internalType": "uint8", "name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function"
    }
]

def load_wallets(filename: str) -> List[Dict]:
    """加载钱包文件"""
    with open(filename, 'r') as f:
        return json.load(f)

async def get_token_decimals(token_contract) -> int:
    """获取代币精度"""
    return await token_contract.functions.decimals().call()

async def check_balances(addresses: List[str], token_address: str) -> List[Tuple[float, float]]:
    """同时检查所有钱包的 BNB 和代币余额"""
    # 创建异步合约实例
    token_contract = w3_async.eth.contract(address=token_address, abi=TOKEN_ABI)
    
    # 获取代币精度
    decimals = await get_token_decimals(token_contract)
    
    async def check_single_wallet(address: str) -> Tuple[float, float]:
        # 同时获取 BNB 和代币余额
        bnb_balance, token_balance = await asyncio.gather(
            w3_async.eth.get_balance(address),
            token_contract.functions.balanceOf(address).call()
        )
        
        return (
            w3.from_wei(bnb_balance, 'ether'),
            token_balance / (10 ** decimals)
        )
    
    # 为所有钱包创建查询任务
    tasks = [check_single_wallet(addr) for addr in addresses]
    
    # 同时执行所有任务
    return await asyncio.gather(*tasks)

def batch_transfer_bnb(from_account: Account, to_addresses: List[str], amount_in_bnb: float):
    """批量转账 BNB"""
    nonce = w3.eth.get_transaction_count(from_account.address)
    gas_price = w3.eth.gas_price
    transactions = []
    
    for to_address in to_addresses:
        transaction = {
            'from': from_account.address,
            'to': to_address,
            'value': w3.to_wei(amount_in_bnb, 'ether'),
            'gas': 21000,
            'gasPrice': gas_price,
            'nonce': nonce
        }
        
        signed_txn = w3.eth.account.sign_transaction(transaction, from_account.key)
        transactions.append(signed_txn)
        nonce += 1
    
    # 批量发送交易
    tx_hashes = []
    for signed_txn in transactions:
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        tx_hashes.append(tx_hash)
    
    return tx_hashes

async def wait_for_transactions(tx_hashes: List[str]):
    """异步等待所有交易确认"""
    async def wait_for_tx(tx_hash):
        receipt = await w3_async.eth.wait_for_transaction_receipt(tx_hash)
        print(f"交易确认: {tx_hash.hex()}")
        return receipt
    
    return await asyncio.gather(*[wait_for_tx(tx) for tx in tx_hashes])

async def main():
    try:
        # 设置命令行参数
        parser = argparse.ArgumentParser(description='批量转账 BNB 和查询余额')
        parser.add_argument('--balance', action='store_true', help='只查询余额')
        args = parser.parse_args()
        
        # 加载主钱包
        main_account = Account.from_key(os.getenv("PRIVATE_KEY"))
        token_address = w3.to_checksum_address(os.getenv("COCO_TOKEN_ADDRESS"))
        
        # 加载目标钱包列表
        wallets = load_wallets('wallets/wallets_20241201_044109.json')
        addresses = [wallet['address'] for wallet in wallets]
        
        print(f"主钱包地址: {main_account.address}")
        
        # 检查所有钱包余额
        print("\n检查所有钱包余额...")
        balances = await check_balances(addresses, token_address)
        
        print("\n当前余额:")
        for wallet, (bnb, token) in zip(wallets, balances):
            print(f"钱包 {wallet['index']}: {wallet['address']}")
            print(f"BNB: {bnb:.4f}, Token: {token:.4f}")
        
        # 如果只是查询余额，到这里就结束
        if args.balance:
            return
            
        # 转账逻辑
        amount_per_wallet = 0.01
        total_amount = amount_per_wallet * len(wallets)
        
        print(f"\n将向 {len(wallets)} 个钱包每个转账 {amount_per_wallet} BNB")
        print(f"总共需要 {total_amount} BNB")
        
        confirm = input("是否继续? (y/n): ")
        if confirm.lower() != 'y':
            return
        
        print("\n开始批量转账...")
        tx_hashes = batch_transfer_bnb(main_account, addresses, amount_per_wallet)
        
        print("\n等待交易确认...")
        receipts = await wait_for_transactions(tx_hashes)
        
        print("\n等待区块链更新...")
        await asyncio.sleep(3)
        
        print("\n检查最终余额...")
        final_balances = await check_balances(addresses, token_address)
        
        print("\n最终余额:")
        for wallet, (bnb, token) in zip(wallets, final_balances):
            print(f"钱包 {wallet['index']}: {wallet['address']}")
            print(f"BNB: {bnb:.4f}, Token: {token:.4f}")
        
        # 检查交易状态
        failed_txs = [tx.hex() for receipt, tx in zip(receipts, tx_hashes) if receipt['status'] != 1]
        if failed_txs:
            print("\n以下交易失败:")
            for tx in failed_txs:
                print(f"- {tx}")
        else:
            print("\n所有交易成功!")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 