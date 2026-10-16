"""Inspect NASA MOSFET thermal overstress MAT v5 files in a ZIP without bulk extraction."""
from __future__ import annotations

import json
import math
import re
import struct
import sys
import zipfile
import zlib
from collections import Counter

MAT_ZIP = sys.argv[1]

DTYPES = {
    1: ("b", 1), 2: ("B", 1), 3: ("h", 2), 4: ("H", 2),
    5: ("i", 4), 6: ("I", 4), 7: ("f", 4), 9: ("d", 8),
    12: ("q", 8), 13: ("Q", 8), 16: ("B", 1),
}
CLASSES = {1: "cell", 2: "struct", 3: "object", 4: "char", 5: "sparse",
           6: "double", 7: "single", 8: "int8", 9: "uint8", 10: "int16",
           11: "uint16", 12: "int32", 13: "uint32", 14: "int64", 15: "uint64"}


def element(buf, pos, endian="<"):
    if pos + 8 > len(buf):
        raise ValueError(f"truncated tag at {pos} of {len(buf)}")
    first, second = struct.unpack_from(endian + "II", buf, pos)
    small_size = first >> 16
    if small_size:
        typ, size = first & 0xffff, small_size
        start, end = pos + 4, pos + 4 + size
        nxt = pos + 8
    else:
        typ, size = first, second
        start, end = pos + 8, pos + 8 + size
        nxt = start + ((size + 7) // 8) * 8
    if end > len(buf):
        raise ValueError(f"element extends past buffer: type={typ}, size={size}")
    return typ, memoryview(buf)[start:end], nxt


def arr_int(data, code, endian="<"):
    width = struct.calcsize(code)
    n = len(data) // width
    return list(struct.unpack(endian + str(n) + code, data[:n * width])) if n else []


def parse_matrix(payload, endian="<", maxdepth=8, depth=0, collect_settings=False):
    p = 0
    typ, flags, p = element(payload, p, endian)
    flags = arr_int(flags, "I", endian)
    cls = (flags[0] & 0xff) if flags else 0
    typ, dims_raw, p = element(payload, p, endian)
    dims = arr_int(dims_raw, "i", endian)
    typ, name_raw, p = element(payload, p, endian)
    name = bytes(name_raw).decode("utf-8", "replace").rstrip("\0")
    out = {"name": name, "class": CLASSES.get(cls, f"class_{cls}"), "dims": dims}
    if cls == 2 and depth < maxdepth:
        typ, width_raw, p = element(payload, p, endian)
        width_vals = arr_int(width_raw, "i", endian)
        width = width_vals[0] if width_vals else 0
        typ, fields_raw, p = element(payload, p, endian)
        b = bytes(fields_raw)
        fields = [b[i:i + width].split(b"\0", 1)[0].decode("utf-8", "replace")
                  for i in range(0, len(b), width)] if width else []
        count = math.prod(dims) if dims else 1
        values, last_values = [], []
        # NASA's logged struct arrays serialize records consecutively. Keep
        # the first and last record, while consuming intermediate tags.
        values = [None] * len(fields)
        last_values = [None] * len(fields)
        observed = {field: [] for field in fields} if collect_settings else {}
        total = count * len(fields)
        for idx in range(total):
            typ, child_raw, p = element(payload, p, endian)
            field_idx = idx % len(fields)
            field_name = fields[field_idx]
            keep_first_or_last = idx < len(fields) or idx >= total - len(fields)
            collect_value = collect_settings and field_name in {
                "lowTemp", "highTemp", "shutdownTemp", "gateVoltage",
                "supplyVoltage", "switchingFrequency", "dutyCycle",
                "packageTemperature", "drainSourceVoltage", "drainCurrent",
                "flangeTemperature", "timeDomain", "date", "time",
            }
            if typ == 14 and (keep_first_or_last or collect_value):
                child = parse_matrix(child_raw, endian, maxdepth, depth + 1,
                                     collect_settings=(field_name == "pwmTempControllerState" or
                                                      (collect_settings and field_name in {"steadyState", "timeDomain"})))
                if collect_value:
                    samples = child.get("sample") or []
                    if samples and isinstance(samples[0], (int, float)):
                        observed[field_name].append(samples[0])
                    elif child.get("text") is not None:
                        observed[field_name].append(child["text"])
                    for nested_field, nested_values in child.get("observed_values", {}).items():
                        observed.setdefault(nested_field, []).extend(nested_values)
                if idx < len(fields):
                    values[field_idx] = child
                elif idx >= total - len(fields):
                    last_values[field_idx] = child
        values = [v or {"class": "missing"} for v in values]
        last_values = [v or {"class": "missing"} for v in last_values]
        out["fields"] = fields
        out["items"] = values
        out["last_items"] = last_values if count > 1 else []
        out["record_count"] = count
        if collect_settings:
            out["observed_values"] = observed
    elif cls == 1 and depth < maxdepth:
        count = math.prod(dims) if dims else 1
        vals = []
        for _ in range(min(count, 64)):
            typ, child_raw, p = element(payload, p, endian)
            vals.append(parse_matrix(child_raw, endian, maxdepth, depth + 1) if typ == 14 else {"class": f"element_{typ}"})
        out["items"] = vals
    else:
        if p < len(payload):
            typ, raw, p2 = element(payload, p, endian)
            out["dtype"] = typ
            out["data_bytes"] = len(raw)
            if cls == 4 and typ in (1, 2, 16):
                out["text"] = bytes(raw[:4096]).decode("utf-8", "replace").rstrip("\0")
            elif typ in DTYPES:
                code, width = DTYPES[typ]
                n = min(len(raw) // width, 12)
                vals = [v[0] for v in struct.iter_unpack(endian + code, raw[:n * width])]
                out["sample"] = vals
    return out


def matrices(buf, endian="<", collect_settings=False):
    p = 0
    while p + 8 <= len(buf):
        typ, raw, nxt = element(buf, p, endian)
        if typ == 14:
            yield parse_matrix(raw, endian, collect_settings=collect_settings)
        elif typ == 15:
            yield from matrices(zlib.decompress(raw), endian, collect_settings=collect_settings)
        if nxt <= p:
            break
        p = nxt


def shape(v):
    return "x".join(str(x) for x in v.get("dims", []))


def walk(v, path="", depth=0):
    name = v.get("name", "")
    here = f"{path}.{name}" if path and name else (name or path)
    yield {"path": here, "class": v.get("class"), "dims": v.get("dims"),
           "dtype": v.get("dtype"), "data_bytes": v.get("data_bytes"),
           "sample": v.get("sample"), "text": v.get("text")}
    fields = v.get("fields", [])
    items = v.get("items", [])
    for i, child in enumerate(items):
        fn = fields[i % len(fields)] if fields else str(i)
        # MATLAB struct child matrices generally have empty matrix names.
        c = dict(child)
        c["name"] = fn
        yield from walk(c, here, depth + 1)
    for i, child in enumerate(v.get("last_items", [])):
        fn = fields[i % len(fields)] if fields else str(i)
        c = dict(child)
        c["name"] = fn + "__last"
        yield from walk(c, here, depth + 1)


def compact(v):
    result = {k: v[k] for k in ("name", "class", "dims", "record_count", "dtype", "data_bytes", "sample", "text", "fields") if k in v}
    fields = v.get("fields", [])
    if fields:
        result["first"] = {f: compact(c) for f, c in zip(fields, v.get("items", []))}
        if v.get("last_items"):
            result["last"] = {f: compact(c) for f, c in zip(fields, v["last_items"])}
    return result


def main():
    out_path = sys.argv[2] if len(sys.argv) > 2 else None
    with zipfile.ZipFile(MAT_ZIP) as zf:
        names = [n for n in zf.namelist() if n.lower().endswith(".mat")]
        output = open(out_path, "w", encoding="utf-8") if out_path else sys.stdout
        try:
            for index, n in enumerate(names, 1):
                with zf.open(n) as fh:
                    header = fh.read(128)
                    endian = ">" if header[126:128] == b"MI" else "<"
                    fh.seek(128)
                    data = fh.read()
                vals = list(matrices(data, endian))
                tests = re.findall(r"Test_(\d+)_run_(\d+)", n, flags=re.I)
                entry = {"file": n, "bytes": zf.getinfo(n).file_size,
                         "test_id": int(tests[0][0]) if tests else None,
                         "run_id": int(tests[0][1]) if tests else None,
                         "variables": [compact(v) for v in vals]}
                output.write(json.dumps(entry, ensure_ascii=True, separators=(",", ":")) + "\n")
                output.flush()
                print(f"{index}/{len(names)} {n}", file=sys.stderr)
        finally:
            if out_path:
                output.close()


if __name__ == "__main__":
    main()
