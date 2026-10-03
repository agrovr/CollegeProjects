from collections import deque

import pytest

import maze


def bfs(maze_data, start):
    seen = {start: 0}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        for neighbour in maze.open_neighbors(maze_data["walls"], cell):
            if neighbour not in seen:
                seen[neighbour] = seen[cell] + 1
                queue.append(neighbour)
    return seen


@pytest.mark.parametrize("seed", range(20))
def test_every_cell_is_reachable_and_the_maze_is_a_tree(seed):
    maze_data = maze.generate_maze(12, 12, seed=seed)
    reachable = bfs(maze_data, maze_data["start"])
    assert len(reachable) == 144
    openings = sum(len(maze.open_neighbors(maze_data["walls"], (x, y))) for y in range(12) for x in range(12))
    assert openings // 2 == 143  # a perfect maze has exactly cells - 1 passages


@pytest.mark.parametrize("seed", range(20))
def test_exit_is_the_farthest_cell_and_the_route_is_walkable(seed):
    maze_data = maze.generate_maze(12, 12, seed=seed)
    distances = bfs(maze_data, maze_data["start"])
    assert distances[maze_data["finish"]] == max(distances.values())
    path = maze_data["path"]
    assert path[0] == maze_data["start"] and path[-1] == maze_data["finish"]
    for a, b in zip(path, path[1:]):
        assert b in maze.open_neighbors(maze_data["walls"], a)


def test_same_seed_same_maze():
    assert maze.generate_maze(12, 12, seed=7) == maze.generate_maze(12, 12, seed=7)
    assert maze.generate_maze(12, 12, seed=7)["walls"] != maze.generate_maze(12, 12, seed=8)["walls"]


def test_features_stay_off_the_start_and_exit():
    for seed in range(20):
        maze_data = maze.generate_maze(12, 12, seed=seed)
        assert maze_data["start"] not in maze_data["features"]
        assert maze_data["finish"] not in maze_data["features"]


def test_walls_block_movement():
    maze_data = maze.generate_maze(12, 12, seed=3)
    size = 3.0
    x, y = maze.cell_center((0, 0), size)
    # Push hard against the outer wall: the player stays inside the maze.
    for _ in range(50):
        x, y = maze.move_with_collision(maze_data, x, y, -0.5, -0.5, 0.3, size)
    assert x >= 0.3 - 1e-9 and y >= 0.3 - 1e-9
    assert maze.can_stand(maze_data, x, y, 0.3, size)
