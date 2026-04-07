"""
动态规划 (Dynamic Programming) 示例
"""


# ============ 1. 斐波那契数列 ============
def fib_recursive(n: int) -> int:
    """递归版 - O(2^n)"""
    if n <= 1:
        return n
    return fib_recursive(n - 1) + fib_recursive(n - 2)


def fib_dp(n: int) -> int:
    """动态规划版 - O(n)"""
    if n <= 1:
        return n
    dp = [0] * (n + 1)
    dp[1] = 1
    for i in range(2, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]


def fib_optimized(n: int) -> int:
    """空间优化版 - O(n), O(1)"""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


# ============ 2. 爬楼梯 ============
def climb_stairs(n: int) -> int:
    """爬楼梯，每次1或2步，多少人有多少种方法"""
    if n <= 2:
        return n
    dp = [0] * (n + 1)
    dp[1], dp[2] = 1, 2
    for i in range(3, n + 1):
        dp[i] = dp[i - 1] + dp[i - 2]
    return dp[n]


# ============ 3. 背包问题 ============
def knapSack(capacity: int, weights: list, values: list, n: int) -> int:
    """0-1背包问题 - 返回最大价值"""
    dp = [[0] * (capacity + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        for w in range(capacity + 1):
            if weights[i - 1] <= w:
                dp[i][w] = max(dp[i - 1][w], dp[i - 1][w - weights[i - 1]] + values[i - 1])
            else:
                dp[i][w] = dp[i - 1][w]

    return dp[n][capacity]


def knapSack_optimized(capacity: int, weights: list, values: list) -> int:
    """空间优化版"""
    dp = [0] * (capacity + 1)

    for i in range(len(weights)):
        for w in range(capacity, weights[i] - 1, -1):
            dp[w] = max(dp[w], dp[w - weights[i]] + values[i])

    return dp[capacity]


# ============ 4. 最长公共子序列 ============
def lcs(s1: str, s2: str) -> int:
    """最长公共子序列长度"""
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])

    return dp[m][n]


# ============ 5. 最长递增子序列 ============
def lis(nums: list[int]) -> int:
    """最长递增子序列 - O(n²)"""
    if not nums:
        return 0
    n = len(nums)
    dp = [1] * n

    for i in range(1, n):
        for j in range(i):
            if nums[j] < nums[i]:
                dp[i] = max(dp[i], dp[j] + 1)

    return max(dp)


def lis_optimized(nums: list[int]) -> int:
    """二分优化版 - O(n log n)"""
    import bisect

    tails = []
    for num in nums:
        pos = bisect.bisect_left(tails, num)
        if pos == len(tails):
            tails.append(num)
        else:
            tails[pos] = num
    return len(tails)


# ============ 6. 编辑距离 ============
def min_distance(word1: str, word2: str) -> int:
    """将word1转换为word2的最少操作数"""
    m, n = len(word1), len(word2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]

    # 初始化
    for i in range(m + 1):
        dp[i][0] = i
    for j in range(n + 1):
        dp[0][j] = j

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if word1[i - 1] == word2[j - 1]:
                dp[i][j] = dp[i - 1][j - 1]
            else:
                dp[i][j] = min(
                    dp[i - 1][j],  # 删除
                    dp[i][j - 1],  # 插入
                    dp[i - 1][j - 1]  # 替换
                ) + 1

    return dp[m][n]


# ============ 7. 买卖股票最佳时机 ============
def max_profit(prices: list[int]) -> int:
    """一次交易最大利润"""
    if not prices:
        return 0

    min_price = prices[0]
    max_profit = 0

    for price in prices[1:]:
        max_profit = max(max_profit, price - min_price)
        min_price = min(min_price, price)

    return max_profit


def max_profit_k(prices: list[int], k: int) -> int:
    """最多k次交易的最大利润"""
    n = len(prices)
    if n == 0 or k == 0:
        return 0

    # 贪心：利润为正就交易
    if k >= n // 2:
        profit = 0
        for i in range(1, n):
            if prices[i] > prices[i - 1]:
                profit += prices[i] - prices[i - 1]
        return profit

    dp = [[[0, 0] for _ in range(k + 1)] for _ in range(n)]
    # dp[i][j][0] = 第i天完成j次交易且持有股票的最大利润
    # dp[i][j][1] = 第i天完成j次交易且不持有股票的最大利润

    for j in range(k + 1):
        dp[0][j][1] = -prices[0]

    for i in range(1, n):
        for j in range(k + 1):
            if j > 0:
                dp[i][j][0] = max(dp[i - 1][j][0], dp[i - 1][j - 1][1] + prices[i])
            dp[i][j][1] = max(dp[i - 1][j][1], dp[i - 1][j][0] - prices[i])

    return dp[n - 1][k][1]


