from web3 import Web3
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 连接到 BSC
BSC_RPC = "https://bsc-dataseed.binance.org/"
w3 = Web3(Web3.HTTPProvider(BSC_RPC))

# 合约地址
UNIVERSAL_ROUTER_ADDRESS = w3.to_checksum_address("0x1a0a18ac4becddbd6389559687d1a73d8927e416")

# 加载 ABI
with open('abis/pancake_universal_router.json', 'r') as f:
    UNIVERSAL_ROUTER_ABI = json.load(f)

def main():
    try:
        account = w3.eth.account.from_key(os.getenv("PRIVATE_KEY"))
        
        # 检查 BNB 余额
        balance = w3.eth.get_balance(account.address)
        bnb_balance = w3.from_wei(balance, 'ether')
        required_bnb = 0.01
        
        print(f"\n钱包余额:")
        print(f"地址: {account.address}")
        print(f"BNB 余额: {bnb_balance:.4f} BNB")
        print(f"需要: {required_bnb} BNB")
        
        if balance < w3.to_wei(required_bnb, 'ether'):
            print(f"错误: BNB 余额不足!")
            return
            
        # 使用新的交易参数
        commands = bytes.fromhex("0b08")
        inputs = [
            bytes.fromhex("0000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000001550f7dca70000"),
            # 修改第二个 input 中的 recipient 地址为我们的地址
            bytes.fromhex(
                "000000000000000000000000" + 
                account.address[2:].lower() +  # 移除 '0x' 前缀并转换为小写
                "000000000000000000000000000000000000000000000000001550f7dca700000000000000000000000000000000000000000000000000001281669589024c0900000000000000000000000000000000000000000000000000000000000000a000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002000000000000000000000000bb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c0000000000000000000000000a1513460bc54b897f9379554f5abe1f0e7fb286"
            )
        ]
        
        # 设置新的 deadline（当前时间 + 20分钟）
        deadline = int((datetime.now() + timedelta(minutes=20)).timestamp())
        
        # 创建合约实例并构建交易
        router = w3.eth.contract(address=UNIVERSAL_ROUTER_ADDRESS, abi=UNIVERSAL_ROUTER_ABI)
        transaction = router.functions.execute(
            commands,
            inputs,
            deadline
        ).build_transaction({
            'from': account.address,
            'gas': 366321,
            'gasPrice': w3.eth.gas_price,
            'nonce': w3.eth.get_transaction_count(account.address),
            'value': w3.to_wei(0.01, 'ether')
        })
        
        # 确认交易
        print(f"\n交易详情:")
        print(f"From: {account.address}")
        print(f"To: {UNIVERSAL_ROUTER_ADDRESS}")
        print(f"Value: 0.01 BNB")
        print(f"Deadline: {deadline}")
        confirm = input("是否继续? (y/n): ")
        if confirm.lower() != 'y':
            return
        
        # 签名并发送交易
        signed_txn = w3.eth.account.sign_transaction(transaction, os.getenv("PRIVATE_KEY"))
        tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
        print(f"交易已发送: {tx_hash.hex()}")
        
        # 等待交易确认
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
        if receipt['status'] == 1:
            print(f"交易成功!")
        else:
            print(f"交易失败!")
            
    except Exception as e:
        print(f"错误: {str(e)}")

if __name__ == "__main__":
    main()