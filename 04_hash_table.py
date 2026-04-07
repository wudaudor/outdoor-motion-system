"""
哈希表 (Hash Table / Dict) 的应用示例
"""

from collections import defaultdict


# ============ 1. 两数之和 ============
def two_sum(nums: list[int], target: int) -> list[int]:
    """查找两数之和为目标值的两个索引"""
    seen = {}  # 值 -> 索引

    for i, num in enumerate(nums):
        complement = target - num
        if complement in seen:
            return [seen[complement], i]
        seen[num] = i

    return []


# ============ 2. 字母异位词分组 ============
def group_anagrams(strs: list[str]) -> list[list[str]]:
    """将字母异位词分组"""
    anagrams = defaultdict(list)

    for s in strs:
        key = ''.join(sorted(s))
        anagrams[key].append(s)

    return list(anagrams.values())


# ============ 3. 最长连续序列 ============
def longest_consecutive(nums: list[int]) -> int:
    """找出最长连续序列的长度"""
    num_set = set(nums)
    longest = 0

    for num in num_set:
        # 只有是序列起点才检查
        if num - 1 not in num_set:
            current = num
            streak = 1

            while current + 1 in num_set:
                current += 1
                streak += 1

            longest = max(longest, streak)

    return longest


# ============ 4. 词频率统计 ============
def word_frequency(text: str) -> dict:
    """统计单词频率"""
    words = text.lower().split()
    freq = defaultdict(int)

    for word in words:
        # 移除标点
        clean_word = ''.join(c for c in word if c.isalnum())
        if clean_word:
            freq[clean_word] += 1

    return dict(freq)


# ============ 5. 查找第一个不重复的字符 ============
def first_unique(s: str) -> str:
    """查找第一个不重复的字符"""
    char_count = defaultdict(int)

    for c in s:
        char_count[c] += 1

    for c in s:
        if char_count[c] == 1:
            return c

    return ""


# ============ 6. 两数组交集 ============
def intersection(nums1: list[int], nums2: list[int]) -> list[int]:
    """返回两数组的交集（去重）"""
    set1 = set(nums1)
    set2 = set(nums2)
    return list(set1 & set2)


# ============ 7. 滑动窗口问题（最小覆盖子串） ============
def min_window(s: str, t: str) -> str:
    """在S中找到包含T所有字符的最小子串"""
    if not s or not t:
        return ""

    # 统计t中字符需求
    need = defaultdict(int)
    for c in t:
        need[c] += 1

    window = defaultdict(int)
    left = 0
    valid = 0
    min_len = float('inf')
    min_start = 0

    for right in range(len(s)):
        c = s[right]
        if c in need:
            window[c] += 1
            if window[c] == need[c]:
                valid += 1

        # 收缩窗口
        while valid == len(need):
            if right - left + 1 < min_len:
                min_len = right - left + 1
                min_start = left

            d = s[left]
            if d in need:
                if window[d] == need[d]:
                    valid -= 1
                window[d] -= 1
            left += 1

    return s[min_start:min_start + min_len] if min_len != float('inf') else ""


if __name__ == "__main__":
    print("=== 哈希表的应用 ===")

    # 两数之和
    print("\n1. 两数之和:")
    nums = [2, 7, 11, 15]
    print(f"  nums={nums}, target=9 -> {two_sum(nums, 9)}")  # [0,1]

    # 字母异位词
    print("\n2. 字母异位词分组:")
    strs = ["eat", "tea", "tan", "ate", "nat", "bat"]
    groups = group_anagrams(strs)
    print(f"  {strs}")
    print(f"  分组结果: {groups}")

    # 最长连续序列
    print("\n3. 最长连续序列:")
    nums = [100, 4, 200, 3, 2, 101]
    print(f"  nums={nums} -> 最长连续序列长度: {longest_consecutive(nums)}")  # 4

    # 词频统计
    print("\n4. 词频统计:")
    text = "Python is great, Python is easy, Python is popular!"
    freq = word_frequency(text)
    print(f"  文本: {text}")
    print(f"  频率: {freq}")

    # 第一个不重复字符
    print("\n5. 第一个不重复字符:")
    s = "abracadabra"
    print(f"  '{s}' -> '{first_unique(s)}'")  # 'c'

    # 数组交集
    print("\n6. 两数组交集:")
    nums1, nums2 = [1, 2, 2, 1], [2, 2]
    print(f"  {nums1} ∩ {nums2} = {intersection(nums1, nums2)}")

    # 最小覆盖子串
    print("\n7. 最小覆盖子串:")
    s, t = "ADOBECODEBANC", "ABC"
    result = min_window(s, t)
    print(f"  S='{s}', T='{t}' -> '{result}'")  # 'BANC'