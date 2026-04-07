"""
查找算法示例
"""


# ============ 1. 二分查找 ============
def binary_search(arr: list, target: int) -> int:
    """二分查找 - O(log n)，返回索引或-1"""
    left, right = 0, len(arr) - 1

    while left <= right:
        mid = (left + right) // 2

        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1

    return -1


def binary_search_left(arr: list, target: int) -> int:
    """查找左边界（第一个 >= target 的位置）"""
    left, right = 0, len(arr)

    while left < right:
        mid = (left + right) // 2
        if arr[mid] < target:
            left = mid + 1
        else:
            right = mid

    return left


def binary_search_right(arr: list, target: int) -> int:
    """查找右边界（最后一个 <= target 的位置）"""
    left, right = 0, len(arr)

    while left < right:
        mid = (left + right) // 2
        if arr[mid] <= target:
            left = mid + 1
        else:
            right = mid

    return left - 1


# ============ 2. 插值查找 ============
def interpolation_search(arr: list, target: int) -> int:
    """
    插值查找 - 适用于均匀分布的数据
    根据目标值估算位置
    """
    left, right = 0, len(arr) - 1

    while left <= right and target >= arr[left] and target <= arr[right]:
        if left == right:
            if arr[left] == target:
                return left
            return -1

        # 插值公式
        pos = left + int(
            ((target - arr[left]) * (right - left)) / (arr[right] - arr[left])
        )

        if arr[pos] == target:
            return pos
        elif arr[pos] < target:
            left = pos + 1
        else:
            right = pos - 1

    return -1


# ============ 3. 指数查找 ============
def exponential_search(arr: list, target: int) -> int:
    """
    指数查找 - 先确定范围，再二分
    适用于无界限搜索
    """
    if arr[0] == target:
        return 0

    bound = 1
    while bound < len(arr) and arr[bound] < target:
        bound *= 2

    return binary_search_in_range(arr, target, bound // 2, min(bound, len(arr) - 1))


def binary_search_in_range(arr: list, target: int, left: int, right: int) -> int:
    """在指定范围内二分查找"""
    while left <= right:
        mid = (left + right) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            left = mid + 1
        else:
            right = mid - 1
    return -1


# ============ 4. 搜索旋转排序数组 ============
def search_rotated(arr: list, target: int) -> int:
    """
    在旋转排序数组中查找（e.g., [4,5,6,7,0,1,2]）
    先找旋转点，再在正确半区二分
    """
    if not arr:
        return -1

    # 找最小元素（旋转点）
    left, right = 0, len(arr) - 1
    while left < right:
        mid = (left + right) // 2
        if arr[mid] > arr[right]:
            left = mid + 1
        else:
            right = mid

    pivot = left

    # 二分查找
    if target >= arr[pivot] and target <= arr[-1]:
        return binary_search_in_range(arr, target, pivot, len(arr) - 1)
    else:
        return binary_search_in_range(arr, target, 0, pivot - 1)


# ============ 5. 搜索二维矩阵 ============
def search_matrix(matrix: list[list[int]], target: int) -> bool:
    """
    在行列都有序的二维矩阵中查找
    从右上角开始，每次排除一行或一列
    """
    if not matrix:
        return False

    rows, cols = len(matrix), len(matrix[0])
    row, col = 0, cols - 1

    while row < rows and col >= 0:
        if matrix[row][col] == target:
            return True
        elif matrix[row][col] > target:
            col -= 1
        else:
            row += 1

    return False


# ============ 6. 寻找峰值 ============
def find_peak_element(arr: list) -> int:
    """
    寻找一个峰值元素（比邻居大）
    返回任意一个峰值索引
    """
    left, right = 0, len(arr) - 1

    while left < right:
        mid = (left + right) // 2

        if arr[mid] < arr[mid + 1]:
            left = mid + 1
        else:
            right = mid

    return left


# ============ 7. 搜索重复元素（斐波那契查找） ============
def fibonacci_search(arr: list, target: int) -> int:
    """斐波那契查找 - O(log n)"""
    n = len(arr)
    fib_m2 = 0  # F(k-2)
    fib_m1 = 1  # F(k-1)
    fib = fib_m1 + fib_m2  # F(k)

    while fib < n:
        fib_m2 = fib_m1
        fib_m1 = fib
        fib = fib_m1 + fib_m2

    offset = -1

    while fib > 1:
        i = min(offset + fib_m2, n - 1)

        if arr[i] < target:
            fib = fib_m1
            fib_m1 = fib_m2
            fib_m2 = fib - fib_m1
            offset = i
        elif arr[i] > target:
            fib = fib_m2
            fib_m1 = fib_m1 - fib_m2
            fib_m2 = fib - fib_m1
        else:
            return i

    if fib_m1 and offset + 1 < n and arr[offset + 1] == target:
        return offset + 1

    return -1


if __name__ == "__main__":
    print("=== 查找算法 ===")

    # 二分查找
    print("\n1. 二分查找:")
    arr = [1, 3, 5, 7, 9, 11, 13, 15]
    target = 7
    print(f"  数组: {arr}, 目标: {target}")
    print(f"  索引: {binary_search(arr, target)}")  # 3

    # 二分查找变体
    print("\n2. 二分查找变体:")
    arr = [1, 2, 2, 2, 3, 4, 5]
    print(f"  数组: {arr}")
    print(f"  第一个>=2的位置: {binary_search_left(arr, 2)}")  # 1
    print(f"  最后一个<=2的位置: {binary_search_right(arr, 2)}")  # 3

    # 旋转数组
    print("\n3. 旋转数组搜索:")
    rotated = [4, 5, 6, 7, 0, 1, 2]
    print(f"  数组: {rotated}, 目标: 0")
    print(f"  索引: {search_rotated(rotated, 0)}")  # 4

    # 二维矩阵搜索
    print("\n4. 二维矩阵搜索:")
    matrix = [
        [1, 4, 7, 11],
        [2, 5, 8, 12],
        [3, 6, 9, 16],
        [10, 13, 14, 17]
    ]
    print(f"  目标 5: {search_matrix(matrix, 5)}")  # True
    print(f"  目标 20: {search_matrix(matrix, 20)}")  # False

    # 寻找峰值
    print("\n5. 寻找峰值:")
    arr = [1, 2, 3, 1]
    print(f"  数组: {arr}, 峰值索引: {find_peak_element(arr)}")  # 2

    arr2 = [1, 2, 1, 3, 1]
    print(f"  数组: {arr2}, 峰值索引: {find_peak_element(arr2)}")  # 1 或 3

    # 斐波那契查找
    print("\n6. 斐波那契查找:")
    arr = [1, 2, 3, 4, 5, 6, 7, 8]
    print(f"  数组: {arr}, 目标: 5")
    print(f"  索引: {fibonacci_search(arr, 5)}")  # 4

    # 复杂度总结
    print("\n7. 查找算法复杂度总结:")
    print("  ┌─────────────────┬──────────┐")
    print("  │ 算法            │ 时间     │")
    print("  ├─────────────────┼──────────┤")
    print("  │ 二分查找        │ O(log n) │")
    print("  │ 插值查找        │ O(log n) │")
    print("  │ 指数查找        │ O(log n) │")
    print("  │ 斐波那契查找    │ O(log n) │")
    print("  │ 二维矩阵搜索    │ O(m+n)   │")
    print("  └─────────────────┴──────────┘")