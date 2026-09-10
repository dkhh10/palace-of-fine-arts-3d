import bpy
for name in ("ARCH_rotunda_vault_coffers_00","ARCH_rotunda_vault_00"):
    ob = bpy.data.objects[name]; me = ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).data; mw = ob.matrix_world
    big = []
    for p in me.polygons:
        c = mw @ p.center; n = (mw.to_3x3() @ p.normal).normalized()
        if p.area > 1.5:
            big.append((p.area, tuple(round(v,1) for v in c), tuple(round(v,2) for v in n), len(p.vertices)))
    big.sort(reverse=True)
    print(f"{name}: {len(me.polygons)} faces; faces over 1.5 m2: {len(big)}")
    for b in big[:12]: print("   area %.1f centre %s normal %s nverts %d" % b)
    # faces whose centre lies in the opening (x -6..0, y 15..20, z 18..22)
    mid = [p for p in me.polygons if (lambda c: -6 < c.x < 0 and 15 < c.y < 20.5 and 17.6 < c.z < 22.5)(mw @ p.center)]
    print(f"   faces with centre inside the opening band z 17.6-22.5: {len(mid)}, total area {sum(p.area for p in mid):.1f} m2")
    for p in mid[:6]:
        c = mw @ p.center; print("     ", round(p.area,2), tuple(round(v,1) for v in c), len(p.vertices))
