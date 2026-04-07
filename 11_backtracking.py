"""
回溯算法 (Backtracking) 示例
"""


# ============ 1. 全排列 ============
def permute(nums: list[int]) -> list[list[int]]:
    """全排列"""
    result = []

    def backtrack(start):
        if start == len(nums):
            result.append(nums.copy())
            return

        for i in range(start, len(nums)):
            nums[start], nums[i] = nums[i], nums[start]
            backtrack(start + 1)
            nums[start], nums[i] = nums[i], nums[start]

    backtrack(0)
    return result


# ============ 2. 组合总和 ============
def combination_sum(candidates: list[int], target: int) -> list[list[int]]:
    """找出和为target的组合（元素可重复）"""
    result = []

    def backtrack(start, current, remaining):
        if remaining == 0:
            result.append(current.copy())
            return
        if remaining < 0:
            return

        for i in range(start, len(candidates)):
            current.append(candidates[i])
            backtrack(i, current, remaining - candidates[i])
            current.pop()

    backtrack(0, [], target)
    return result


# ============ 3. 子集 ============
def subsets(nums: list[int]) -> list[list[int]]:
    """生成所有子集"""
    result = []

    def backtrack(start, current):
        result.append(current.copy())
        for i in range(start, len(nums)):
            current.append(nums[i])
            backtrack(i + 1, current)
            current.pop()

    backtrack(0, [])
    return result


def subsets_with_dup(nums: list[int]) -> list[list[int]]:
    """有重复元素的子集"""
    nums.sort()
    result = []

    def backtrack(start, current):
        result.append(current.copy())
        for i in range(start, len(nums)):
            if i > start and nums[i] == nums[i - 1]:
                continue
            current.append(nums[i])
            backtrack(i + 1, current)
            current.pop()

    backtrack(0, [])
    return result


# ============ 4. N皇后 ============
def solve_n_queens(n: int) -> list[list[str]]:
    """N皇后问题"""
    result = []
    board = [['.' for _ in range(n)] for _ in range(n)]
    cols = set()
    diag1 = set()  # row + col
    diag2 = set()  # row - col

    def backtrack(row):
        if row == n:
            result.append([''.join(row) for row in board])
            return

        for col in range(n):
            d1, d2 = row + col, row - col
            if col in cols or d1 in diag1 or d2 in diag2:
                continue

            board[row][col] = 'Q'
            cols.add(col)
            diag1.add(d1)
            diag2.add(d2)

            backtrack(row + 1)

            board[row][col] = '.'
            cols.remove(col)
            diag1.remove(d1)
            diag2.remove(d2)

    backtrack(0)
    return result


# ============ 5. 括号生成 ============
def generate_parenthesis(n: int) -> list[str]:
    """生成n对括号的所有有效组合"""
    result = []

    def backtrack(current, left, right):
        if len(current) == 2 * n:
            result.append(current)
            return

        if left < n:
            backtrack(current + '(', left + 1, right)
        if right < left:
            backtrack(current + ')', left, right + 1)

    backtrack('', 0, 0)
    return result


# ============ 6. 单词搜索 ============
def exist(board: list[list[str]], word: str) -> bool:
    """在棋盘中查找单词（相邻单元格）"""
    if not board:
        return False

    rows, cols = len(board), len(board[0])

    def backtrack(r, c, index):
        if index == len(word):
            return True
        if r < 0 or c < 0 or r >= rows or c >= cols or board[r][c] != word[index]:
            return False

        board[r][c] = '#'  # 标记已访问
        found = (backtrack(r + 1, c, index + 1) or
                 backtrack(r - 1, c, index + 1) or
                 backtrack(r, c + 1, index + 1) or
                 backtrack(r, c - 1, index + 1))
        board[r][c] = word[index]  # 恢复

        return found

    for r in range(rows):
        for c in range(cols):
            if backtrack(r, c, 0):
                return True

    return False


# ============ 7. 电话号码的字母组合 ============
def letter_combinations(digits: str) -> list[str]:
    """电话号码的字母组合"""
    phone = {
        '2': 'abc', '3': 'def', '4': 'ghi', '5': 'jkl',
        '6': 'mno', '7': 'pqrs', '8': 'tuv', '9': 'wxyz'
    }

    result = []

    def backtrack(index, current):
        if index == len(digits):
            result.append(current)
            return

        for letter in phone[digits[index]]:
            backtrack(index + 1, current + letter)

    if digits:
        backtrack(0, '')
    return result


