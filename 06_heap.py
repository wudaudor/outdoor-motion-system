"""
堆 (Heap) 的应用示例
"""

import heapq
from typing import List


# ============ 1. Top K 问题 ============
def top_k(nums: list[int], k: int) -> list[int]:
    """找出前k大的数"""
    # 小顶堆，保留k个最大元素
    return heapq.nlargest(k, nums)


def top_k_heap(nums: list[int], k: int) -> list[int]:
    """用堆找出前k大的数（适用于大数据流）"""
    heap = []
    for num in nums:
        heapq.heappush(heap, num)
        if len(heap) > k:
            heapq.heappop(heap)  # 弹出最小的

    return sorted(heap, reverse=True)


# ============ 2. 合并有序文件 ============
def merge_k_sorted_lists(lists: List[List[int]]) -> List[int]:
    """合并k个有序数组"""
    heap = []

    # 初始化堆，每个元素为 (值, 列表索引, 元素索引)
    for i, lst in enumerate(lists):
        if lst:
            heapq.heappush(heap, (lst[0], i, 0))

    result = []
    while heap:
        val, list_idx, elem_idx = heapq.heappop(heap)
        result.append(val)

        # 推送该列表的下一个元素
        if elem_idx + 1 < len(lists[list_idx]):
            next_val = lists[list_idx][elem_idx + 1]
            heapq.heappush(heap, (next_val, list_idx, elem_idx + 1))

    return result


# ============ 3. 数据流中位数 ============
class MedianFinder:
    """
    动态数据流中位数
    使用大顶堆存较小一半，小顶堆存较大一半
    """

    def __init__(self):
        self.small = []  # 大顶堆（存较小的一半，负数实现）
        self.large = []  # 小顶堆（存较大的一半）

    def add_num(self, num: int):
        """添加数字"""
        # 默认加入小顶堆
        heapq.heappush(self.small, -num)

        # 平衡两个堆
        if self.small and self.large and -self.small[0] > self.large[0]:
            val = -heapq.heappop(self.small)
            heapq.heappush(self.large, val)

        # 确保 small 元素数 >= large 元素数
        if len(self.small) < len(self.large):
            val = heapq.heappop(self.large)
            heapq.heappush(self.small, -val)

    def find_median(self) -> float:
        """获取中位数"""
        if len(self.small) > len(self.large):
            return -self.small[0]
        return (-self.small[0] + self.large[0]) / 2


# ============ 4. 丑数 ============
def nth_ugly_number(n: int) -> int:
    """
    丑数：只包含质因数 2, 3, 5 的数
    返回第 n 个丑数
    """
    ugly = [1]
    i2 = i3 = i5 = 0

    for _ in range(n - 1):
        next2, next3, next5 = ugly[i2] * 2, ugly[i3] * 3, ugly[i5] * 5
        next_ugly = min(next2, next3, next5)
        ugly.append(next_ugly)

        if next_ugly == next2:
            i2 += 1
        if next_ugly == next3:
            i3 += 1
        if next_ugly == next5:
            i5 += 1

    return ugly[-1]


# ============ 5. 哈夫曼编码（最小堆实现） ============
import heapq
from collections import Counter


class HuffmanNode:
    def __init__(self, char, freq):
        self.char = char
        self.freq = freq
        self.left = None
        self.right = None

    def __lt__(self, other):
        return self.freq < other.freq


def huffman_coding(text: str) -> tuple:
    """哈夫曼编码"""
    freq = Counter(text)
    heap = [HuffmanNode(char, f) for char, f in freq.items()]
    heapq.heapify(heap)

    while len(heap) > 1:
        left = heapq.heappop(heap)
        right = heapq.heappop(heap)

        merged = HuffmanNode(None, left.freq + right.freq)
        merged.left = left
        merged.right = right

        heapq.heappush(heap, merged)

    root = heap[0]
    codes = {}

    def generate_codes(node, code=""):
        if node.char:
            codes[node.char] = code
        else:
            if node.left:
                generate_codes(node.left, code + "0")
            if node.right:
                generate_codes(node.right, code + "1")

    generate_codes(root)

    encoded = ''.join(codes[c] for c in text)

    return codes, encoded


# ============ 6. 堆排序 ============
def heap_sort(arr: list[int]) -> list[int]:
    """堆排序"""
    heap = arr.copy()
    heapq.heapify(heap)
    return [heapq.heappop(heap) for _ in range(len(heap))]


if __name__ == "__main__":
    print("=== 堆的应用 ===")

    # Top K
    print("\n1. Top K 问题:")
    nums = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5]
    k = 3
    print(f"  数组: {nums}, k={k}")
    print(f"  前{k}大的数: {top_k(nums, k)}")
    print(f"  堆方法: {top_k_heap(nums, k)}")

    # 合并有序列表
    print("\n2. 合并k个有序列表:")
    lists = [[1, 4, 7], [2, 5, 8], [3, 6, 9]]
    print(f"  输入: {lists}")
    print(f"  合并结果: {merge_k_sorted_lists(lists)}")

    # 数据流中位数
    print("\n3. 数据流中位数:")
    mf = MedianFinder()
    for num in [2, 3, 4, 7, 5]:
        mf.add_num(num)
        print(f"  添加 {num} 后，中位数 = {mf.find_median()}")

    # 丑数
    print("\n4. 丑数:")
    for i in [1, 5, 10]:
        print(f"  第{i}个丑数: {nth_ugly_number(i)}")

    # 哈夫曼编码
    print("\n5. 哈夫曼编码:")
    text = "hello world"
    codes, encoded = huffman_coding(text)
    print(f"  原文: '{text}'")
    print(f"  编码表: {codes}")
    print(f"  编码结果: {encoded}")
    print(f"  压缩率: {len(encoded)}/{len(text) * 8} bits = {len(encoded)/(len(text)*8):.2%}")

    # 堆排序
    print("\n6. 堆排序:")
    arr = [64, 34, 25, 12, 22, 11, 90]
    print(f"  输入: {arr}")
    print(f"  排序: {heap_sort(arr)}")