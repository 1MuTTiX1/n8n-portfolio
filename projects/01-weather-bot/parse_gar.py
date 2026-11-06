#!/usr/bin/env python3
"""
Экспорт адресных объектов ГАР (уровни 1..6) в CSV-файлы. БД не нужна.
Только стандартные библиотеки Python 3.8+.

    python parse_gar.py --gar C:\path\to\gar_xml --out C:\path\to\csv --merge

Результат: по одному файлу на регион (ru_locations_64.csv, ...).
Уже готовые регионы при повторном запуске пропускаются (--force пересоздаёт).
С --merge дополнительно собирается общий ru_locations_all.csv.

Ожидается структура: <gar>\\<код региона>\\AS_ADDR_OBJ_<дата>_<guid>.XML
                                          \\AS_ADM_HIERARCHY_<дата>_<guid>.XML
"""
import argparse
import csv
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

MAX_LEVEL = 6
ADDR_RE = re.compile(r"^AS_ADDR_OBJ_\d{8}_", re.I)
HIER_RE = re.compile(r"^AS_ADM_HIERARCHY_\d{8}_", re.I)
MUN_RE = re.compile(r"^AS_MUN_HIERARCHY_\d{8}_", re.I)
VN_PREFIX = re.compile(r"^(муниципальный округ|поселение|город)\s+", re.I)
HEADER = ["id", "gar_object_id", "parent_id", "region_id", "region_code",
          "name", "type_name", "gar_level", "kind"]


def iter_attrs(path, tag):
    """Потоковый разбор огромного XML: память не растёт."""
    ctx = ET.iterparse(path, events=("start", "end"))
    _, root = next(ctx)
    for ev, el in ctx:
        if ev == "end" and el.tag == tag:
            yield el.attrib
            root.clear()


def find_file(folder: Path, regex):
    for p in sorted(folder.iterdir()):
        if p.is_file() and regex.match(p.name):
            return p
    return None


def classify(level, type_name, parent_kind):
    t = (type_name or "").lower()
    if level == 1:
        return "region"
    if "внутригор" in t or "вн.тер" in t or "вн. тер" in t:
        return "city_district"
    if t == "р-н" and parent_kind in ("city", "city_district"):
        return "city_district"
    if t in ("г", "г.") or level == 5:
        return "city"
    if level in (2, 3):
        return "district"
    if level == 4:
        return "settlement"
    return "locality"


def read_region(region_dir: Path, region_code: int):
    addr_file = find_file(region_dir, ADDR_RE)
    hier_file = find_file(region_dir, HIER_RE)
    if not addr_file or not hier_file:
        return None

    objs = {}
    for a in iter_attrs(addr_file, "OBJECT"):
        if a.get("ISACTIVE", "1") != "1" or a.get("ISACTUAL", "1") != "1":
            continue
        lvl = int(a["LEVEL"])
        if lvl > MAX_LEVEL:
            continue
        objs[int(a["OBJECTID"])] = {
            "guid": a["OBJECTGUID"],
            "name": a["NAME"],
            "type": a.get("TYPENAME", ""),
            "level": lvl,
        }

    parent = {}
    for a in iter_attrs(hier_file, "ITEM"):
        if a.get("ISACTIVE", "1") != "1":
            continue
        oid = int(a["OBJECTID"])
        if oid in objs:
            parent[oid] = int(a["PARENTOBJID"])

    # Внутригородские территории (районы Москвы, СПб, Севастополя: тип «вн.тер.г.») есть только
    # в муниципальной иерархии, поэтому родителя для них берём оттуда.
    vn = {i for i, o in objs.items()
          if o["level"] in (3, 4) and i not in parent and "вн.тер" in o["type"].lower()}
    if vn:
        mun_file = find_file(region_dir, MUN_RE)
        if mun_file:
            for a in iter_attrs(mun_file, "ITEM"):
                if a.get("ISACTIVE", "1") != "1" or not a.get("PARENTOBJID"):
                    continue
                oid = int(a["OBJECTID"])
                if oid in vn:
                    parent[oid] = int(a["PARENTOBJID"])

    # Остальные уровни 3 и 4 (м.р-н, с.п., г.п., г.о.) относятся к муниципальной иерархии и
    # дублируют районы 2-го уровня. Оставляем их, только если родитель всё же нашёлся.
    for oid in [i for i, o in objs.items() if o["level"] in (3, 4) and i not in parent]:
        del objs[oid]
    for oid in [i for i in parent if i not in objs]:
        del parent[oid]

    kinds = {}
    for oid in sorted(objs, key=lambda i: objs[i]["level"]):
        o = objs[oid]
        kinds[oid] = classify(o["level"], o["type"], kinds.get(parent.get(oid)))

    def root_guid(oid):
        for _ in range(20):
            p = parent.get(oid)
            if p is None or p not in objs:
                break
            oid = p
        return objs[oid]["guid"]

    rows, orphans = [], 0
    for oid, o in objs.items():
        p = parent.get(oid)
        pguid = objs[p]["guid"] if p in objs else ""
        if not pguid and o["level"] > 1:
            orphans += 1
        name = VN_PREFIX.sub("", o["name"]) if "вн.тер" in o["type"].lower() else o["name"]
        rows.append([o["guid"], oid, pguid, root_guid(oid), region_code,
                     name, o["type"], o["level"], kinds[oid]])
    rows.sort(key=lambda r: (r[7], r[5]))
    return rows, orphans


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gar", required=True, help="папка gar_xml с подпапками регионов")
    ap.add_argument("--out", required=True, help="папка для CSV")
    ap.add_argument("--regions", help="коды регионов через запятую, по умолчанию все")
    ap.add_argument("--force", action="store_true", help="пересоздать уже готовые файлы")
    ap.add_argument("--merge", action="store_true", help="собрать общий ru_locations_all.csv")
    args = ap.parse_args()

    root, out = Path(args.gar), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    wanted = {int(x) for x in args.regions.split(",")} if args.regions else None
    folders = sorted(p for p in root.iterdir() if p.is_dir() and p.name.isdigit())
    if not folders:
        sys.exit(f"В {root} нет папок с кодами регионов (01, 02, ... 99). Проверьте путь.")

    total = 0
    for f in folders:
        code = int(f.name)
        if wanted and code not in wanted:
            continue
        target = out / f"ru_locations_{code:02}.csv"
        if target.exists() and not args.force:
            print(f"[{code:02}] уже есть {target.name}, пропуск")
            continue
        t0 = time.time()
        res = read_region(f, code)
        if res is None:
            print(f"[{code:02}] нет AS_ADDR_OBJ / AS_ADM_HIERARCHY, пропуск")
            continue
        rows, orphans = res
        tmp = target.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(HEADER)
            w.writerows(rows)
        tmp.replace(target)
        total += len(rows)
        print(f"[{code:02}] {len(rows):>7} объектов, без родителя: {orphans}, {time.time()-t0:.0f} c")

    if args.merge:
        merged = out / "ru_locations_all.csv"
        n = 0
        with open(merged, "w", encoding="utf-8", newline="") as dst:
            dst.write(",".join(HEADER) + "\n")
            for p in sorted(out.glob("ru_locations_[0-9][0-9].csv")):
                with open(p, "r", encoding="utf-8", newline="") as src:
                    next(src)
                    for line in src:
                        dst.write(line)
                        n += 1
        print(f"Общий файл: {merged} ({n} строк)")
    print(f"Готово. Новых записей: {total}")


if __name__ == "__main__":
    main()