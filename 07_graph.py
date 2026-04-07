"""
图 (Graph) 的应用示例
"""

from collections import defaultdict, deque
import math


# ============ 1. 图的表示 ============
class Graph:
    """邻接表表示的图"""

    def __init__(self, directed=False):
        self.graph = defaultdict(list)
        self.directed = directed

    def add_edge(self, u, v, weight=1):
        self.graph[u].append((v, weight))
        if not self.directed:
            self.graph[v].append((u, weight))

    def bfs(self, start):
        """广度优先遍历"""
        visited = set()
        queue = deque([start])
        visited.add(start)
        result = []

        while queue:
            node = queue.popleft()
            result.append(node)

            for neighbor, _ in self.graph[node]:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        return result

    def dfs(self, start, visited=None):
        """深度优先遍历"""
        if visited is None:
            visited = set()

        visited.add(start)
        result = [start]

        for neighbor, _ in self.graph[start]:
            if neighbor not in visited:
                result.extend(self.dfs(neighbor, visited))

        return result


# ============ 2. 最短路径 - Dijkstra ============
def dijkstra(graph: dict, start) -> dict:
    """
    Dijkstra 单源最短路径
    graph: {节点: [(邻居, 权重), ...]}
    """
    dist = {start: 0}
    pq = [(0, start)]  # (距离, 节点)
    visited = set()

    while pq:
        d, node = heapq.heappop(pq)

        if node in visited:
            continue
        visited.add(node)

        for neighbor, weight in graph[node]:
            new_dist = d + weight
            if neighbor not in dist or new_dist < dist[neighbor]:
                dist[neighbor] = new_dist
                heapq.heappush(pq, (new_dist, neighbor))

    return dist


