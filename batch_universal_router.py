from web3 import Web3, AsyncWeb3
import json
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import asyncio
from typing import List, Dict

# 加载环境变量
load_dotenv()

# 连接到 BSC
BSC_RPC = "https://bsc-dataseed.binance.org/"
w3 = Web3(Web3.HTTPProvider(BSC_RPC))
w3_async = AsyncWeb3(AsyncWeb3.AsyncHTTPProvider(BSC_RPC))

# 合约地址
UNIVERSAL_ROUTER_ADDRESS = w3.to_checksum_address("0x1a0a18ac4becddbd6389559687d1a73d8927e416")

def load_wallets(filename: str) -> List[Dict]:
    """加载钱包文件"""
    with open(filename, 'r') as f:
        return json.load(f)

async def execute_trade(wallet: Dict, router_contract, commands: bytes, inputs: List[bytes], deadline: int):
    """执行单个钱包的交易"""
    try:
        account = w3.eth.account.from_key(wallet['private_key'])
        
        # 检查 BNB 余额
        balance = await w3_async.eth.get_balance(account.address)
        bnb_balance = w3.from_wei(balance, 'ether')
        required_bnb = 0.01
        
        print(f"\n钱包 {wallet['index']} 余额:")
        print(f"地址: {account.address}")
        print(f"BNB 余额: {bnb_balance:.4f} BNB")
        
        if balance < w3.to_wei(required_bnb, 'ether'):
            print(f"钱包 {wallet['index']} BNB 余额不足!")
            return False, "余额不足"
        
        # 修改 inputs 中的接收地址为当前钱包地址
        modified_inputs = [
            inputs[0],
            bytes.fromhex(
                "000000000000000000000000" + 
                account.address[2:].lower() +
                inputs[1][24:].hex()  # 保持其余数据不变
            )
        ]
        
        # 构建交易
        transaction = await router_contract.functions.execute(
            commands,
            modified_inputs,
            deadline
        ).build_transaction({
            'from': account.address,
            'gas': 366321,
            'gasPrice': await w3_async.eth.gas_price,
            'nonce': await w3_async.eth.get_transaction_count(account.address),
            'value': w3.to_wei(0.01, 'ether')
        })
        
        # 签名并发送交易
        signed_txn = w3.eth.account.sign_transaction(transaction, wallet['private_key'])
        tx_hash = await w3_async.eth.send_raw_transaction(signed_txn.rawTransaction)
        print(f"钱包 {wallet['index']} 交易已发送: {tx_hash.hex()}")
        
        # 等待交易确认
        receipt = await w3_async.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt['status'] == 1:
            print(f"钱包 {wallet['index']} 交易成功!")
            return True, receipt
        else:
            print(f"钱包 {wallet['index']} 交易失败!")
            return False, receipt
            
    except Exception as e:
        print(f"钱包 {wallet['index']} 交易错误: {str(e)}")
        return False, str(e)

async def main():
    try:
        # 加载 Router ABI
        with open('abis/pancake_universal_router.json', 'r') as f:
            ROUTER_ABI = json.load(f)
        
        # 创建合约实例
        router_contract = w3_async.eth.contract(
            address=UNIVERSAL_ROUTER_ADDRESS,
            abi=ROUTER_ABI
        )
        
        # 加载钱包列表
        wallets = load_wallets('wallets/wallets_20241201_044109.json')
        print(f"已加载 {len(wallets)} 个钱包")
        
        # 准备交易参数
        commands = bytes.fromhex("0b08")
        inputs = [
            bytes.fromhex("0000000000000000000000000000000000000000000000000000000000000002000000000000000000000000000000000000000000000000001550f7dca70000"),
            bytes.fromhex("000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000001550f7dca700000000000000000000000000000000000000000000000000001281669589024c0900000000000000000000000000000000000000000000000000000000000000a000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000000002000000000000000000000000bb4cdb9cbd36b01bd1cbaebf2de08d9173bc095c0000000000000000000000000a1513460bc54b897f9379554f5abe1f0e7fb286")
        ]
        deadline = int((datetime.now() + timedelta(minutes=20)).timestamp())
        
        # 先测试第一个钱包
        print("\n开始测试交易...")
        test_result = await execute_trade(wallets[0], router_contract, commands, inputs, deadline)
        
        if not test_result[0]:
            print("\n测试交易失败，建议检查后再尝试批量交易")
            return
            
        print("\n测试交易成功!")
        
        # 询问是否继续执行其他钱包
        response = input("\n是否继续执行其余钱包的交易? (y/n): ")
        if response.lower() != 'y':
            print("批量交易已取消")
            return
        
        # 创建剩余钱包的交易任务
        print("\n开始执行剩余钱包交易...")
        remaining_wallets = wallets[1:]
        tasks = [
            execute_trade(wallet, router_contract, commands, inputs, deadline)
            for wallet in remaining_wallets
        ]
        
        # 同时执行所有交易
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 将测试交易的结果加入到总结果中
        all_results = [test_result] + list(results)
        
        # 统计结果
        success_count = sum(1 for result in all_results if isinstance(result, tuple) and result[0])
        fail_count = len(all_results) - success_count
        
        print("\n交易统计:")
        print(f"成功: {success_count}")
        print(f"失败: {fail_count}")
        
        # 显示详细结果
        print("\n详细结果:")
        for wallet, result in zip(wallets, all_results):
            if isinstance(result, tuple):
                status = "成功" if result[0] else "失败"
                print(f"钱包 {wallet['index']}: {status}")
            else:
                print(f"钱包 {wallet['index']}: 错误 - {str(result)}")
        
    except Exception as e:
        print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main()) 