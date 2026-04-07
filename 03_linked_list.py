"""
链表 (Linked List) 的应用示例
"""


# ============ 1. 单链表节点 ============
class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next


# ============ 2. LRU 缓存（链表 + 哈希表） ============
class LRUCache:
    """
    LRU 缓存实现
    使用哈希表 + 双向链表实现 O(1) 访问
    """

    def __init__(self, capacity: int):
        self.capacity = capacity
        self.cache = {}  # key -> node
        # 虚拟头尾节点
        self.head = ListNode()
        self.tail = ListNode()
        self.head.next = self.tail
        self.tail.prev = self.head

    def _remove(self, node):
        """从链表中移除节点"""
        node.prev.next = node.next
        node.next.prev = node.prev

    def _add_to_front(self, node):
        """添加到链表头部（最近使用）"""
        node.next = self.head.next
        node.prev = self.head
        self.head.next.prev = node
        self.head.next = node

    def get(self, key: int) -> int:
        """获取值，不存在返回-1"""
        if key in self.cache:
            node = self.cache[key]
            self._remove(node)
            self._add_to_front(node)
            return node.val
        return -1

    def put(self, key: int, value: int):
        """放入缓存"""
        if key in self.cache:
            node = self.cache[key]
            node.val = value
            self._remove(node)
            self._add_to_front(node)
        else:
            if len(self.cache) >= self.capacity:
                # 淘汰最久未使用的（tail前一个）
                lru = self.tail.prev
                self._remove(lru)
                del self.cache[lrU.val if hasattr(lru, 'val') else lru[1]]

            new_node = ListNode(value)
            self.cache[key] = new_node
            self._add_to_front(new_node)


# ============ 3. 合并两个有序链表 ============
def merge_two_lists(l1: ListNode, l2: ListNode) -> ListNode:
    """合并两个有序链表"""
    dummy = ListNode(0)
    curr = dummy

    while l1 and l2:
        if l1.val <= l2.val:
            curr.next = l1
            l1 = l1.next
        else:
            curr.next = l2
            l2 = l2.next
        curr = curr.next

    curr.next = l1 or l2
    return dummy.next


# ============ 4. 检测环形链表 ============
def has_cycle(head: ListNode) -> bool:
    """快慢指针检测环形链表"""
    slow = fast = head

    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next
        if slow == fast:
            return True

    return False


# ============ 5. 反转链表 ============
def reverse_list(head: ListNode) -> ListNode:
    """反转链表"""
    prev = None
    curr = head

    while curr:
        next_temp = curr.next
        curr.next = prev
        prev = curr
        curr = next_temp

    return prev


# ============ 6. 链表中点 ============
def middle_node(head: ListNode) -> ListNode:
    """快慢指针找中点"""
    slow = fast = head

    while fast and fast.next:
        slow = slow.next
        fast = fast.next.next

    return slow


def list_to_linked_list(values: list) -> ListNode:
    """列表转链表"""
    if not values:
        return None
    dummy = ListNode(0)
    curr = dummy
    for v in values:
        curr.next = ListNode(v)
        curr = curr.next
    return dummy.next


def linked_list_to_list(head: ListNode) -> list:
    """链表转列表"""
    result = []
    while head:
        result.append(head.val)
        head = head.next
    return result


if __name__ == "__main__":
    print("=== 链表的应用 ===")

    # LRU 缓存
    print("\n1. LRU 缓存:")
    cache = LRUCache(3)
    operations = [
        ("put", 1, 1),
        ("put", 2, 2),
        ("put", 3, 3),
        ("get", 1, None),  # 返回1
        ("put", 4, 4),     # 淘汰key=2
        ("get", 2, None), # 返回-1
        ("get", 3, None), # 返回3
    ]
    for op in operations:
        if op[0] == "put":
            cache.put(op[1], op[2])
            print(f"  put({op[1]}, {op[2]})")
        else:
            result = cache.get(op[1])
            print(f"  get({op[1]}) = {result}")

    # 合并有序链表
    print("\n2. 合并有序链表:")
    l1 = list_to_linked_list([1, 3, 5, 7])
    l2 = list_to_linked_list([2, 4, 6, 8])
    merged = merge_two_lists(l1, l2)
    print(f"  [1,3,5,7] + [2,4,6,8] = {linked_list_to_list(merged)}")

    # 检测环形链表
    print("\n3. 检测环形链表:")
    # 创建有环链表
    head = list_to_linked_list([1, 2, 3])
    head.next.next.next = head.next  # 3指向2，形成环
    print(f"  [1->2->3->2...] 有环: {has_cycle(head)}")

    # 反转链表
    print("\n4. 反转链表:")
    head = list_to_linked_list([1, 2, 3, 4, 5])
    reversed_head = reverse_list(head)
    print(f"  [1,2,3,4,5] 反转后 = {linked_list_to_list(reversed_head)}")

    # 找中点
    print("\n5. 链表的中点:")
    head = list_to_linked_list([1, 2, 3, 4, 5])
    mid = middle_node(head)
    print(f"  [1,2,3,4,5] 中点是: {mid.val}")