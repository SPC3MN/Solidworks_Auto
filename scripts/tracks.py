"""Generated (illustrative) copper tracks for board layouts.

The real routing of these boards is not known, so tracks are GENERATED: every
two-terminal passive end and every IC is routed to its nearest neighbouring
part or connector by a grid router that keeps clear of parts, holes, headers,
the board edge and other tracks. They make the model look and render like a
populated board; they are not the board's actual copper.

Geometry rules (so the volume is exact arithmetic):
- grid 0.5 mm, track width 0.3, so neighbouring tracks are >= 0.2 apart and a
  track never touches a part (centre >= 0.25 from any part box);
- paths are shortest with a turn penalty, so a track never touches itself;
- with mitred 90-degree corners, a track's area = centreline length x width.
Tracks sit on the PCB top (z = T .. T + t), touching only the PCB.

CLI: python scripts/tracks.py projects/<p>  -> writes "tracks" into the
project's layout file and prints the count and the added volume.
"""
import heapq
import json
import math
import pathlib
import sys

from layout_check import boxes, kind_of, part_geom

GRID, W, THICK = 0.5, 0.3, 0.035
HARD = W / 2 + 0.1          # track centre to part box, minimum
BAND = 0.8                  # a route may end within this distance of its target box
EDGE = 0.6


def _box_dist(px, py, b):
    dx = max(b[0] - px, 0, px - b[2])
    dy = max(b[1] - py, 0, py - b[3])
    return math.hypot(dx, dy)


class Router:
    def __init__(self, L, Wd, obstacles):
        self.L, self.Wd = L, Wd
        self.nx, self.ny = int(L / GRID), int(Wd / GRID)
        self.obst = obstacles  # [(ref, x0, y0, x1, y1)]
        self.blocked = set()
        for i in range(self.nx):
            for j in range(self.ny):
                x, y = self.xy(i, j)
                if x < EDGE or y < EDGE or x > L - EDGE or y > Wd - EDGE:
                    self.blocked.add((i, j))
        for _, *b in obstacles:
            for i in range(max(0, int((b[0] - HARD) / GRID) - 1), min(self.nx, int((b[2] + HARD) / GRID) + 2)):
                for j in range(max(0, int((b[1] - HARD) / GRID) - 1), min(self.ny, int((b[3] + HARD) / GRID) + 2)):
                    if _box_dist(*self.xy(i, j), b) < HARD:
                        self.blocked.add((i, j))

    def xy(self, i, j):
        return (i + 0.5) * GRID, (j + 0.5) * GRID

    def cell(self, x, y):
        return int(x / GRID), int(y / GRID)

    def route(self, start, target_box, max_len=60):
        """Turn-penalised shortest path from start cell to any free cell in the target band."""
        if start in self.blocked:
            return None
        goal = lambda c: _box_dist(*self.xy(*c), target_box) <= BAND  # noqa: E731
        pq = [(0, 0, start, None, None)]
        seen = {}
        while pq:
            cost, n, c, d, prev = heapq.heappop(pq)
            if (c, d) in seen:
                continue
            seen[(c, d)] = prev
            if goal(c) and n > 0:
                path, key = [c], (c, d)
                while seen[key] is not None:
                    key = seen[key]
                    path.append(key[0])
                return path[::-1]
            if n >= max_len:
                continue
            for nd in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nc = (c[0] + nd[0], c[1] + nd[1])
                if not (0 <= nc[0] < self.nx and 0 <= nc[1] < self.ny) or nc in self.blocked:
                    continue
                heapq.heappush(pq, (cost + 1 + (3 if d and nd != d else 0), n + 1, nc, nd, (c, d)))
        return None

    def commit(self, path):
        self.blocked.update(path)


def simplify(pts):
    out = [pts[0]]
    for a, b in zip(pts[1:], pts[2:]):
        p = out[-1]
        if (a[0] - p[0]) * (b[1] - a[1]) != (a[1] - p[1]) * (b[0] - a[0]):
            out.append(a)
    out.append(pts[-1])
    return out


