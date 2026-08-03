import math
import random
from collections import deque


NORTH = 1
EAST = 2
SOUTH = 4
WEST = 8
ALL_WALLS = NORTH | EAST | SOUTH | WEST

DIRECTIONS = (
    (0, -1, NORTH, SOUTH),
    (1, 0, EAST, WEST),
    (0, 1, SOUTH, NORTH),
    (-1, 0, WEST, EAST),
)


def _carve_maze(width, height, rng):
    walls = [[ALL_WALLS for _ in range(width)] for _ in range(height)]
    visited = {(0, 0)}
    stack = [(0, 0)]

    while stack:
        x, y = stack[-1]
        choices = []

        for dx, dy, wall, opposite in DIRECTIONS:
            next_x = x + dx
            next_y = y + dy
            if (0 <= next_x < width and 0 <= next_y < height
                    and (next_x, next_y) not in visited):
                choices.append((next_x, next_y, wall, opposite))

        if choices:
            next_x, next_y, wall, opposite = rng.choice(choices)
            walls[y][x] &= ~wall
            walls[next_y][next_x] &= ~opposite
            visited.add((next_x, next_y))
            stack.append((next_x, next_y))
        else:
            stack.pop()

    return walls


def open_neighbors(walls, cell):
    width = len(walls[0])
    height = len(walls)
    x, y = cell
    neighbors = []

    for dx, dy, wall, _ in DIRECTIONS:
        next_x = x + dx
        next_y = y + dy
        if (walls[y][x] & wall) == 0:
            if 0 <= next_x < width and 0 <= next_y < height:
                neighbors.append((next_x, next_y))

    return neighbors


def _find_paths(walls, start):
    distances = {start: 0}
    parents = {start: None}
    waiting = deque([start])

    while waiting:
        cell = waiting.popleft()
        for neighbor in open_neighbors(walls, cell):
            if neighbor not in distances:
                distances[neighbor] = distances[cell] + 1
                parents[neighbor] = cell
                waiting.append(neighbor)

    return distances, parents


def _build_path(parents, finish):
    path = []
    cell = finish

    while cell is not None:
        path.append(cell)
        cell = parents[cell]

    path.reverse()
    return path


def _choose_unused(candidates, used, rng):
    available = [cell for cell in candidates if cell not in used]
    if not available:
        return None
    cell = rng.choice(available)
    used.add(cell)
    return cell


def _place_features(walls, path, distances, start, finish, rng):
    width = len(walls[0])
    height = len(walls)
    path_set = set(path)
    blocked = {start, finish}
    features = {}

    all_cells = [
        (x, y)
        for y in range(height)
        for x in range(width)
        if (x, y) not in blocked and distances[(x, y)] > 3
    ]
    off_path = [cell for cell in all_cells if cell not in path_set]
    dead_ends = [
        cell for cell in off_path
        if len(open_neighbors(walls, cell)) == 1
    ]

    curse_choices = sorted(dead_ends or off_path or all_cells,
                            key=lambda cell: distances[cell], reverse=True)
    curse_cell = _choose_unused(curse_choices[:8], blocked, rng)
    if curse_cell:
        features[curse_cell] = "curse"

    far_off_path = sorted(off_path, key=lambda cell: distances[cell], reverse=True)
    eye_cell = _choose_unused(far_off_path[:max(8, len(far_off_path) // 2)],
                              blocked, rng)
    if eye_cell:
        features[eye_cell] = "eye"

    lift_cell = _choose_unused(far_off_path[:max(12, len(far_off_path) // 2)],
                               blocked, rng)
    if lift_cell:
        features[lift_cell] = "lift"

    trap_choices = off_path if off_path else all_cells
    for _ in range(4):
        cell = _choose_unused(trap_choices, blocked, rng)
        if cell:
            features[cell] = "lava"

    for _ in range(2):
        cell = _choose_unused(trap_choices, blocked, rng)
        if cell:
            features[cell] = "turn"

    path_choices = path[4:-3]
    if path_choices:
        target_indexes = (len(path_choices) // 4,
                          len(path_choices) // 2,
                          (3 * len(path_choices)) // 4)
        for index in target_indexes:
            nearby = path_choices[max(0, index - 2):index + 3]
            cell = _choose_unused(nearby, blocked, rng)
            if cell:
                features[cell] = "speed"

    eye_cell = _choose_unused(dead_ends or off_path or all_cells, blocked, rng)
    if eye_cell:
        features[eye_cell] = "eye"

    return features


def generate_maze(width=12, height=12, seed=None):
    rng = random.Random(seed)
    start = (0, 0)
    best_result = None

    for _ in range(8):
        walls = _carve_maze(width, height, rng)
        distances, parents = _find_paths(walls, start)
        finish = max(distances, key=distances.get)
        path = _build_path(parents, finish)

        if best_result is None or len(path) > len(best_result[3]):
            best_result = (walls, distances, parents, path, finish)
        if len(path) >= (width * height) // 3:
            break

    walls, distances, parents, path, finish = best_result
    features = _place_features(walls, path, distances, start, finish, rng)

    return {
        "width": width,
        "height": height,
        "walls": walls,
        "start": start,
        "finish": finish,
        "path": path,
        "distances": distances,
        "features": features,
    }


def has_wall(maze_data, cell, wall):
    x, y = cell
    return (maze_data["walls"][y][x] & wall) != 0


def cell_center(cell, cell_size):
    x, y = cell
    return ((x + 0.5) * cell_size, (y + 0.5) * cell_size)


def world_to_cell(x, y, cell_size):
    return (int(math.floor(x / cell_size)), int(math.floor(y / cell_size)))


def can_stand(maze_data, x, y, radius, cell_size):
    maze_width = maze_data["width"] * cell_size
    maze_height = maze_data["height"] * cell_size

    if (x - radius < 0 or x + radius > maze_width
            or y - radius < 0 or y + radius > maze_height):
        return False

    cell_x, cell_y = world_to_cell(x, y, cell_size)
    if not (0 <= cell_x < maze_data["width"]
            and 0 <= cell_y < maze_data["height"]):
        return False

    local_x = x - cell_x * cell_size
    local_y = y - cell_y * cell_size
    walls = maze_data["walls"][cell_y][cell_x]

    if local_x < radius and (walls & WEST):
        return False
    if local_x > cell_size - radius and (walls & EAST):
        return False
    if local_y < radius and (walls & NORTH):
        return False
    if local_y > cell_size - radius and (walls & SOUTH):
        return False

    return True


def move_with_collision(maze_data, x, y, dx, dy, radius, cell_size):
    next_x = x + dx
    if can_stand(maze_data, next_x, y, radius, cell_size):
        x = next_x

    next_y = y + dy
    if can_stand(maze_data, x, next_y, radius, cell_size):
        y = next_y

    return x, y
