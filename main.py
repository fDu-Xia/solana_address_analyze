from fontTools.merge.util import current_time
from solana.rpc.api import Client
import time
from solders.pubkey import Pubkey
import networkx as nx
import matplotlib.pyplot as plt



def is_token_transfer(tx_data) -> bool:
    try:
        # 获取 logMessages
        log_messages = tx_data.value.transaction.meta.log_messages

        # 检查是否存在目标消息
        result = 'Program TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA invoke [1]' in log_messages
        return result

    except (KeyError, TypeError):
        return False

def is_sol_transfer(tx_data) -> int:
    try:
        # 获取 logMessages
        log_messages = tx_data.value.transaction.meta.log_messages

        # 计算目标消息出现的次数
        count = log_messages.count('Program 11111111111111111111111111111111 invoke [1]')
        return count

    except (KeyError, TypeError):
        return 0



def get_token_receiver(address:str, tx_data, target_mint: str):
    try:
        # 获取 pre 和 post token balances
        post_token_balances = tx_data.value.transaction.meta.post_token_balances

        receiver = []
        addressPub = Pubkey.from_string(address)
        mintPub = Pubkey.from_string(target_mint)
        # 检查 postTokenBalances
        for balance in post_token_balances:
            if balance.mint == mintPub and balance.owner != addressPub:
                receiver.append(str(balance.owner))
        return receiver

    except (KeyError, TypeError):
        return []

def get_sol_receiver(address:str,tx_data,receiver_counts:int):
    try:
        account_keys = tx_data.value.transaction.transaction.message.account_keys
        index = account_keys.index(address)
        end_index = index + 1 + receiver_counts
        return account_keys[index + 1:end_index]
    except (KeyError, TypeError,ValueError):
        return []

class SolanaTransferAnalyzer:
    def __init__(self, rpc_url="https://mainnet.helius-rpc.com/?api-key=28559d54-a5d0-483f-8154-d5c29989db7f"):
        self.client = Client(rpc_url)
        self.graph = nx.Graph()

    def construct_graph(self,addresses):
        for address in addresses:
            self.graph.add_node(address)

    def add_edge(self,node,neighbors):
        for neighbor in neighbors:
            self.graph.add_edge(node,neighbor)

    def print_all_connected_subgraph(self, max_node_count):
        for c in nx.connected_components(self.graph):
            nodeSet = self.graph.subgraph(c).nodes
            if len(nodeSet) <= max_node_count:
                print(nodeSet,end="\n")

    def get_graph_neighbour(self, address: str, mint_address: str,time_interval):
        current =  int(time.time())
        neighbors = []
        addressPub = Pubkey.from_string(address)
        before = None
        while True:
            try:
                # 获取账户的交易签名
                signatures = self.client.get_signatures_for_address(account=addressPub, limit=1000, before=before)

                if not signatures.value:
                    return neighbors
                before = signatures.value[-1].signature
                # 获取每个交易的详细信息
                for sig_info in signatures.value:
                    if current - sig_info.block_time > time_interval:
                        return neighbors
                    try:
                        # 获取交易详情
                        tx_data = self.client.get_transaction(
                            sig_info.signature,
                            encoding="jsonParsed",
                            max_supported_transaction_version=0
                        )
                        if mint_address == 'sol':
                            count = is_sol_transfer(tx_data)
                            if count > 0:
                                receivers = get_sol_receiver(address, tx_data, count)
                                neighbors.extend(receivers)
                        else:
                            if is_token_transfer(tx_data):
                                receivers = get_token_receiver(address, tx_data, mint_address)
                                neighbors.extend(receivers)

                        # 添加延时以避免请求过快
                        time.sleep(0.1)

                    except Exception as e:
                        print(f"Error processing transaction {sig_info.signature}: {str(e)}")
                        continue
            except Exception as e:
                print(f"Error occurred: {str(e)}")


def main():
    # 初始化
    analyzer = SolanaTransferAnalyzer()
    #如果是sol
    #token_mint = "sol"

    #ava为例
    token_mint = "DKu9kykSfbN5LBfFXtNNDPaX35o4Fv6vJ9FKk7pZpump"
    wallet1 = "8SJR9CNrANJvgWVND9ZPNHK6va6VCC3p7NBSx8c3hotM"
    wallet2 = "w6AovkEzgdQYt6yJDN7atHMkRQv877FpXWvRKouv6Gc"
    wallet3 = "DnzPxMvaYutWV9ULiErSXMTvqcJ1gkN1qvHN4bqGLovB"

    wallets = [wallet1,wallet2,wallet3]

    analyzer.construct_graph(wallets)

    #只看七天内的交易
    seven_days_in_seconds = 604800

    for wallet in wallets:
        neighbors = analyzer.get_graph_neighbour(wallet, token_mint,seven_days_in_seconds)
        analyzer.add_edge(wallet,neighbors)

    #打印结果：只打印节点数量小于3的集群
    analyzer.print_all_connected_subgraph(3)


if __name__ == "__main__":
    main()