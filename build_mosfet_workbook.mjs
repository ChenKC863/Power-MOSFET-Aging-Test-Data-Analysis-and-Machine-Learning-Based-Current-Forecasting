import fs from "node:fs/promises";
import path from "node:path";
import { Workbook, SpreadsheetFile } from "@oai/artifact-tool";

const root = process.cwd();
const data = JSON.parse(await fs.readFile(path.join(root, "mosfet_analysis.json"), "utf8"));
const workbook = Workbook.create();
const navy = "#20364D";
const blue = "#1F4E78";
const pale = "#EAF0F6";

const colName = (n) => {
  let s = "";
  while (n > 0) {
    const r = (n - 1) % 26;
    s = String.fromCharCode(65 + r) + s;
    n = Math.floor((n - 1) / 26);
  }
  return s;
};
const nval = (o, k) => (o && o[k] !== undefined ? o[k] : null);
const valuesList = (setting) => (setting?.values_observed_all_controller_records || []).join(", ");
const rangeText = (setting) => {
  if (setting?.min_observed == null) return "";
  const a = setting.min_observed;
  const b = setting.max_observed;
  return a === b ? String(a) : `${a}–${b}`;
};
function addStyledTable(name, title, subtitle, headers, rows, tableName, widths, freezeCols = 0) {
  const sheet = workbook.worksheets.add(name);
  sheet.showGridLines = false;
  sheet.tabColor = blue;
  sheet.getRange("A2").values = [[title]];
  sheet.getRange("A2").format = { font: { bold: true, color: navy, size: 14 }, verticalAlignment: "center" };
  sheet.getRange("A3").values = [[subtitle]];
  sheet.getRange("A3").format = { font: { italic: true, color: "#526477", size: 10 }, wrapText: false, verticalAlignment: "center" };
  sheet.getRange("A3").format.rowHeight = 20;
  const lastCol = colName(headers.length);
  const headerRow = 5;
  const endRow = headerRow + rows.length;
  const values = [headers, ...rows];
  sheet.getRange(`A${headerRow}:${lastCol}${endRow}`).values = values;
  sheet.getRange(`A${headerRow}:${lastCol}${headerRow}`).format = {
    fill: blue,
    font: { bold: true, color: "#FFFFFF", size: 10 },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
  };
  sheet.getRange(`A${headerRow}:${lastCol}${endRow}`).format.verticalAlignment = "center";
  sheet.getRange(`A${headerRow + 1}:${lastCol}${endRow}`).format.font = { name: "Arial", size: 10, color: "#263746" };
  for (const [col, width] of Object.entries(widths)) sheet.getRange(`${col}:${col}`).format.columnWidth = width;
  sheet.getRange(`A${headerRow}:${lastCol}${headerRow}`).format.rowHeight = 32;
  const table = sheet.tables.add(`A${headerRow}:${lastCol}${endRow}`, true, tableName);
  table.showFilterButton = true;
  sheet.freezePanes.freezeRows(headerRow);
  if (freezeCols) sheet.freezePanes.freezeColumns(freezeCols);
  return sheet;
}

