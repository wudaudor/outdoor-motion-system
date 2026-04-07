"""
二叉树 (Binary Tree) 的应用示例
"""


# ============ 1. 二叉树节点 ============
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


# ============ 2. 二叉搜索树（BST） ============
class BST:
    """简单的二叉搜索树实现"""

    def __init__(self):
        self.root = None

    def insert(self, val):
        """插入节点"""
        if not self.root:
            self.root = TreeNode(val)
        else:
            self._insert_rec(self.root, val)

    def _insert_rec(self, node, val):
        if val < node.val:
            if node.left:
                self._insert_rec(node.left, val)
            else:
                node.left = TreeNode(val)
        else:
            if node.right:
                self._insert_rec(node.right, val)
            else:
                node.right = TreeNode(val)

    def search(self, val) -> bool:
        """搜索节点"""
        return self._search_rec(self.root, val)

    def _search_rec(self, node, val):
        if not node:
            return False
        if val == node.val:
            return True
        elif val < node.val:
            return self._search_rec(node.left, val)
        else:
            return self._search_rec(node.right, val)


# ============ 3. 二叉树遍历 ============
def preorder(root: TreeNode) -> list:
    """前序遍历: 根-左-右"""
    if not root:
        return []
    return [root.val] + preorder(root.left) + preorder(root.right)


def inorder(root: TreeNode) -> list:
    """中序遍历: 左-根-右（BST排序输出）"""
    if not root:
        return []
    return inorder(root.left) + [root.val] + inorder(root.right)


def postorder(root: TreeNode) -> list:
    """后序遍历: 左-右-根"""
    if not root:
        return []
    return postorder(root.left) + postorder(root.right) + [root.val]


def level_order(root: TreeNode) -> list[list]:
    """层序遍历（按层输出）"""
    if not root:
        return []

    result = []
    queue = [root]

    while queue:
        level_size = len(queue)
        level_vals = []

        for _ in range(level_size):
            node = queue.pop(0)
            level_vals.append(node.val)

            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)

        result.append(level_vals)

    return result


# ============ 4. 二叉树深度 ============
def max_depth(root: TreeNode) -> int:
    """计算二叉树最大深度"""
    if not root:
        return 0
    return 1 + max(max_depth(root.left), max_depth(root.right))


# ============ 5. 验证二叉搜索树 ============
def is_valid_bst(root: TreeNode, min_val=float('-inf'), max_val=float('inf')) -> bool:
    """验证是否为合法的二叉搜索树"""
    if not root:
        return True

    if root.val <= min_val or root.val >= max_val:
        return False

    return (is_valid_bst(root.left, min_val, root.val) and
            is_valid_bst(root.right, root.val, max_val))


# ============ 6. 最近的公共祖先 ============
def lowest_common_ancestor(root: TreeNode, p: TreeNode, q: TreeNode) -> TreeNode:
    """查找最近公共祖先"""
    if not root or root == p or root == q:
        return root

    left = lowest_common_ancestor(root.left, p, q)
    right = lowest_common_ancestor(root.right, p, q)

    if left and right:
        return root
    return left or right


# ============ 7. 二叉树构建（层序） ============
def build_tree_from_list(values: list) -> TreeNode:
    """从层序列表构建二叉树"""
    if not values:
        return None

    root = TreeNode(values[0])
    queue = [root]
    i = 1

    while queue and i < len(values):
        node = queue.pop(0)

        # 左子节点
        if i < len(values) and values[i] is not None:
            node.left = TreeNode(values[i])
            queue.append(node.left)
        i += 1

        # 右子节点
        if i < len(values) and values[i] is not None:
            node.right = TreeNode(values[i])
            queue.append(node.right)
        i += 1

    return root


def tree_to_list(root: TreeNode) -> list:
    """二叉树转层序列表"""
    if not root:
        return []

    result = []
    queue = [root]

    while queue:
        node = queue.pop(0)
        if node:
            result.append(node.val)
            queue.append(node.left)
            queue.append(node.right)
        else:
            result.append(None)

    # 移除末尾的None
    while result and result[-1] is None:
        result.pop()

    return result


if __name__ == "__main__":
    print("=== 二叉树的应用 ===")

    # 构建BST
    print("\n1. 二叉搜索树:")
    bst = BST()
    for val in [7, 3, 9, 1, 5, 8, 10]:
        bst.insert(val)
    print(f"  插入: [7, 3, 9, 1, 5, 8, 10]")
    print(f"  搜索 5: {bst.search(5)}")
    print(f"  搜索 6: {bst.search(6)}")

    # 构建测试树
    print("\n2. 二叉树遍历:")
    #       1
    #      / \
    #     2   3
    #    / \   \
    #   4   5   6
    root = build_tree_from_list([1, 2, 3, 4, 5, None, 6])
    print(f"  树结构: {tree_to_list(root)}")
    print(f"  前序遍历: {preorder(root)}")    # [1,2,4,5,3,6]
    print(f"  中序遍历: {inorder(root)}")     # [4,2,5,1,3,6]
    print(f"  后序遍历: {postorder(root)}")   # [4,5,2,6,3,1]
    print(f"  层序遍历: {level_order(root)}") # [[1], [2,3], [4,5,6]]

    # 二叉树深度
    print("\n3. 二叉树深度:")
    print(f"  树的最大深度: {max_depth(root)}")  # 3

    # 验证BST
    print("\n4. 验证BST:")
    bst_tree = build_tree_from_list([2, 1, 3])
    print(f"  [2,1,3] 是BST: {is_valid_bst(bst_tree)}")
    invalid_tree = build_tree_from_list([5, 1, 4, None, None, 3, 6])
    print(f"  [5,1,4,None,None,3,6] 是BST: {is_valid_bst(invalid_tree)}")  # False

    # 最近公共祖先
    print("\n5. 最近公共祖先:")
    # 创建一个更复杂的树来测试
    #       3
    #      / \
    #     5   1
    #    / \  / \
    #   6  2 0   8
    tree = build_tree_from_list([3, 5, 1, 6, 2, 0, 8])
    p = tree.left  # 5
    q = tree.right  # 1
    lca = lowest_common_ancestor(tree, p, q)
    print(f"  节点5和节点1的LCA: {lca.val if lca else 'None'}")  # 3