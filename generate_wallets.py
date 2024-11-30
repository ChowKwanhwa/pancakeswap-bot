from eth_account import Account
import secrets
import json
import csv
import os
from datetime import datetime

def generate_wallets(n: int):
    """
    生成 n 个钱包地址和私钥
    """
    wallets = []
    
    for i in range(n):
        # 生成一个随机的私钥
        priv = secrets.token_hex(32)
        private_key = "0x" + priv
        
        # 从私钥创建账户
        account = Account.from_key(private_key)
        
        wallet = {
            "address": account.address,
            "private_key": private_key,
            "index": i + 1
        }
        wallets.append(wallet)
        
        # 打印进度
        print(f"已生成第 {i + 1} 个钱包")
    
    return wallets

def save_wallets(wallets: list):
    """
    保存钱包信息到文件
    """
    # 创建 wallets 文件夹（如果不存在）
    if not os.path.exists("wallets"):
        os.makedirs("wallets")
    
    # 生成文件名（包含时间戳）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # 保存为 JSON 文件
    json_file = f"wallets/wallets_{timestamp}.json"
    with open(json_file, "w") as f:
        json.dump(wallets, f, indent=4)
    
    # 保存为 CSV 文件
    csv_file = f"wallets/wallets_{timestamp}.csv"
    with open(csv_file, "w", newline='') as f:
        writer = csv.writer(f)
        # 写入表头
        writer.writerow(["Index", "Address", "Private Key"])
        # 写入数据
        for wallet in wallets:
            writer.writerow([
                wallet["index"],
                wallet["address"],
                wallet["private_key"]
            ])
    
    return json_file, csv_file

def main():
    try:
        # 获取用户输入
        n = int(input("请输入要生成的钱包数量: "))
        
        if n <= 0:
            print("错误: 数量必须大于 0")
            return
        
        print(f"\n开始生成 {n} 个钱包...")
        wallets = generate_wallets(n)
        
        print("\n保存钱包信息...")
        json_file, csv_file = save_wallets(wallets)
        
        print("\n完成！")
        print(f"JSON 文件已保存到: {json_file}")
        print(f"CSV 文件已保存到: {csv_file}")
        print("请务必安全保管私钥！")
        
    except ValueError:
        print("错误: 请输入有效的数字")
    except Exception as e:
        print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    main() 