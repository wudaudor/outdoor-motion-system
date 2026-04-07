"""
排序算法示例
"""


# ============ 1. 冒泡排序 ============
def bubble_sort(arr: list) -> list:
    """冒泡排序 - O(n²)"""
    n = len(arr)
    arr = arr.copy()

    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        if not swapped:
            break

    return arr


# ============ 2. 快速排序 ============
def quick_sort(arr: list) -> list:
    """快速排序 - 平均 O(n log n)"""
    if len(arr) <= 1:
        return arr

    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]

    return quick_sort(left) + middle + quick_sort(right)


# ============ 3. 归并排序 ============
def merge_sort(arr: list) -> list:
    """归并排序 - O(n log n)"""
    if len(arr) <= 1:
        return arr

    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])

    return merge_two(left, right)


def merge_two(a: list, b: list) -> list:
    """合并两个有序数组"""
    result = []
    i = j = 0

    while i < len(a) and j < len(b):
        if a[i] <= b[j]:
            result.append(a[i])
            i += 1
        else:
            result.append(b[j])
            j += 1

    result.extend(a[i:])
    result.extend(b[j:])
    return result


# ============ 4. 堆排序 ============
def heap_sort(arr: list) -> list:
    """堆排序 - O(n log n)"""
    import heapq
    heap = arr.copy()
    heapq.heapify(heap)
    return [heapq.heappop(heap) for _ in range(len(heap))]


# ============ 5. 计数排序 ============
def counting_sort(arr: list, max_val: int = None) -> list:
    """计数排序 - O(n+k)，适用于范围较小的整数"""
    if not arr:
        return []

    if max_val is None:
        max_val = max(arr)

    count = [0] * (max_val + 1)
    result = []

    for num in arr:
        count[num] += 1

    for i, c in enumerate(count):
        result.extend([i] * c)

    return result


# ============ 6. 桶排序 ============
def bucket_sort(arr: list, num_buckets: int = 5) -> list:
    """桶排序 - O(n+k)"""
    if not arr:
        return []

    min_val, max_val = min(arr), max(arr)
    range_val = (max_val - min_val) / num_buckets or 1

    buckets = [[] for _ in range(num_buckets)]

    # 分配到桶
    for num in arr:
        idx = min(int((num - min_val) / range_val), num_buckets - 1)
        buckets[idx].append(num)

    # 各桶内排序后合并
    result = []
    for bucket in buckets:
        bucket.sort()
        result.extend(bucket)

    return result


# ============ 7. 算法复杂度对比 ============
def benchmark_sort():
    """简单性能测试"""
    import time
    import random

    sizes = [100, 1000, 5000]
    algorithms = {
        "冒泡排序": bubble_sort,
        "快速排序": quick_sort,
        "归并排序": merge_sort,
        "堆排序": heap_sort,
        "计数排序": counting_sort,
        "桶排序": bucket_sort,
    }

    print("\n排序算法性能对比 (随机数组):")
    print(f"{'算法':<12}", end="")

    for size in sizes:
        print(f"{size:>10}", end="")
    print()

    for name, sort_fn in algorithms.items():
        print(f"{name:<12}", end="")

        for size in sizes:
            arr = [random.randint(0, size) for _ in range(size)]

            start = time.time()
            sort_fn(arr)
            elapsed = time.time() - start

            print(f"{elapsed*1000:>10.2f}", end="")
        print()


if __name__ == "__main__":
    print("=== 排序算法 ===")

    test_arrays = [
        [64, 34, 25, 12, 22, 11, 90],
        [5, 2, 8, 1, 9, 3, 7, 4, 6],
        [3, 3, 3, 1, 1, 2, 2, 0],
    ]

    for arr in test_arrays:
        print(f"\n原数组: {arr}")
        print(f"  冒泡: {bubble_sort(arr)}")
        print(f"  快速: {quick_sort(arr)}")
        print(f"  归并: {merge_sort(arr)}")
        print(f"  堆排: {heap_sort(arr)}")
        print(f"  计数: {counting_sort(arr, max(arr))}")
        print(f"  桶排: {bucket_sort(arr)}")

    # 性能测试
    benchmark_sort()