# ============ 3. 拓扑排序 ============
def topological_sort(graph: dict) -> list:
    """Kahn算法拓扑排序"""
    in_degree = defaultdict(int)
    all_nodes = set(graph.keys())

    # 初始化入度
    for node in graph:
        for neighbor, _ in graph[node]:
            in_degree[neighbor] += 1
            all_nodes.add(neighbor)

    # 入度为0的节点队列
    queue = deque([node for node in all_nodes if in_degree[node] == 0])
    result = []

    while queue:
        node = queue.popleft()
        result.append(node)

        for neighbor, _ in graph[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return result


# ============ 4. 最小生成树 - Prim ============
def prim(graph: dict, start) -> tuple:
    """
    Prim 最小生成树算法
    返回: (总权重, 边列表)
    """
    visited = {start}
    edges = []
    total_weight = 0
    pq = []

    for neighbor, weight in graph[start]:
        heapq.heappush(pq, (weight, start, neighbor))

    while pq and len(visited) < len(graph):
        weight, u, v = heapq.heappop(pq)

        if v in visited:
            continue

        visited.add(v)
        edges.append((u, v, weight))
        total_weight += weight

        for neighbor, w in graph[v]:
            if neighbor not in visited:
                heapq.heappush(pq, (w, v, neighbor))

    return total_weight, edges


# ============ 5. 岛屿数量（DFS） ============
def num_islands(grid: list[list[str]]) -> int:
    """计算网格中岛屿的数量"""
    if not grid:
        return 0

    rows, cols = len(grid), len(grid[0])
    count = 0

    def dfs(r, c):
        if r < 0 or c < 0 or r >= rows or c >= cols or grid[r][c] == '0':
            return
        grid[r][c] = '0'  # 标记已访问
        dfs(r + 1, c)
        dfs(r - 1, c)
        dfs(r, c + 1)
        dfs(r, c - 1)

    for r in range(rows):
        for c in range(cols):
            if grid[r][c] == '1':
                count += 1
                dfs(r, c)

    return count


# ============ 6. 课程表（检测环） ============
def can_finish(num_courses: int, prerequisites: list) -> bool:
    """判断是否能完成所有课程（检测有向图是否有环）"""
    graph = defaultdict(list)
    in_degree = [0] * num_courses

    for u, v in prerequisites:
        graph[v].append(u)
        in_degree[u] += 1

    queue = deque([i for i in range(num_courses) if in_degree[i] == 0])
    completed = 0

    while queue:
        course = queue.popleft()
        completed += 1

        for next_course in graph[course]:
            in_degree[next_course] -= 1
            if in_degree[next_course] == 0:
                queue.append(next_course)

    return completed == num_courses


# ============ 7. 克隆图 ============
class Node:
    def __init__(self, val=0, neighbors=None):
        self.val = val
        self.neighbors = neighbors or []


def clone_graph(node: Node) -> Node:
    """克隆无向图"""
    if not node:
        return None

    clones = {node: Node(node.val)}
    queue = deque([node])

    while queue:
        current = queue.popleft()

        for neighbor in current.neighbors:
            if neighbor not in clones:
                clones[neighbor] = Node(neighbor.val)
                queue.append(neighbor)

            clones[current].neighbors.append(clones[neighbor])

    return clones[node]


# ============ 8. 欧拉路径（Hierholzer算法） ============
def find_eulerian_path(graph: dict, start) -> list:
    """
    查找欧拉路径（经过每条边恰好一次）
    适用于有向图
    """
    # 统计入度和出度
    in_degree = defaultdict(int)
    out_degree = defaultdict(int)

    for u in graph:
        out_degree[u] = len(graph[u])
        for v, _ in graph[u]:
            in_degree[v] += 1

    # 找起点
    start_node = start
    end_node = start

    for node in out_degree:
        if out_degree[node] - in_degree[node] == 1:
            start_node = node
        elif out_degree[node] - in_degree[node] == -1:
            end_node = node

    # Hierholzer算法
    stack = [start_node]
    path = []
    temp_graph = {k: list(v) for k, v in graph.items()}

    while stack:
        node = stack[-1]
        if temp_graph[node]:
            next_node, _ = temp_graph[node].pop()
            stack.append(next_node)
        else:
            path.append(stack.pop())

    return path[::-1]


import heapq

if __name__ == "__main__":
    print("=== 图的应用 ===")

    # 创建测试图
    #     A ---3--- B
    #     |       / \
    #     2      1   4
    #     |     /     \
    #     D---2------- C
    #          \       /
    #           5-----

    print("\n1. 图的遍历:")
    g = Graph()
    g.add_edge('A', 'B', 3)
    g.add_edge('A', 'D', 2)
    g.add_edge('B', 'C', 4)
    g.add_edge('B', 'D', 1)
    g.add_edge('C', 'D', 5)

    print(f"  BFS (从A): {g.bfs('A')}")
    print(f"  DFS (从A): {g.dfs('A')}")

    # Dijkstra
    print("\n2. Dijkstra 最短路径:")
    graph = {
        'A': [('B', 3), ('D', 2)],
        'B': [('C', 4), ('D', 1)],
        'C': [('D', 5)],
        'D': []
    }
    print(f"  从A到各点最短距离: {dijkstra(graph, 'A')}")

    # 拓扑排序
    print("\n3. 拓扑排序:")
    dag = {
        'A': [('C', 1)],
        'B': [('C', 1)],
        'C': [('D', 1)],
        'D': []
    }
    print(f"  顺序: {topological_sort(dag)}")

    # 最小生成树
    print("\n4. Prim 最小生成树:")
    mst_graph = {
        'A': [('B', 1), ('C', 3)],
        'B': [('A', 1), ('C', 1), ('D', 4)],
        'C': [('A', 3), ('B', 1), ('D', 1)],
        'D': [('B', 4), ('C', 1)]
    }
    weight, edges = prim(mst_graph, 'A')
    print(f"  总权重: {weight}")
    print(f"  边: {edges}")

    # 岛屿数量
    print("\n5. 岛屿数量:")
    grid = [
        ['1', '1', '0', '0', '0'],
        ['1', '1', '0', '0', '0'],
        ['0', '0', '1', '0', '0'],
        ['0', '0', '0', '1', '1']
    ]
    print(f"  网格岛屿数: {num_islands(grid)}")  # 3

    # 课程表
    print("\n6. 课程表（能否完成）:")
    print(f"  2门课，前置[1,0] -> {can_finish(2, [[1, 0]])}")  # True
    print(f"  2门课，前置[1,0],[0,1] -> {can_finish(2, [[1, 0], [0, 1]])}")  # False

    # 欧拉路径
    print("\n7. 欧拉路径:")
    euler_graph = {
        0: [(1, 1)],
        1: [(2, 1), (3, 1)],
        2: [(0, 1), (3, 1)],
        3: [(4, 1)],
        4: [(3, 1)]
    }
    print(f"  路径: {find_eulerian_path(euler_graph, 1)}")