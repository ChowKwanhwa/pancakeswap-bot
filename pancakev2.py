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
PANCAKE_ROUTER = "0x10ED43C718714eb63d5aA57B78B54704E256024E"
WBNB = "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c"
TOKEN = "0xF3c7CECF8cBC3066F9a87b310cEBE198d00479aC"

def get_token_price():
    """
    获取代币价格
    """
    # 加载 Router 合约 ABI
    with open('abis/pancake_v2.json', 'r') as f:
        ROUTER_ABI = json.load(f)
    
    router = w3.eth.contract(
        address=w3.to_checksum_address(PANCAKE_ROUTER),
        abi=ROUTER_ABI
    )
    
    # 查询 0.01 BNB 能换多少代币
    amount_in = w3.to_wei(0.01, 'ether')
    path = [WBNB, TOKEN]
    
    try:
        amounts_out = router.functions.getAmountsOut(
            amount_in,
            path
        ).call()
        
        print(f"0.01 BNB 可以换取: {w3.from_wei(amounts_out[1], 'ether')} 代币")
        return amounts_out[1]
    except Exception as e:
        print(f"获取价格失败: {str(e)}")
        return None

def buy_token():
    """
    购买代币
    """
    account = w3.eth.account.from_key(os.getenv("PRIVATE_KEY"))
    
    # 加载 Router 合约 ABI
    with open('abis/pancake_v2.json', 'r') as f:
        ROUTER_ABI = json.load(f)
    
    router = w3.eth.contract(
        address=w3.to_checksum_address(PANCAKE_ROUTER),
        abi=ROUTER_ABI
    )
    
    # 设置交易参数
    amount_in = w3.to_wei(0.01, 'ether')  # 0.01 BNB
    path = [WBNB, TOKEN]
    deadline = int((datetime.now() + timedelta(minutes=20)).timestamp())
    
    # 获取预期输出数量
    amounts_out = router.functions.getAmountsOut(amount_in, path).call()
    amount_out_min = int(amounts_out[1] * 0.95)  # 设置 5% 滑点
    
    # 构建交易
    transaction = router.functions.swapExactETHForTokensSupportingFeeOnTransferTokens(
        amount_out_min,  # 最小获得的代币数量
        path,           # 交易路径
        account.address,  # 接收地址
        deadline        # 截止时间
    ).build_transaction({
        'from': account.address,
        'value': amount_in,  # 发送的 BNB 数量
        'gas': 300000,
        'gasPrice': w3.eth.gas_price,
        'nonce': w3.eth.get_transaction_count(account.address),
    })
    
    # 签名交易
    signed_txn = w3.eth.account.sign_transaction(
        transaction,
        private_key=os.getenv("PRIVATE_KEY")
    )
    
    # 发送交易
    tx_hash = w3.eth.send_raw_transaction(signed_txn.raw_transaction)
    print(f"交易已发送! 交易哈希: {tx_hash.hex()}")
    
    # 等待交易确认
    print("等待交易确认...")
    tx_receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    if tx_receipt['status'] == 1:
        print(f"交易成功! Gas used: {tx_receipt['gasUsed']}")
    else:
        print("交易失败!")
    
    return tx_receipt

def main():
    try:
        # 首先查询价格
        print("查询代币价格...")
        expected_amount = get_token_price()
        
        if expected_amount is None:
            print("无法获取价格，终止交易")
            return
        
        # 询问是否继续交易
        response = input("是否继续交易? (y/n): ")
        if response.lower() != 'y':
            print("交易已取消")
            return
        
        # 执行购买
        print("执行购买交易...")
        receipt = buy_token()
        
    except Exception as e:
        print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    main()