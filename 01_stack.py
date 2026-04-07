"""
栈 (Stack) 的应用示例
"""

# ============ 1. 括号匹配验证 ============
def is_valid_brackets(s: str) -> bool:
    """验证括号字符串是否合法"""
    stack = []
    brackets_map = {')': '(', ']': '[', '}': '{'}

    for char in s:
        if char in '([{':
            stack.append(char)
        elif char in ')]}':
            if not stack or stack[-1] != brackets_map[char]:
                return False
            stack.pop()

    return len(stack) == 0


# ============ 2. 表达式求值（后缀表达式） ============
def evaluate_postfix(expr: str) -> int:
    """计算后缀表达式（如 "3 4 + 2 *" -> 14）"""
    stack = []
    tokens = expr.split()

    for token in tokens:
        if token.isdigit():
            stack.append(int(token))
        else:
            b, a = stack.pop(), stack.pop()
            if token == '+':
                stack.append(a + b)
            elif token == '-':
                stack.append(a - b)
            elif token == '*':
                stack.append(a * b)
            elif token == '/':
                stack.append(int(a / b))

    return stack[0]


# ============ 3. 每日温度（单调栈） ============
def daily_temperatures(temps: list[int]) -> list[int]:
    """返回每个温度需要等多少天才能等到更高的温度"""
    n = len(temps)
    result = [0] * n
    stack = []  # 存索引

    for i, temp in enumerate(temps):
        while stack and temps[stack[-1]] < temp:
            prev_idx = stack.pop()
            result[prev_idx] = i - prev_idx
        stack.append(i)

    return result


if __name__ == "__main__":
    # 测试
    print("=== 栈的应用 ===")

    # 括号匹配
    print("\n1. 括号匹配:")
    test_cases = ["()", "()[]{}", "(]", "([)]", "{[]}"]
    for s in test_cases:
        print(f"  '{s}' -> {is_valid_brackets(s)}")

    # 后缀表达式
    print("\n2. 后缀表达式求值:")
    print(f"  '3 4 + 2 *' = {evaluate_postfix('3 4 + 2 *')}")  # (3+4)*2 = 14
    print(f"  '5 3 - 2 *' = {evaluate_postfix('5 3 - 2 *')}")  # (5-3)*2 = 4

    # 每日温度
    print("\n3. 每日温度:")
    temps = [73, 74, 75, 71, 69, 72, 76, 73]
    result = daily_temperatures(temps)
    print(f"  输入: {temps}")
    print(f"  输出: {result}")  # [1, 1, 4, 2, 1, 1, 0, 0]