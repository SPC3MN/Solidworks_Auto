"""Feasibility estimate: plug fan + turn (now) against an axial fan blowing straight up.

First-order numbers only (velocity heads, textbook loss factors, Cordier sizing). Run:
    .venv\\Scripts\\python projects\\airmn\\upflow_estimate.py
"""
import math

RHO = 1.2                    # kg/m3
Q = 500 / 3600               # m3/s, brief
P_FILTER = 2.4               # Pa at 500 m3/h, brief
CORE_R = 0.149               # m, pack inner radius
GRID_R, GRID_PHI = 0.2036, 0.62   # perforated lid top: grid radius, open fraction (current lid)
MOTOR_W_RATED = {"12 V 300 rpm": (300, 1.2), "24 V 600 rpm @15 V": (335, 2.0)}  # (loaded rpm est., kg cm)


def q(v):
    return 0.5 * RHO * v * v


def area(r_out, r_in=0.0):
    return math.pi * (r_out ** 2 - r_in ** 2)


def perf_plate_K(phi):
    """Idelchik, thin perforated plate, sharp holes; K on the approach velocity."""
    return (0.707 * math.sqrt(1 - phi) + 1 - phi) ** 2 / phi ** 2


def omega_s(rpm, dp):
    """Specific speed (dimensionless): radial < 1.5, mixed 1.5 .. 3, axial > 3 for best efficiency."""
    return (rpm * 2 * math.pi / 60) * math.sqrt(Q) / (dp / RHO) ** 0.75


v_core = Q / area(CORE_R)
v_grid = Q / area(GRID_R)
p_grid = perf_plate_K(GRID_PHI) * q(v_grid)
common = {"filter": P_FILTER, "core + bellmouth (0.15 q_core)": 0.15 * q(v_core)}

# --- A: plug fan (now): radial discharge into the lid, 90 deg turn, up through the grid
u_a = math.pi * 0.300 * 335 / 60
c_r = Q / (math.pi * 0.300 * 0.112)
c_u = 0.8 * (u_a - c_r * math.tan(math.radians(40)))      # slip factor 0.8
loss_a = dict(common)
loss_a["spider + motor in inflow (0.3 q_core)"] = 0.3 * q(v_core)
loss_a["turn in the lid (1.0 q of radial exit)"] = 1.0 * q(c_r)
loss_a["perforated top"] = p_grid
dp_a = sum(loss_a.values())
eta_a = 0.30            # plug fan, static-to-shaft, at this size and speed

# --- B: axial, 400 mm, hub 0.45, outlet guide vanes, in the lid, blowing up through the grid
D_b, hub_b = 0.400, 0.45
cx_b = Q / area(D_b / 2, hub_b * D_b / 2)
loss_b = dict(common)
loss_b["spider + motor in inflow (0.3 q_core)"] = 0.3 * q(v_core)
loss_b["expansion core -> fan annulus (0.2 q_annulus)"] = 0.2 * q(cx_b)
loss_b["perforated top"] = p_grid
loss_b["residual swirl after vanes (0.1 q_annulus)"] = 0.1 * q(cx_b)
dp_b = sum(loss_b.values())
eta_b = 0.45            # small axial with stator, total-to-shaft
phi_b, psi_b = 0.25, None
u_b = cx_b / phi_b
rpm_b = u_b / (math.pi * D_b) * 60
psi_b = dp_b / (RHO * u_b ** 2)

rows = []
for name, dp, eta, rpm, D in (("A plug fan + lid turn (now)", dp_a, eta_a, 335, 0.300),
                              ("B axial 400, outlet vanes", dp_b, eta_b, rpm_b, D_b)):
    w = Q * dp / eta
    torque = w / (rpm * 2 * math.pi / 60)
    rows.append((name, dp, rpm, math.pi * D * rpm / 60, omega_s(rpm, dp), eta, w, torque * 100 / 9.81))

if __name__ == "__main__":
    print(f"core velocity {v_core:.2f} m/s (q {q(v_core):.2f} Pa); grid approach {v_grid:.2f} m/s, "
          f"K {perf_plate_K(GRID_PHI):.2f}, loss {p_grid:.2f} Pa")
    print(f"A: radial exit c_r {c_r:.2f} m/s, swirl c_u {c_u:.2f} m/s, tip {u_a:.2f} m/s")
    print(f"B: annulus {cx_b:.2f} m/s, tip {u_b:.2f} m/s, phi {phi_b}, psi {psi_b:.3f}")
    for k, v in (("A", loss_a), ("B", loss_b)):
        print(k, {n: round(x, 2) for n, x in v.items()})
    print(f"{'option':30s} {'dp Pa':>6} {'rpm':>5} {'tip m/s':>7} {'Os':>5} {'eta':>4} {'shaft W':>7} {'kg cm':>6}")
    for r in rows:
        print(f"{r[0]:30s} {r[1]:6.2f} {r[2]:5.0f} {r[3]:7.2f} {r[4]:5.2f} {r[5]:4.2f} {r[6]:7.2f} {r[7]:6.2f}")
