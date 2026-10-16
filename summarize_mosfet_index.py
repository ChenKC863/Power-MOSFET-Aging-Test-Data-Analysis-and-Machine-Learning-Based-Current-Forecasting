"""Build concise run/device summaries from analyze_mosfet_mat.py JSONL output."""
import json
import re
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


def first_num(obj):
    vals = obj.get("sample") or []
    return vals[0] if vals else None


def measurement_times(struct, time_field):
    if not struct:
        return None, None
    first = (struct.get("first") or {}).get(time_field) or {}
    last = (struct.get("last") or {}).get(time_field) or first
    return first.get("text"), last.get("text")


def parse_time(s):
    if not s:
        return None
    for fmt in ("%m/%d/%Y %H:%M:%S.%f", "%m/%d/%Y %H:%M:%S"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    return None


def subset(obj, keys):
    return {k: first_num(obj.get(k) or {}) for k in keys}


def main():
    index_path, out_path = map(Path, sys.argv[1:3])
    records = [json.loads(line) for line in index_path.read_text(encoding="utf-8").splitlines() if line]
    files = []
    groups = defaultdict(list)
    for rec in records:
        vars_ = rec.get("variables", [])
        root = vars_[0] if vars_ else {}
        meas = root.get("first", {})
        pwm = meas.get("pwmTempControllerState", {})
        transient = meas.get("transient", {})
        steady = meas.get("steadyState", {})
        pwm_first = pwm.get("first", {})
        pwm_last = pwm.get("last", {}) or pwm_first
        transient_td = ((transient.get("first") or {}).get("timeDomain") or {}).get("first", {})
        t0, t1 = measurement_times(pwm, "time")
        d0, d1 = measurement_times(transient, "date")
        s0, s1 = measurement_times(steady, "date")
        dt0 = parse_time(t0)
        dt1 = parse_time(t1)
        run = {
            "file": rec["file"].split("/", 1)[-1],
            "test_id": rec.get("test_id"),
            "run_id": rec.get("run_id"),
            "bytes": rec.get("bytes"),
            "filename_error_flag": "error" in rec["file"].lower(),
            "variable_names": [v.get("name") for v in vars_],
            "pwm_records": pwm.get("record_count"),
            "transient_records": transient.get("record_count"),
            "steady_records": steady.get("record_count"),
            "transient_dt_seconds": first_num(transient_td.get("dt") or {}),
            "transient_samples_per_channel": ((transient_td.get("gateSignalVoltage") or {}).get("dims") or [None, None])[-1],
            "start_time": t0,
            "end_time": t1,
            "start_datetime": dt0.isoformat(sep=" ") if dt0 else None,
            "end_datetime": dt1.isoformat(sep=" ") if dt1 else None,
            "transient_start": d0,
            "transient_end": d1,
            "steady_start": s0,
            "steady_end": s1,
            "duration_minutes": (dt1 - dt0).total_seconds() / 60 if dt0 and dt1 else None,
            "settings_first": subset(pwm_first, ["lowTemp", "highTemp", "shutdownTemp", "gateVoltage", "supplyVoltage", "switchingFrequency", "dutyCycle"]),
            "settings_last": subset(pwm_last, ["lowTemp", "highTemp", "shutdownTemp", "gateVoltage", "supplyVoltage", "switchingFrequency", "dutyCycle"]),
            "settings_observed": pwm.get("observed_values", {}),
            "steady_first": subset((steady.get("first") or {}).get("timeDomain", {}), ["supplyVoltage", "packageTemperature", "drainSourceVoltage", "drainCurrent", "flangeTemperature"]),
            "steady_last": subset((steady.get("last") or {}).get("timeDomain", {}), ["supplyVoltage", "packageTemperature", "drainSourceVoltage", "drainCurrent", "flangeTemperature"]),
            "transient_shape": {k: (v.get("dims") if v else None) for k, v in (((transient.get("first") or {}).get("timeDomain") or {}).get("first") or {}).items()},
        }
        files.append(run)
        if run["test_id"] is not None:
            groups[run["test_id"]].append(run)

    tests = []
    setting_keys = ["lowTemp", "highTemp", "shutdownTemp", "gateVoltage", "supplyVoltage", "switchingFrequency", "dutyCycle"]
    for test_id, runs in sorted(groups.items()):
        runs = sorted(runs, key=lambda x: (x["run_id"] or 0, x["filename_error_flag"], x["file"]))
        good = [r for r in runs if not r["filename_error_flag"]]
        all_times = [t for r in good for t in (parse_time(r["start_time"]), parse_time(r["end_time"])) if t]
        settings = {}
        for key in setting_keys:
            vals = [x for r in good for x in r.get("settings_observed", {}).get(key, [])]
            if not vals:
                vals = [r[k][key] for r in good for k in ("settings_first", "settings_last") if r[k].get(key) is not None]
            settings[key] = {"min_observed": min(vals) if vals else None,
                             "max_observed": max(vals) if vals else None,
                             "values_observed_all_controller_records": sorted(set(vals))}
        firsts = [r["settings_first"] for r in good if r["settings_first"]]
        lasts = [r["settings_last"] for r in good if r["settings_last"]]
        durations = [r["duration_minutes"] for r in good if r["duration_minutes"] is not None]
        tests.append({
            "test_id": test_id,
            "run_files": len(runs),
            "valid_named_runs": len(good),
            "run_ids": sorted({r["run_id"] for r in runs if r["run_id"] is not None}),
            "flagged_files": [r["file"] for r in runs if r["filename_error_flag"]],
            "start_time": min(all_times).isoformat(sep=" ") if all_times else None,
            "end_time": max(all_times).isoformat(sep=" ") if all_times else None,
            "sum_file_durations_minutes": round(sum(durations), 3),
            "sum_observed_file_durations_hours": round(sum(durations) / 60, 3),
            "transient_dt_seconds": sorted({r["transient_dt_seconds"] for r in good if r["transient_dt_seconds"] is not None}),
            "transient_samples_per_channel": sorted({r["transient_samples_per_channel"] for r in good if r["transient_samples_per_channel"] is not None}),
            "controller_settings_range": settings,
            "start_controller_settings": firsts[0] if firsts else {},
            "end_controller_settings": lasts[-1] if lasts else {},
        })

    dictionary = [
        {"field": "measurement", "matlab_type": "struct 1x1", "unit": "—", "meaning": "單一檔案的資料根節點；含控制器狀態、瞬態、穩態三個子結構。"},
        {"field": "measurement.pwmTempControllerState", "matlab_type": "struct array; each row is one controller-state record", "unit": "—", "meaning": "熱循環控制器狀態與設定；記錄數見檔案索引。"},
        {"field": "measurement.pwmTempControllerState.time", "matlab_type": "char 1x23", "unit": "local timestamp; timezone not encoded", "meaning": "控制器紀錄時間字串（月/日/年 時:分:秒.毫秒）。"},
        {"field": "measurement.pwmTempControllerState.timeEpoch", "matlab_type": "double scalar", "unit": "MATLAB datenum (days)", "meaning": "同筆紀錄的 MATLAB 日期序號。"},
        {"field": "measurement.pwmTempControllerState.nanosec_time", "matlab_type": "double scalar", "unit": "fractional second (s)", "meaning": "秒的小數部分；欄名雖為 nanosec_time，數值例如 0.93，並非以 ns 為單位。"},
        {"field": "measurement.pwmTempControllerState.lowTemp / highTemp / shutdownTemp", "matlab_type": "double scalar", "unit": "°C (inferred from field semantics and logged values)", "meaning": "低溫、高溫循環設定與控制器關機門檻。"},
        {"field": "measurement.pwmTempControllerState.gateVoltage / supplyVoltage", "matlab_type": "double scalar", "unit": "V (inferred from field semantics)", "meaning": "閘極與供電設定值。"},
        {"field": "measurement.pwmTempControllerState.switchingFrequency", "matlab_type": "double scalar", "unit": "Hz", "meaning": "功率循環切換頻率。"},
        {"field": "measurement.pwmTempControllerState.dutyCycle", "matlab_type": "double scalar", "unit": "%", "meaning": "切換訊號工作週期。"},
        {"field": "measurement.pwmTempControllerState.gateState", "matlab_type": "double scalar, logged as 0/1", "unit": "binary state", "meaning": "控制器記錄中的閘極狀態。不是失效標籤。"},
        {"field": "measurement.transient", "matlab_type": "struct array", "unit": "—", "meaning": "不連續擷取的高速瞬態波形；每一筆含時間戳及完整波形週期。"},
        {"field": "measurement.transient.date / timeEpoch / nanosec_time", "matlab_type": "char / double / double", "unit": "timestamp / MATLAB datenum / fractional second", "meaning": "瞬態波形快照的紀錄時間。"},
        {"field": "measurement.transient.timeDomain.dt", "matlab_type": "double scalar", "unit": "s", "meaning": "每個瞬態週期的取樣間隔；有效波形檔出現 0.2、0.25、1、2 μs。兩個檔案的波形陣列為空，dt=1 s 不應當成有效波形取樣率。"},
        {"field": "measurement.transient.timeDomain.gateSignalVoltage", "matlab_type": "double 1xN numeric array", "unit": "V (inferred)", "meaning": "瞬態閘極訊號波形；每通道點數為 500、1000 或 5000，兩個檔案為空陣列。"},
        {"field": "measurement.transient.timeDomain.gateSourceVoltage", "matlab_type": "double 1xN numeric array", "unit": "V (inferred)", "meaning": "瞬態閘源電壓波形；陣列長度會隨 run 設定改變。"},
        {"field": "measurement.transient.timeDomain.drainSourceVoltage", "matlab_type": "double 1xN numeric array", "unit": "V (inferred)", "meaning": "瞬態汲源電壓波形；陣列長度會隨 run 設定改變。"},
        {"field": "measurement.transient.timeDomain.drainCurrent", "matlab_type": "double 1xN numeric array", "unit": "A (inferred)", "meaning": "瞬態汲極電流波形；陣列長度會隨 run 設定改變。"},
        {"field": "measurement.steadyState", "matlab_type": "struct array", "unit": "—", "meaning": "較慢速、彙整後的穩態電熱量測。"},
        {"field": "measurement.steadyState.date / timeEpoch / nanosec_time", "matlab_type": "char / double / double", "unit": "timestamp / MATLAB datenum / fractional second", "meaning": "穩態量測時間。"},
        {"field": "measurement.steadyState.timeDomain.supplyVoltage", "matlab_type": "double scalar", "unit": "V", "meaning": "穩態供電電壓。"},
        {"field": "measurement.steadyState.timeDomain.packageTemperature / flangeTemperature", "matlab_type": "double scalar", "unit": "°C (inferred)", "meaning": "封裝與法蘭溫度。"},
        {"field": "measurement.steadyState.timeDomain.drainSourceVoltage", "matlab_type": "double scalar", "unit": "V", "meaning": "穩態汲源電壓。"},
        {"field": "measurement.steadyState.timeDomain.drainCurrent", "matlab_type": "double scalar", "unit": "A", "meaning": "穩態汲極電流。"},
        {"field": "failure label / event time", "matlab_type": "not present in common MAT schema", "unit": "—", "meaning": "原始 MATLAB 結構沒有明示失效旗標、失效時間、ΔRDS(on) 或停止原因欄位。"},
    ]
    out = {"archive": index_path.name, "mat_file_count": len(files), "test_group_count": len(tests), "files": files, "tests": tests, "dictionary": dictionary}
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"mat_file_count": len(files), "test_group_count": len(tests), "test_ids": [t["test_id"] for t in tests], "flagged": [r["file"] for r in files if r["filename_error_flag"]], "output": str(out_path)}, ensure_ascii=True))


if __name__ == "__main__":
    main()