// Overview and scope notes.
const overview = workbook.worksheets.add("概覽");
overview.showGridLines = false;
overview.tabColor = navy;
const observedHours = data.files.reduce((s, f) => s + (f.duration_minutes || 0), 0) / 60;
const coverageStart = [...data.files].map((f) => f.start_datetime).filter(Boolean).sort()[0];
const coverageEnd = [...data.files].map((f) => f.end_datetime).filter(Boolean).sort().at(-1);
overview.getRange("A2:B2").values = [["MOSFET 熱過應力老化資料盤點", "NASA PCoE 資料集 13；本地 ZIP 檔案分析"]];
overview.getRange("A2:B2").format = { font: { bold: true, color: navy, size: 14 }, verticalAlignment: "center" };
overview.getRange("A4:B10").values = [
  ["盤點指標", "結果"],
  ["MAT 檔案數", data.mat_file_count],
  ["檔名 Test ID 群組", data.test_group_count],
  ["資料涵蓋期間", `${coverageStart?.slice(0, 10) ?? ""} 至 ${coverageEnd?.slice(0, 10) ?? ""}`],
  ["檔內首末時間差合計", `${observedHours.toFixed(2)} 小時（每檔首末時間差相加；不等於確認的通電老化時數）`],
  ["需注意檔案", `${data.files.filter((f) => f.filename_error_flag).length} 個檔名帶有 setup error 註記；${data.files.filter((f) => f.transient_samples_per_channel === 0).length} 個檔案的瞬態波形陣列為空；另有 ${data.files.filter((f) => f.test_id == null).length} 個檔案不符合 Test/run 命名模式。`],
  ["失效標籤", "MAT 共通結構未見明確 failure flag、事件時間、停止原因或 ΔRDS(on) 欄位。"],
];
overview.getRange("A4:B4").format = { fill: blue, font: { bold: true, color: "#FFFFFF" }, verticalAlignment: "center" };
overview.getRange("A4:B10").format.verticalAlignment = "center";
overview.getRange("A5:A10").format.font = { bold: true, color: navy, size: 10 };
overview.getRange("B5:B10").format = { font: { name: "Arial", size: 10, color: "#263746" }, wrapText: true, verticalAlignment: "center" };
overview.getRange("A:A").format.columnWidth = 25;
overview.getRange("B:B").format.columnWidth = 104;
overview.getRange("A12:B18").values = [
  ["讀取與詮釋重點", "說明"],
  ["Test ID 與元件 ID", "檔名提供 Test_1 至 Test_42，並以 run 編號切分資料。表內將其稱為 Test ID 群組；未將其提升為實體序號，除非資料集文件明確建立一對一映射。"],
  ["老化設定", "lowTemp/highTemp 是控制器記錄的循環設定，會隨測試階段改變。元件條件表的範圍／值清單彙總每筆控制器紀錄；檔案索引另列各 run 首末值。"],
  ["觀測時間", "時間保留 MAT 內原始年月日時字串並轉成 ISO 樣式；資料沒有時區欄位。run 之間可能有中斷，跨檔涵蓋期不可直接當成持續通電時間。"],
  ["量測結構", "每個檔案根節點為 measurement，含 pwmTempControllerState、transient、steadyState。檔案索引列出各子結構的紀錄數。"],
  ["失效判定", "NASA 文獻的 ΔRDS(on)=0.045 是預後模型採用的門檻；本地 MAT 未直接儲存 ΔRDS(on) 或失效標籤。若使用此門檻，應稱為模型推導的門檻穿越時間，並核對資料版本與正規化方式。"],
  ["Setup error 檔案", "Test_13_run_1 1 (error setting up this run).mat 檔名帶 setup error 註記；它仍含可解析的量測記錄，因此在索引中保留、標記，建模前應人工判讀是否納入。"],
];
overview.getRange("A12:B12").format = { fill: blue, font: { bold: true, color: "#FFFFFF" }, verticalAlignment: "center" };
overview.getRange("A13:A18").format.font = { bold: true, color: navy, size: 10 };
overview.getRange("B13:B18").format = { font: { name: "Arial", size: 10, color: "#263746" }, wrapText: true, verticalAlignment: "center" };
overview.getRange("A12:A18").format.rowHeight = 32;
overview.freezePanes.freezeRows(4);

// Per Test-ID condition table.
const testHeaders = ["Test ID", "MAT 檔數", "Run ID", "資料涵蓋起點", "資料涵蓋終點", "檔內首末時間差合計 (h)", "lowTemp 完整記錄範圍 (°C)", "highTemp 完整記錄範圍 (°C)", "shutdownTemp 記錄值 (°C)", "gateVoltage 記錄值 (V)", "supplyVoltage 記錄值 (V)", "switchingFrequency 記錄值 (Hz)", "dutyCycle 記錄值 (%)", "瞬態 dt 值 (s)", "每通道波形點數", "檔名異常註記"];
const testRows = data.tests.map((t) => {
  const s = t.controller_settings_range;
  return [t.test_id, t.run_files, t.run_ids.join(", "), t.start_time, t.end_time,
    t.sum_observed_file_durations_hours,
    rangeText(s.lowTemp), rangeText(s.highTemp), valuesList(s.shutdownTemp),
    valuesList(s.gateVoltage), valuesList(s.supplyVoltage), valuesList(s.switchingFrequency),
    valuesList(s.dutyCycle), t.transient_dt_seconds.join(", "), t.transient_samples_per_channel.join(", "), t.flagged_files.join("; ")];
});
addStyledTable("元件條件", "Test ID 老化條件與量測涵蓋", "溫度與電氣設定範圍／值清單統計每筆控制器紀錄；時間戳無時區，檔內首末時間差相加不是實際通電老化時數。瞬態取樣間隔與陣列長度會隨 run 改變。", testHeaders, testRows, "TestConditions", {
  A: 10, B: 10, C: 16, D: 22, E: 22, F: 22, G: 22, H: 22, I: 18, J: 18, K: 20, L: 22, M: 18, N: 22, O: 22, P: 48,
});

