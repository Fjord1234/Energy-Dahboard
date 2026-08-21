# -*- coding: utf-8 -*-
"""Merge Jeju weather + generation into preprocessed CSV (2024-01-01 ~ 2025-12-31)."""

from __future__ import annotations

import os
import re
import warnings

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

FOLDER = os.path.dirname(os.path.abspath(__file__))
START, END = "2024-01-01", "2025-12-31"

# Unicode literals (avoid source-file encoding issues on Windows)
K_WIND_FILE = "\ubc14\ub78c"          # ??
K_SUN_FILE = "\uc77c\uc870"           # ??
K_SOLAR = "\ud0dc\uc591\uad11"        # ???
K_WIND_GEN = "\ud48d\ub825"           # ??
K_TOTAL = "\uc804\uccb4"              # ??
OUT_KO = "\uc804\ucc98\ub9ac\uc644\ub8cc.csv"  # ?????.csv
OUT_EN = "preprocessed_complete.csv"

PLANT_MAP = {
    "\uad50\ub798": "gyorae",           # ??
    "\uc885\ud569\uacbd\uae30\uc7a5": "stadium",  # ?????
    "\ud589\uc6d0": "haengwon",         # ??
    "\ud64d\ubcf4\uad00\uc8fc\ucc28\uc7a5": "promo_parking",  # ??????
    "\uc218\uc0b0": "susan",            # ??
    "\uac00\uc2dc\ub9ac": "gasiri",     # ???
    "\uae40\ub155": "gimnyeong",        # ??
    "\ub3d9\ubcf5": "dongbok",          # ??
    "\uc2e0\ucc3d": "sinchang",         # ??
}


def read_csv(path: str) -> pd.DataFrame:
    for enc in ("cp949", "euc-kr", "utf-8-sig", "utf-8"):
        try:
            return pd.read_csv(path, encoding=enc)
        except Exception:
            continue
    raise RuntimeError(f"Cannot read: {path}")


def clean_cols(cols) -> list:
    out = []
    for c in cols:
        s = str(c).replace("\t", "").replace('"', "").replace("'", "")
        s = re.sub(r"\s+", "", s).strip()
        out.append(s)
    return out


