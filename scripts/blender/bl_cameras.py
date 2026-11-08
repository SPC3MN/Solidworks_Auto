"""Camera presets with exact framing.

The camera looks at the target box centre from (az, el). For a perspective camera the
distance is solved exactly so every corner of the box fits inside the frame with the
requested margin; for an orthographic camera the ortho scale is solved the same way.
"""
import math

import bpy
from mathutils import Vector

import bl_stage as ST
import bl_util as U

SENSOR = 36.0


def target_box(box, target, objects_by_key):
    lo, hi = box
    if not target or target == "product":
        return lo, hi
    if target.startswith("region:"):
        r = target.split(":", 1)[1]
        lo, hi = lo.copy(), hi.copy()
        q = (hi - lo) * 0.3
        if r == "top":
            lo.z = hi.z - q.z
        elif r == "bottom":
            hi.z = lo.z + q.z
        elif r == "front":
            hi.y = lo.y + q.y
        elif r == "left":
            hi.x = lo.x + q.x
        elif r == "right":
            lo.x = hi.x - q.x
        return lo, hi
    if target.startswith("component:"):
        key = target.split(":", 1)[1]
        ob = objects_by_key.get(key)
        if ob is None:
            U.log(f"camera target {key} not found, framing the product")
            return lo, hi
        return U.exact_world_bbox(ob)
    return lo, hi


def corners(lo, hi):
    return [Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]


def make(name, spec, box, aspect, coll, objects_by_key=None, product_box=None):
    """Create a camera object. spec = preset merged with overrides. aspect = width / height."""
    tlo, thi = target_box(box, spec.get("target"), objects_by_key or {})
    centre = (tlo + thi) / 2 + Vector((0, 0, spec.get("target_offset_z", 0.0) * (thi - tlo).z))
    fwd = -ST.direction(spec.get("az", 35), spec.get("el", 20))  # camera -> target
    if abs(fwd.z) > 0.9999:
        up_hint = Vector((0, 1, 0))
    else:
        up_hint = Vector((0, 0, 1))
    right = fwd.cross(up_hint).normalized()
    up = right.cross(fwd).normalized()
    m = spec.get("margin", 0.1)
    data = bpy.data.cameras.new(name)
    data.sensor_fit = "HORIZONTAL" if aspect >= 1 else "VERTICAL"
    data.sensor_width = data.sensor_height = SENSOR
    pts = [p - centre for p in corners(tlo, thi)]
    if spec.get("type", "PERSP") == "ORTHO":
        data.type = "ORTHO"
        w = max(abs(p.dot(right)) for p in pts) * 2
        h = max(abs(p.dot(up)) for p in pts) * 2
        frame_w = max(w, h * aspect) / (1 - 2 * m)
        data.ortho_scale = frame_w if aspect >= 1 else frame_w / aspect
        if abs(spec.get("el", 0)) < 5:
            # elevation views: put the frame's bottom edge on the product base, so the camera
            # never sees below the floor (which renders as a band of a different tone)
            frame_h = data.ortho_scale / aspect if aspect >= 1 else data.ortho_scale
            data.shift_y = (frame_h - h) / 2 / data.ortho_scale
        diag = (thi - tlo).length
        dist = diag * 3 + 0.5
    else:
        data.type = "PERSP"
        data.lens = spec.get("focal_mm", 50)
        half = SENSOR / 2 / data.lens  # tan of half the fov on the fitted side
        tx, ty = (half, half / aspect) if aspect >= 1 else (half * aspect, half)
        tx, ty = tx * (1 - 2 * m), ty * (1 - 2 * m)
        dist = max(max(abs(p.dot(right)) / tx, abs(p.dot(up)) / ty) - p.dot(fwd) for p in pts)
    data.clip_start = max(dist * 0.01, 0.001)
    data.clip_end = dist * 50 + 10
    ob = bpy.data.objects.new(name, data)
    ob.location = centre - fwd * dist
    ST.aim(ob, centre)
    dof = spec.get("dof")
    if dof and data.type == "PERSP":
        data.dof.use_dof = True
        data.dof.aperture_fstop = dof.get("fstop", 8.0)
        data.dof.focus_distance = dist  # focus on the target centre
    coll.objects.link(ob)
    return ob


def framing_report(cam, scene, box):
    """Where the product box lands in the frame (0..1 coords): fill and any cropping."""
    from bpy_extras.object_utils import world_to_camera_view
    pts = [world_to_camera_view(scene, cam, p) for p in corners(*box)]
    xs, ys = [p.x for p in pts], [p.y for p in pts]
    behind = any(p.z <= 0 for p in pts)
    lo_x, hi_x, lo_y, hi_y = min(xs), max(xs), min(ys), max(ys)
    crop = behind or lo_x < -0.001 or lo_y < -0.001 or hi_x > 1.001 or hi_y > 1.001
    fill = max(0.0, min(hi_x, 1) - max(lo_x, 0)) * max(0.0, min(hi_y, 1) - max(lo_y, 0))
    return {"frame_x": [round(lo_x, 3), round(hi_x, 3)], "frame_y": [round(lo_y, 3), round(hi_y, 3)],
            "bbox_fill": round(fill, 3), "cropped": bool(crop)}