// Per-file inventory.
const fileHeaders = ["Test ID", "Run ID", "MAT 檔名", "檔案大小 (MB)", "起始時間", "結束時間", "檔內首末時間差 (min)", "控制器紀錄數", "瞬態紀錄數", "穩態紀錄數", "lowTemp 起始 (°C)", "lowTemp 結束 (°C)", "highTemp 起始 (°C)", "highTemp 結束 (°C)", "shutdownTemp 起始 (°C)", "shutdownTemp 結束 (°C)", "gateVoltage 起始 (V)", "gateVoltage 結束 (V)", "supplyVoltage 起始 (V)", "supplyVoltage 結束 (V)", "switchingFrequency 起始 (Hz)", "switchingFrequency 結束 (Hz)", "dutyCycle 起始 (%)", "dutyCycle 結束 (%)", "瞬態 dt (s)", "每通道波形點數", "檔名旗標", "波形陣列狀態"];
const fileRows = [...data.files].sort((a, b) => (a.test_id ?? 999) - (b.test_id ?? 999) || (a.run_id ?? 999) - (b.run_id ?? 999) || a.file.localeCompare(b.file)).map((f) => [
  f.test_id, f.run_id, f.file, f.bytes / 1048576, f.start_time, f.end_time, f.duration_minutes,
  f.pwm_records, f.transient_records, f.steady_records,
  nval(f.settings_first, "lowTemp"), nval(f.settings_last, "lowTemp"),
  nval(f.settings_first, "highTemp"), nval(f.settings_last, "highTemp"),
  nval(f.settings_first, "shutdownTemp"), nval(f.settings_last, "shutdownTemp"),
  nval(f.settings_first, "gateVoltage"), nval(f.settings_last, "gateVoltage"),
  nval(f.settings_first, "supplyVoltage"), nval(f.settings_last, "supplyVoltage"),
  nval(f.settings_first, "switchingFrequency"), nval(f.settings_last, "switchingFrequency"),
  nval(f.settings_first, "dutyCycle"), nval(f.settings_last, "dutyCycle"),
  f.transient_dt_seconds, f.transient_samples_per_channel,
  f.filename_error_flag ? "檔名含 error setting up this run" : f.test_id == null ? "檔名未包含 Test_ID/run_ID 模式" : "",
  f.transient_samples_per_channel === 0 ? "四通道皆為空陣列；dt 不適用" : "有波形點",
]);
const filesSheet = addStyledTable("MAT檔案索引", "MAT 檔案逐檔索引", "所有 106 個 MAT 檔的巢狀欄位結構一致；設定欄位為該檔首末控制器記錄。setup error 檔與空波形檔保留並分別標記。", fileHeaders, fileRows, "MatFileInventory", {
  A: 10, B: 10, C: 58, D: 16, E: 22, F: 22, G: 20, H: 17, I: 17, J: 17,
  K: 17, L: 17, M: 17, N: 17, O: 19, P: 19, Q: 19, R: 19, S: 20, T: 20,
  U: 25, V: 25, W: 19, X: 19, Y: 20, Z: 20, AA: 35, AB: 32,
}, 3);
filesSheet.getRange(`D6:D${fileRows.length + 5}`).setNumberFormat("0.00");
filesSheet.getRange(`G6:G${fileRows.length + 5}`).setNumberFormat("0.00");

// Data dictionary.
const dictHeaders = ["MAT 欄位路徑", "MATLAB 型別／形狀", "單位", "意義", "分析注意事項"];
const dictRows = data.dictionary.map((d) => {
  let caut = "";
  if (d.field.includes("nanosec_time")) caut = "欄名與數值尺度不一致；數值如 0.93，是秒的小數部分，勿當成奈秒。";
  else if (d.field.endsWith(".dt")) caut = "有效波形檔之間取樣間隔不同；空波形檔中的 dt=1 s 是無效佔位值。";
  else if (d.field.includes("gateSignalVoltage") || d.field.includes("gateSourceVoltage") || d.field.includes("drainSourceVoltage") || d.field.includes("drainCurrent") && d.field.includes("transient")) caut = "每通道陣列點數有 500、1000、5000 三種；Test_2_run_2、Test_40_run_2 為空陣列。";
  else if (d.field.includes("gateState")) caut = "0/1 控制狀態，不等於故障旗標。";
  else if (d.field.includes("timeEpoch")) caut = "MATLAB datenum，以天為單位；報告用 time/date 字串保留原貌。";
  else if (d.field.includes("failure label")) caut = "未發現明示欄位；需以文獻門檻衍生標籤時，應說明推導步驟。";
  else if (d.unit.includes("inferred")) caut = "單位依欄名、數值與文獻語境推定；NASA 資料集參考文件目前離線。";
  return [d.field, d.matlab_type, d.unit, d.meaning, caut];
});
const dictSheet = addStyledTable("資料字典", "MAT 資料字典", "型別與形狀依本次解析的 MAT v5 結構；欄位單位若無原始資料字典佐證，已標示為推定。", dictHeaders, dictRows, "MatDataDictionary", {
  A: 62, B: 46, C: 36, D: 64, E: 64,
});
dictSheet.getRange(`D6:E${dictRows.length + 5}`).format.wrapText = true;
dictSheet.getRange(`D6:E${dictRows.length + 5}`).format.autofitRows();