def to_date(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce").dt.normalize()


def coalesce_numeric(df: pd.DataFrame) -> pd.DataFrame:
    for c in df.columns:
        if c == "date":
            continue
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def find_by_substr(substr: str, suffix: str = ".csv") -> str:
    for name in os.listdir(FOLDER):
        if substr in name and name.endswith(suffix):
            return os.path.join(FOLDER, name)
    raise FileNotFoundError(f"No file containing {substr!r}")


def load_generation(keyword: str) -> pd.DataFrame:
    frames = []
    for name in sorted(os.listdir(FOLDER)):
        if not name.endswith(".csv"):
            continue
        if keyword not in name:
            continue
        if name in (OUT_KO, OUT_EN, "make_preprocessed.py"):
            continue
        path = os.path.join(FOLDER, name)
        df = read_csv(path)
        df.columns = clean_cols(df.columns)
        df = df.rename(columns={df.columns[0]: "date"})
        df["date"] = to_date(df["date"])
        df = df.dropna(subset=["date"])
        frames.append(df)
        print("gen:", name, len(df))
    if not frames:
        raise RuntimeError(f"No generation files for {keyword}")
    all_df = pd.concat(frames, ignore_index=True)
    all_df = all_df.sort_values("date").drop_duplicates("date", keep="last")
    return coalesce_numeric(all_df)


def rename_gen_columns(df: pd.DataFrame, kind: str) -> pd.DataFrame:
    mapping = {}
    for c in df.columns:
        if c == "date":
            mapping[c] = "date"
            continue
        if K_TOTAL in c:
            mapping[c] = f"{kind}_total_kwh"
            continue
        key = None
        for kor, eng in PLANT_MAP.items():
            if kor in c:
                key = eng
                break
        if key is None:
            key = f"site_{abs(hash(c)) % 10000}"
        mapping[c] = f"{kind}_{key}_kwh"

    renamed = df.rename(columns=mapping)
    # Coalesce duplicate target columns (quarterly header variants)
    pieces = {"date": renamed["date"]}
    for target in sorted(set(mapping.values()) - {"date"}):
        same = [c for c in renamed.columns if c == target]
        if not same:
            continue
        if len(same) == 1:
            pieces[target] = renamed[same[0]]
        else:
            block = renamed.loc[:, same]
            # duplicate labels -> iloc by positions
            idxs = [i for i, c in enumerate(renamed.columns) if c == target]
            block = renamed.iloc[:, idxs]
            pieces[target] = block.bfill(axis=1).iloc[:, 0]
    out = pd.DataFrame(pieces)
    return out


def main():
    wind_path = find_by_substr(K_WIND_FILE)
    sun_path = find_by_substr(K_SUN_FILE)
    temp_path = None
    for name in os.listdir(FOLDER):
        if name.startswith("extremum") and name.endswith(".xls"):
            temp_path = os.path.join(FOLDER, name)
            break
    if temp_path is None:
        raise FileNotFoundError("extremum xls not found")

    print("wind weather:", os.path.basename(wind_path))
    print("sunshine:", os.path.basename(sun_path))
    print("temperature:", os.path.basename(temp_path))

    # Wind weather
    wind_w = read_csv(wind_path)
    wind_w.columns = clean_cols(wind_w.columns)
    wind_w = wind_w.rename(columns={wind_w.columns[0]: "date"})
    wind_w["date"] = to_date(wind_w["date"])
    wind_cols = [c for c in wind_w.columns if c != "date"]
    pos_w = [
        "wind_avg_ms",
        "wind_max_ms",
        "wind_max_dir_deg",
        "wind_max_time",
        "wind_gust_ms",
        "wind_gust_dir_deg",
        "wind_gust_time",
    ]
    rename_w = {c: pos_w[i] if i < len(pos_w) else f"wind_extra_{i}" for i, c in enumerate(wind_cols)}
    rename_w["date"] = "date"
    wind_w = wind_w.rename(columns=rename_w)
    keep_w = ["date", "wind_avg_ms", "wind_max_ms", "wind_gust_ms"]
    wind_w = coalesce_numeric(wind_w[keep_w]).drop_duplicates("date", keep="last")

    # Sunshine
    sun = read_csv(sun_path)
    sun.columns = clean_cols(sun.columns)
    sun = sun.rename(columns={sun.columns[0]: "date"})
    sun["date"] = to_date(sun["date"])
    sun_cols = [c for c in sun.columns if c != "date"]
    pos_s = ["sunshine_hr", "sunshine_rate_pct", "solar_radiation_mj_m2"]
    rename_s = {c: pos_s[i] if i < len(pos_s) else f"sun_extra_{i}" for i, c in enumerate(sun_cols)}
    rename_s["date"] = "date"
    sun = sun.rename(columns=rename_s)
    keep_s = ["date", "sunshine_hr", "sunshine_rate_pct", "solar_radiation_mj_m2"]
    sun = coalesce_numeric(sun[keep_s]).drop_duplicates("date", keep="last")

    # Temperature
    temp = pd.read_csv(temp_path, sep="\t", encoding="cp949")
    temp.columns = clean_cols(temp.columns)
    temp = temp.rename(columns={temp.columns[0]: "date"})
    temp["date"] = to_date(temp["date"])
    t_cols = [c for c in temp.columns if c != "date"]
    pos_t = ["temp_avg_c", "temp_max_c", "temp_max_time", "temp_min_c", "temp_min_time"]
    rename_t = {c: pos_t[i] if i < len(pos_t) else f"temp_extra_{i}" for i, c in enumerate(t_cols)}
    rename_t["date"] = "date"
    temp = temp.rename(columns=rename_t)
    keep_t = ["date", "temp_avg_c", "temp_max_c", "temp_min_c"]
    temp = coalesce_numeric(temp[keep_t]).drop_duplicates("date", keep="last")

    solar = rename_gen_columns(load_generation(K_SOLAR), "solar")
    wind_g = rename_gen_columns(load_generation(K_WIND_GEN), "wind")
    solar = coalesce_numeric(solar)
    wind_g = coalesce_numeric(wind_g)

    def fill_total(df: pd.DataFrame, kind: str) -> pd.DataFrame:
        total_col = f"{kind}_total_kwh"
        plant_cols = [c for c in df.columns if c.startswith(f"{kind}_") and c.endswith("_kwh") and c != total_col]
        if not plant_cols:
            return df
        if total_col not in df.columns:
            df[total_col] = df[plant_cols].sum(axis=1, min_count=1)
        else:
            missing = df[total_col].isna()
            df.loc[missing, total_col] = df.loc[missing, plant_cols].sum(axis=1, min_count=1)
        return df

    solar = fill_total(solar, "solar")
    wind_g = fill_total(wind_g, "wind")

    calendar = pd.DataFrame({"date": pd.date_range(START, END, freq="D")})
    out = (
        calendar.merge(temp, on="date", how="left")
        .merge(wind_w, on="date", how="left")
        .merge(sun, on="date", how="left")
        .merge(solar, on="date", how="left")
        .merge(wind_g, on="date", how="left")
    )

    # If totals still missing after merge, recompute from plant columns
    for kind in ("solar", "wind"):
        total_col = f"{kind}_total_kwh"
        plant_cols = [c for c in out.columns if c.startswith(f"{kind}_") and c.endswith("_kwh") and c != total_col]
        if total_col in out.columns and plant_cols:
            missing = out[total_col].isna()
            out.loc[missing, total_col] = out.loc[missing, plant_cols].sum(axis=1, min_count=1)

    preferred = [
        "date",
        "temp_avg_c",
        "temp_max_c",
        "temp_min_c",
        "wind_avg_ms",
        "wind_max_ms",
        "wind_gust_ms",
        "sunshine_hr",
        "sunshine_rate_pct",
        "solar_radiation_mj_m2",
        "solar_total_kwh",
        "wind_total_kwh",
    ]
    plant_cols = sorted(
        c for c in out.columns
        if c.endswith("_kwh") and c not in preferred
    )
    # drop duplicate-named columns if any remain
    out = out.loc[:, ~out.columns.duplicated()]
    ordered = [c for c in preferred if c in out.columns] + [
        c for c in plant_cols if c in out.columns and c not in preferred
    ]
    out = out[ordered].sort_values("date").reset_index(drop=True)
    out["date"] = out["date"].dt.strftime("%Y-%m-%d")

    out_ko = os.path.join(FOLDER, OUT_KO)
    out_en = os.path.join(FOLDER, OUT_EN)
    out.to_csv(out_ko, index=False, encoding="utf-8-sig")
    out.to_csv(out_en, index=False, encoding="utf-8-sig")

    print("saved:", out_ko)
    print("saved:", out_en)
    print("rows:", len(out))
    print("cols:", list(out.columns))
    for c in preferred[1:]:
        if c in out.columns:
            s = pd.to_numeric(out[c], errors="coerce")
            print(f"  {c}: non-null={int(s.notna().sum())}/{len(s)}")
    if "solar_total_kwh" in out.columns:
        miss = out.loc[pd.to_numeric(out["solar_total_kwh"], errors="coerce").isna(), "date"]
        print("solar missing days:", len(miss))
        if len(miss):
            print("  first/last:", miss.iloc[0], miss.iloc[-1])
    if "wind_total_kwh" in out.columns:
        wmiss = out.loc[pd.to_numeric(out["wind_total_kwh"], errors="coerce").isna(), "date"]
        print("wind missing days:", len(wmiss))


if __name__ == "__main__":
    main()
