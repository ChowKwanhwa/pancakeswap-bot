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
PANCAKE_ROUTER = "0x10ED43C718714eb63d5aA57B78B54704E256024E"
WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
TOKEN = "0xF3c7CECF8cBC3066F9a87b310cEBE198d00479aC"

def load_wallets(filename: str) -> List[Dict]:
    """加载钱包文件"""
    with open(filename, 'r') as f:
        return json.load(f)

async def get_token_price(router_contract) -> tuple:
    """获取代币价格"""
    amount_in = w3.to_wei(0.01, 'ether')
    path = [WBNB, TOKEN]
    
    try:
        amounts_out = await router_contract.functions.getAmountsOut(
            amount_in,
            path
        ).call()
        return True, amounts_out[1]
    except Exception as e:
        return False, str(e)

async def execute_swap(wallet: Dict, router_contract, amount_out_min: int):
    """执行单个钱包的交易"""
    try:
        account = w3.eth.account.from_key(wallet['private_key'])
        amount_in = w3.to_wei(0.01, 'ether')
        path = [WBNB, TOKEN]
        deadline = int((datetime.now() + timedelta(minutes=20)).timestamp())
        
        # 构建交易
        transaction = await router_contract.functions.swapExactETHForTokensSupportingFeeOnTransferTokens(
            amount_out_min,
            path,
            account.address,
            deadline
        ).build_transaction({
            'from': account.address,
            'value': amount_in,
            'gas': 300000,
            'gasPrice': await w3_async.eth.gas_price,
            'nonce': await w3_async.eth.get_transaction_count(account.address),
        })
        
        # 签名并发送交易
        signed_txn = w3.eth.account.sign_transaction(transaction, wallet['private_key'])
        tx_hash = await w3_async.eth.send_raw_transaction(signed_txn.rawTransaction)
        
        print(f"钱包 {wallet['index']} 交易已发送: {tx_hash.hex()}")
        
        # 等待交易确认
        receipt = await w3_async.eth.wait_for_transaction_receipt(tx_hash)
        
        if receipt['status'] == 1:
            print(f"钱包 {wallet['index']} 交易成功! Gas used: {receipt['gasUsed']}")
            return True, receipt
        else:
            print(f"钱包 {wallet['index']} 交易失败!")
            return False, receipt
            
    except Exception as e:
        print(f"钱包 {wallet['index']} 交易错误: {str(e)}")
        return False, str(e)

async def main():
    try:
        # 加载 Router 合约 ABI
        with open('abis/pancake_v2.json', 'r') as f:
            ROUTER_ABI = json.load(f)
        
        # 创建合约实例
        router_contract = w3_async.eth.contract(
            address=w3.to_checksum_address(PANCAKE_ROUTER),
            abi=ROUTER_ABI
        )
        
        # 加载钱包列表
        wallets = load_wallets('wallets/wallets_20241201_044109.json')
        print(f"已加载 {len(wallets)} 个钱包")
        
        # 查询价格
        print("\n查询代币价格...")
        success, price_result = await get_token_price(router_contract)
        
        if not success:
            print(f"获取价格失败: {price_result}")
            return
            
        amount_out_min = int(price_result * 0.95)  # 设置 5% 滑点
        print(f"0.01 BNB 可以换取: {w3.from_wei(price_result, 'ether')} 代币")
        
        # 询问是否开始测试交易
        response = input("\n是否开始测试交易（使用第一个钱包）? (y/n): ")
        if response.lower() != 'y':
            print("交易已取消")
            return
        
        # 先测试第一个钱包
        print("\n开始测试交易...")
        test_result = await execute_swap(wallets[0], router_contract, amount_out_min)
        
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
        remaining_wallets = wallets[1:]  # 跳过第一个钱包
        tasks = [
            execute_swap(wallet, router_contract, amount_out_min)
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