// Physical failure modes vs. prognostic threshold vs. raw data availability.
const failureHeaders = ["層次", "定義／判據", "與本地 MAT 的關係", "使用限制", "來源"];
const failureRows = [
  ["NASA 資料集定位", "NASA PCoE 將第 13 項資料集描述為功率 MOSFET 熱過應力 run-to-failure 實驗。", "與檔案目錄一致：Test_1–Test_42，含多個 run 檔。", "NASA 資料集參考文件目前標示離線；本地檔名 Test ID 不能自動等同經驗證的實體序號。", "https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/"],
  ["主要劣化機制", "NASA 文獻指出主要失效機制為 die-attach degradation；ON-state resistance 增加可作為先兆。", "原始結構未見 RDS(on) 或 ΔRDS(on) 欄位；可由瞬態 VDS、ID 在有效 ON 區間推導。", "要先處理閘極 ON 判定、除零／低電流、溫度效應與每顆元件 pristine 基準正規化。", "https://data.nasa.gov/dataset/prognostics-of-power-mosfets-under-thermal-stress-accelerated-aging-using-data-driven-and-"],
  ["物理失效條件", "相關 NASA RAMS 論文列出 latch-up、thermal run-away、或因 gate control loss 而無法 turn ON。", "共通 MAT schema 沒有明示的實際失效事件、失效時間或停止原因欄位。", "若從波形辨認事件，仍需建立並驗證明確事件判讀規則；不得僅以最後一筆資料視為失效。", "https://ntrs.nasa.gov/api/citations/20140010629/downloads/20140010629.pdf?attachment=true"],
  ["NASA 預後模型門檻", "該論文採用 ΔRDS(on)=0.045 作為 crisp failure threshold。", "MAT 檔未直接儲存 ΔRDS(on)；此值不是原始欄位，也不是本地檔自帶的 failure label。", "只可稱為依論文作法導出的 threshold crossing；採用前需確認資料版本、基準與正規化定義相符。", "https://ntrs.nasa.gov/api/citations/20140010629/downloads/20140010629.pdf?attachment=true"],
];
const failureSheet = addStyledTable("失效定義", "失效模式與可用標籤", "區分物理失效、論文中的預後門檻，以及原始 MAT 有沒有事件標註。", failureHeaders, failureRows, "FailureDefinitions", {
  A: 22, B: 78, C: 68, D: 76, E: 82,
});
failureSheet.getRange(`B6:E${failureRows.length + 5}`).format.wrapText = true;
failureSheet.getRange(`B6:E${failureRows.length + 5}`).format.autofitRows();

workbook.recalculate();
const outPath = path.join(root, "MOSFET_熱過應力資料盤點.xlsx");
const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outPath);

const inspection = await workbook.inspect({ kind: "workbook,sheet,table", maxChars: 6000, tableMaxRows: 3, tableMaxCols: 5, tableMaxCellChars: 80 });
console.log(JSON.stringify({ output: outPath, sheets: workbook.worksheets.items.map((s) => s.name), inspection: inspection.ndjson }));
const preview = await workbook.render({ sheetName: "元件條件", autoCrop: "all", scale: 0.8, format: "png" });
await fs.writeFile(path.join(root, "mosfet_workbook_preview.png"), new Uint8Array(await preview.arrayBuffer()));
for (const sheetName of ["概覽", "資料字典", "失效定義"]) {
  const p = await workbook.render({ sheetName, autoCrop: "all", scale: 0.8, format: "png" });
  await fs.writeFile(path.join(root, `mosfet_preview_${sheetName}.png`), new Uint8Array(await p.arrayBuffer()));
}
