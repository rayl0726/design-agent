from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import ezdxf
from ezdxf import bbox


class CADParser:
    async def parse(self, file_path: Path | str) -> dict[str, Any]:
        path = Path(file_path)
        doc = ezdxf.readfile(str(path))
        msp = doc.modelspace()

        extents = bbox.extents(msp)
        area = 0.0
        if extents.has_data:
            width = extents.extmax.x - extents.extmin.x
            height = extents.extmax.y - extents.extmin.y
            area = abs(width * height)

        columns = []
        for entity in msp:
            if entity.dxftype() == "CIRCLE":
                radius = entity.dxf.radius
                if 50 < radius < 500:
                    columns.append({
                        "type": "circle_column",
                        "center": [entity.dxf.center.x, entity.dxf.center.y],
                        "radius": radius,
                    })
            elif entity.dxftype() == "LWPOLYLINE":
                points = list(entity.get_points("xy"))
                if len(points) == 4:
                    xs = [p[0] for p in points]
                    ys = [p[1] for p in points]
                    w = max(xs) - min(xs)
                    h = max(ys) - min(ys)
                    if abs(w - h) < 50 and 100 < w < 1000:
                        columns.append({
                            "type": "rect_column",
                            "center": [(min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2],
                            "width": w,
                            "height": h,
                        })

        layers = [layer.dxf.name for layer in doc.layers]

        return {
            "source_type": "cad",
            "file_path": str(path),
            "format": "dxf",
            "area_estimate": round(area, 2) if area else None,
            "unit": doc.header.get("$INSUNITS", "unknown"),
            "layers": layers,
            "columns": columns,
            "entity_count": len(msp),
        }
