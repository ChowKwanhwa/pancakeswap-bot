import os
import json
import requests
from pathlib import Path
from web3 import Web3

def get_contract_abi(contract_address: str, api_key: str) -> dict:
    """
    从BSCScan获取合约ABI
    """
    url = "https://api.bscscan.com/api"
    params = {
        "module": "contract",
        "action": "getabi",
        "address": contract_address,
        "apikey": api_key
    }
    
    response = requests.get(url, params=params)
    result = response.json()
    
    if result["status"] == "1" and result["message"] == "OK":
        return json.loads(result["result"])
    else:
        raise Exception(f"获取ABI失败: {result['message']}")

def save_abi_to_file(contract_name: str, abi: dict, folder: str = "abis"):
    """
    将ABI保存到文件，使用合约名称命名
    """
    # 创建文件夹（如果不存在）
    Path(folder).mkdir(parents=True, exist_ok=True)
    
    # 生成文件名
    filename = os.path.join(folder, f"{contract_name.lower()}.json")
    
    # 保存ABI到文件
    with open(filename, 'w') as f:
        json.dump(abi, f, indent=2)
    
    print(f"ABI已保存到: {filename}")

def get_pair_address():
    """
    获取 COCO-BUSD 交易对地址
    """
    # 连接到 BSC
    w3 = Web3(Web3.HTTPProvider("https://bsc-dataseed.binance.org/"))
    
    # 加载 Factory ABI
    with open('abis/pancake_factory.json', 'r') as f:
        factory_abi = json.load(f)
    
    # Factory 合约地址
    factory_address = w3.to_checksum_address("0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73")
    
    # COCO 和 BUSD 地址
    coco_address = w3.to_checksum_address(os.getenv("COCO_TOKEN_ADDRESS"))
    busd_address = w3.to_checksum_address("0x55d398326f99059ff775485246999027b3197955")  # BUSD
    
    # 创建 Factory 合约实例
    factory_contract = w3.eth.contract(address=factory_address, abi=factory_abi)
    
    # 获取交易对地址
    pair_address = factory_contract.functions.getPair(coco_address, busd_address).call()
    return pair_address

def main():
    # 从.env文件读取API key
    from dotenv import load_dotenv
    load_dotenv()
    
    # 获取BSC API key
    bsc_api_key = os.getenv("BSC_SCAN_API_KEY")
    if not bsc_api_key:
        raise Exception("未找到 BSC_SCAN_API_KEY")
    
    # 使用合约名称和地址的映射
    contracts = {
        "PANCAKE_UNIVERSAL_ROUTER": os.getenv("PANCAKE_UNIVERSAL_ROUTER"),
        "WBNB": os.getenv("WBNB_ADDRESS"),
        "COCO_TOKEN": os.getenv("COCO_TOKEN_ADDRESS"),
        "PANCAKE_FACTORY": os.getenv("PANCAKE_FACTORY_ADDRESS"),
        "PANCAKE_V2": '0x10ed43c718714eb63d5aa57b78b54704e256024e'
    }
    
    # 获取并保存每个合约的ABI
    for contract_name, address in contracts.items():
        if address:
            try:
                print(f"\n正在获取合约 {contract_name} ({address}) 的ABI...")
                abi = get_contract_abi(address, bsc_api_key)
                save_abi_to_file(contract_name, abi)
                print(f"成功获取并保存合约 {contract_name} 的ABI")
            except Exception as e:
                print(f"处理合约 {contract_name} 时出错: {str(e)}")
    
    # 获取并保存 Pair ABI
    try:
        pair_address = get_pair_address()
        print(f"\n正在获取 COCO-BUSD Pair 合约 ({pair_address}) 的ABI...")
        pair_abi = get_contract_abi(pair_address, bsc_api_key)
        save_abi_to_file("pancake_pair", pair_abi)
        print(f"成功获取并保存 Pair 合约的ABI")
    except Exception as e:
        print(f"处理 Pair 合约时出错: {str(e)}")

if __name__ == "__main__":
    main()