def outline(pts, w=W):
    """Mitred outline polygon of an orthogonal polyline."""
    def normal(a, b):
        dx, dy = b[0] - a[0], b[1] - a[1]
        n = math.hypot(dx, dy)
        return -dy / n, dx / n
    left, right = [], []
    for k, p in enumerate(pts):
        ns = []
        if k > 0:
            ns.append(normal(pts[k - 1], p))
        if k < len(pts) - 1:
            ns.append(normal(p, pts[k + 1]))
        nx, ny = (ns[0][0] + ns[1][0], ns[0][1] + ns[1][1]) if len(ns) == 2 else ns[0]
        h = w / 2
        left.append((p[0] + nx * h, p[1] + ny * h))
        right.append((p[0] - nx * h, p[1] - ny * h))
    return left + right[::-1]


def track_volume(lay):
    t = lay.get("track_t", THICK)
    total = 0.0
    for tr in lay.get("tracks", []):
        pts = tr["pts"]
        total += sum(math.dist(a, b) for a, b in zip(pts, pts[1:])) * tr.get("w", W) * t
    return total


def apply(part, lay, T):
    """Extrude all tracks in one feature on the PCB top."""
    from swlib import polygon
    trs = lay.get("tracks", [])
    if trs:
        part.extrude("Tracks", [polygon(outline(tr["pts"], tr.get("w", W))) for tr in trs],
                     lay.get("track_t", THICK), z=T)


def generate(lay, keepouts, L, Wd):
    parts = [(c, part_geom(lay, c)) for c in lay.get("parts", [])]
    pboxes = {b[0]: b[1:5] for b in boxes(lay, with_leads=True)}
    obstacles = [(k, *v) for k, v in pboxes.items()] + [(k["ref"], k["x0"], k["y0"], k["x1"], k["y1"]) for k in keepouts]
    r = Router(L, Wd, obstacles)
    targets = [(o[0], o[1:]) for o in obstacles if not o[0].lower().startswith(("hole", "tp", "p5", "p6", "p10"))]

    def nearest(px, py, exclude):
        best = min(((_box_dist(px, py, b), ref, b) for ref, b in targets if ref != exclude), default=None)
        return best

    starts = []
    for c, (x, y, l, w, h, rot) in parts:
        if kind_of(lay, c) == "passive":
            along_x = l >= w
            for s in (-1, 1):
                ex, ey = (x + s * (l / 2 + HARD + 0.01), y) if along_x else (x, y + s * (w / 2 + HARD + 0.01))
                starts.append((c["ref"], ex, ey, (s, 0) if along_x else (0, s)))
        elif l * w < 400:  # ICs and small connectors: one route out of the +y side
            starts.append((c["ref"], x, y + w / 2 + HARD + 0.6, (0, 1)))
    tracks = []
    for ref, ex, ey, d in starts:
        cell = None
        for k in range(4):
            cand = r.cell(ex + d[0] * k * GRID, ey + d[1] * k * GRID)
            if cand not in r.blocked and 0 <= cand[0] < r.nx and 0 <= cand[1] < r.ny:
                cell = cand
                break
        if cell is None:
            continue
        nb = nearest(*r.xy(*cell), ref)
        if nb is None:
            continue
        path = r.route(cell, nb[2])
        if path is None or len(path) < 2:
            continue
        r.commit(path)
        pts = simplify([tuple(round(v, 4) for v in r.xy(*p)) for p in path])
        tracks.append({"from": ref, "to": nb[1], "pts": [list(p) for p in pts], "w": W})
    return tracks


def layout_file(project):
    f = project / "parameters" / "layout.json"
    return f if f.exists() else project / "parameters" / "smd_layout.json"


def main(project, board=None):
    f = layout_file(project)
    lay = json.loads(f.read_text())
    ko_f = project / "parameters" / "keepouts.json"
    keepouts = json.loads(ko_f.read_text()) if ko_f.exists() else []
    L, Wd = board or (lay["board"]["l"], lay["board"]["w"])
    lay["tracks"] = generate(lay, keepouts, L, Wd)
    lay["track_t"] = THICK
    lay["_tracks_note"] = "tracks are GENERATED by scripts/tracks.py (illustrative routing, not the real copper)"
    f.write_text(json.dumps(lay, indent=1) + "\n")
    print(f"{project.name}: {len(lay['tracks'])} tracks, volume {track_volume(lay):.4f} mm^3")


if __name__ == "__main__":
    sys.path.insert(0, str(pathlib.Path(__file__).parent))
    b = (float(sys.argv[2]), float(sys.argv[3])) if len(sys.argv) > 3 else None
    main(pathlib.Path(sys.argv[1]), b)