# ============ 8. 组合 ============
def combine(n: int, k: int) -> list[list[int]]:
    """生成 [1..n] 中所有 k 个数的组合"""
    result = []

    def backtrack(start, current):
        if len(current) == k:
            result.append(current.copy())
            return

        for i in range(start, n + 1):
            current.append(i)
            backtrack(i + 1, current)
            current.pop()

    backtrack(1, [])
    return result


# ============ 9. 全排列 II（有重复） ============
def permuteUnique(nums: list[int]) -> list[list[int]]:
    """有重复数字的全排列"""
    nums.sort()
    result = []
    used = [False] * len(nums)

    def backtrack(current):
        if len(current) == len(nums):
            result.append(current.copy())
            return

        for i in range(len(nums)):
            if used[i] or (i > 0 and nums[i] == nums[i - 1] and not used[i - 1]):
                continue

            used[i] = True
            current.append(nums[i])
            backtrack(current)
            current.pop()
            used[i] = False

    backtrack([])
    return result


# ============ 10. 求解数独 ============
def solve_sudoku(board: list[list[str]]) -> None:
    """求解数独"""
    def is_valid(board, row, col, num):
        # 检查行
        if num in board[row]:
            return False
        # 检查列
        if any(board[i][col] == num for i in range(9)):
            return False
        # 检查3x3方块
        start_row, start_col = 3 * (row // 3), 3 * (col // 3)
        for i in range(start_row, start_row + 3):
            for j in range(start_col, start_col + 3):
                if board[i][j] == num:
                    return False
        return True

    def backtrack(board):
        for i in range(9):
            for j in range(9):
                if board[i][j] == '.':
                    for num in '123456789':
                        if is_valid(board, i, j, num):
                            board[i][j] = num
                            if backtrack(board):
                                return True
                            board[i][j] = '.'
                    return False
        return True

    backtrack(board)


if __name__ == "__main__":
    print("=== 回溯算法示例 ===")

    # 全排列
    print("\n1. 全排列:")
    nums = [1, 2, 3]
    print(f"  {nums} 的全排列: {permute(nums)}")

    # 组合总和
    print("\n2. 组合总和:")
    candidates = [2, 3, 6, 7]
    target = 7
    print(f"  {candidates} 中和为{target}的组合: {combination_sum(candidates, target)}")

    # 子集
    print("\n3. 子集:")
    nums = [1, 2, 3]
    print(f"  {nums} 的所有子集: {subsets(nums)}")

    # N皇后
    print("\n4. N皇后 (n=4):")
    solutions = solve_n_queens(4)
    print(f"  解的数量: {len(solutions)}")
    for i, sol in enumerate(solutions[:2], 1):
        print(f"  解{i}:")
        for row in sol:
            print(f"    {row}")

    # 括号生成
    print("\n5. 括号生成:")
    n = 3
    print(f"  n={n} 的括号组合: {generate_parenthesis(n)}")

    # 单词搜索
    print("\n6. 单词搜索:")
    board = [
        ['A', 'B', 'C', 'E'],
        ['S', 'F', 'C', 'S'],
        ['A', 'D', 'E', 'E']
    ]
    words = ["ABCCED", "SEE", "ABCB"]
    for word in words:
        print(f"  '{word}' 在棋盘中: {exist(board, word)}")

    # 电话号码
    print("\n7. 电话号码字母组合:")
    digits = "23"
    print(f"  '{digits}' 的组合: {letter_combinations(digits)}")

    # 组合
    print("\n8. 组合:")
    n, k = 4, 2
    print(f"  [1..{n}] 中 {k} 个数的组合: {combine(n, k)}")

    # 全排列 II
    print("\n9. 全排列 II:")
    nums = [1, 1, 2]
    print(f"  {nums} 的全排列: {permuteUnique(nums)}")

    # 回溯算法复杂度
    print("\n10. 回溯算法复杂度分析:")
    print("  ┌─────────────────┬──────────────────┐")
    print("  │ 问题            │ 时间复杂度       │")
    print("  ├─────────────────┼──────────────────┤")
    print("  │ 全排列          │ O(n! × n)        │")
    print("  │ 子集            │ O(2^n × n)       │")
    print("  │ 组合总和        │ O(k × C(n,k))    │")
    print("  │ N皇后           │ O(n!)            │")
    print("  └─────────────────┴──────────────────┘")