# ============ 8. 打家劫舍 ============
def rob(nums: list[int]) -> int:
    """不能偷连续两 houses 的最大金额"""
    if not nums:
        return 0
    if len(nums) == 1:
        return nums[0]

    prev2, prev1 = nums[0], max(nums[0], nums[1])

    for i in range(2, len(nums)):
        curr = max(prev1, prev2 + nums[i])
        prev2, prev1 = prev1, curr

    return prev1


def rob_circle(nums: list[int]) -> int:
    """环形街道版本"""
    if not nums:
        return 0
    if len(nums) == 1:
        return nums[0]

    # 不偷第一间或最后一间
    return max(rob_simple(nums[:-1]), rob_simple(nums[1:]))


def rob_simple(nums: list[int]) -> int:
    """打家劫舍基础版"""
    prev2, prev1 = 0, 0
    for num in nums:
        curr = max(prev1, prev2 + num)
        prev2, prev1 = prev1, curr
    return prev1


# ============ 9. 单词拆分 ============
def word_break(s: str, word_dict: list[str]) -> bool:
    """判断能否用字典中的词拆分"""
    word_set = set(word_dict)
    n = len(s)
    dp = [False] * (n + 1)
    dp[0] = True

    for i in range(1, n + 1):
        for j in range(i):
            if dp[j] and s[j:i] in word_set:
                dp[i] = True
                break

    return dp[n]


# ============ 10. 凑零钱 ============
def coin_change(coins: list[int], amount: int) -> int:
    """最少硬币数量凑成 amount"""
    dp = [float('inf')] * (amount + 1)
    dp[0] = 0

    for coin in coins:
        for i in range(coin, amount + 1):
            dp[i] = min(dp[i], dp[i - coin] + 1)

    return dp[amount] if dp[amount] != float('inf') else -1


if __name__ == "__main__":
    print("=== 动态规划示例 ===")

    # 斐波那契
    print("\n1. 斐波那契数列:")
    n = 20
    print(f"  F({n}) = {fib_dp(n)} (DP版)")
    print(f"  F({n}) = {fib_optimized(n)} (空间优化版)")

    # 爬楼梯
    print("\n2. 爬楼梯:")
    print(f"  5步楼梯的方法数: {climb_stairs(5)}")

    # 背包问题
    print("\n3. 背包问题:")
    capacity = 10
    weights = [2, 3, 5, 7]
    values = [2, 4, 6, 9]
    print(f"  容量={capacity}, 物品(重量,价值)={list(zip(weights, values))}")
    print(f"  最大价值: {knapSack_optimized(capacity, weights, values)}")

    # LCS
    print("\n4. 最长公共子序列:")
    s1, s2 = "abcbdab", "bdcaba"
    print(f"  '{s1}' 和 '{s2}' 的LCS长度: {lcs(s1, s2)}")

    # LIS
    print("\n5. 最长递增子序列:")
    nums = [10, 9, 2, 5, 3, 7, 101, 18]
    print(f"  {nums} 的LIS长度: {lis(nums)}")
    print(f"  二分优化版: {lis_optimized(nums)}")

    # 编辑距离
    print("\n6. 编辑距离:")
    word1, word2 = "horse", "ros"
    print(f"  '{word1}' -> '{word2}': {min_distance(word1, word2)}")

    # 买卖股票
    print("\n7. 买卖股票:")
    prices = [7, 1, 5, 3, 6, 4]
    print(f"  价格: {prices}, 最大利润(一次): {max_profit(prices)}")

    # 打家劫舍
    print("\n8. 打家劫舍:")
    nums = [2, 7, 9, 3, 1]
    print(f"  金额: {nums}, 最大盗窃: {rob(nums)}")

    # 单词拆分
    print("\n9. 单词拆分:")
    s = "leetcode"
    word_dict = ["leet", "code"]
    print(f"  '{s}' 可以拆分: {word_break(s, word_dict)}")

    # 凑零钱
    print("\n10. 凑零钱:")
    coins = [1, 2, 5]
    amount = 11
    print(f"  硬币{coins}凑{amount}元，最少: {coin_change(coins, amount)}枚")