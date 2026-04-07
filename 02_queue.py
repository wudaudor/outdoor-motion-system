"""
队列 (Queue) 的应用示例
"""

from collections import deque
import time


# ============ 1. 约瑟夫问题 ============
def josephus(n: int, k: int) -> int:
    """约瑟夫环：n个人围成圈，每次数到k的人出列，返回最后存活者的编号"""
    queue = deque(range(1, n + 1))

    while len(queue) > 1:
        for _ in range(k - 1):
            queue.append(queue.popleft())  # 队首移到队尾
        queue.popleft()  # 第k个人出列

    return queue[0]


# ============ 2. 任务调度器 ============
class TaskScheduler:
    """模拟任务队列调度"""

    def __init__(self):
        self.tasks = deque()

    def add_task(self, task_name: str, priority: int = 0):
        """添加任务（priority越大优先级越高）"""
        self.tasks.append((priority, task_name))
        # 按优先级排序
        self.tasks = deque(sorted(self.tasks, key=lambda x: -x[0]))

    def execute_next(self):
        """执行下一个任务"""
        if self.tasks:
            priority, task = self.tasks.popleft()
            print(f"执行任务: {task} (优先级: {priority})")
            return task
        print("没有待执行的任务")
        return None

    def show_pending(self):
        """显示待执行任务"""
        print(f"待执行任务 ({len(self.tasks)}个):")
        for p, t in self.tasks:
            print(f"  - {t} (优先级: {p})")


# ============ 3. 滑动窗口最大值 ============
def max_sliding_window(nums: list[int], k: int) -> list[int]:
    """获取滑动窗口最大值"""
    if not nums or k == 0:
        return []

    deque_idx = deque()  # 存索引
    result = []

    for i, num in enumerate(nums):
        # 移除超出窗口的索引
        while deque_idx and deque_idx[0] <= i - k:
            deque_idx.popleft()

        # 移除比当前元素小的索引（保持递减）
        while deque_idx and nums[deque_idx[-1]] < num:
            deque_idx.pop()

        deque_idx.append(i)

        # 窗口形成后记录最大值
        if i >= k - 1:
            result.append(nums[deque_idx[0]])

    return result


# ============ 4. 生产者-消费者模拟 ============
class ProducerConsumer:
    """模拟生产者消费者问题"""

    def __init__(self, buffer_size: int = 5):
        self.buffer = deque(maxlen=buffer_size)
        self.max_size = buffer_size

    def produce(self, item: str):
        """生产数据"""
        if len(self.buffer) >= self.max_size:
            print(f"缓冲区满，生产者等待...")
            return False
        self.buffer.append(item)
        print(f"生产: {item}, 缓冲区: {list(self.buffer)}")
        return True

    def consume(self):
        """消费数据"""
        if not self.buffer:
            print("缓冲区空，消费者等待...")
            return None
        item = self.buffer.popleft()
        print(f"消费: {item}, 缓冲区: {list(self.buffer)}")
        return item


if __name__ == "__main__":
    print("=== 队列的应用 ===")

    # 约瑟夫问题
    print("\n1. 约瑟夫问题:")
    print(f"  n=5, k=2 -> 最后存活者编号: {josephus(5, 2)}")  # 3

    # 任务调度器
    print("\n2. 任务调度器:")
    scheduler = TaskScheduler()
    scheduler.add_task("发送邮件", priority=2)
    scheduler.add_task("数据备份", priority=1)
    scheduler.add_task("处理请求", priority=3)
    scheduler.show_pending()
    print("执行顺序:")
    scheduler.execute_next()
    scheduler.execute_next()
    scheduler.execute_next()

    # 滑动窗口
    print("\n3. 滑动窗口最大值:")
    nums = [1, 3, -1, -3, 5, 3, 6, 7]
    k = 3
    print(f"  输入: {nums}, 窗口大小: {k}")
    print(f"  输出: {max_sliding_window(nums, k)}")  # [3, 3, 5, 5, 6, 7]

    # 生产者-消费者
    print("\n4. 生产者-消费者模拟:")
    pc = ProducerConsumer(buffer_size=3)
    pc.produce("A")
    pc.produce("B")
    pc.produce("C")
    pc.produce("D")  # 缓冲区满
    pc.consume()
    pc.consume()
    pc.consume()
    pc.consume()  # 缓冲区空