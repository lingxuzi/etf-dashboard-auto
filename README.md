# ETF Dashboard Auto-Updater

本仓库基于你提供的“ETF 估值与性价比仪表盘（自动数据版）”，在 GitHub Actions 上定时抓取行情与估值数据，自动生成 `docs/assets.csv` 并通过 GitHub Pages 对外展示。

## 架构概览

- `config/indices.yaml`：25 个目标指数的元数据，包括行情代码、估值来源、ETF 代理。
- `scripts/`：抓数与加工流水线。
  - `fetch_cn_csindex.py`：调用 AKShare 的中证指数估值与行情接口。
  - `fetch_hk_hsi.py`：下载恒生官方网站 Factsheet（解析 PE/PB/Dividend Yield）并使用 Yahoo Finance 获取价格。
  - `fetch_us_yf.py`：使用 Yahoo Finance 指数行情与 ETF 股息率序列。
  - `compute_metrics.py`：合成估值百分位与近十年最大回撤。
  - `build_assets.py`：生成仪表盘读取的 `docs/assets.csv`。
- `data/`：存放抓取到的原始数据 (`raw/`) 与加工后的指标 (`processed/`)。
- `docs/`：GitHub Pages 静态站点（`index.html` + 最新 `assets.csv`）。
- `.github/workflows/update.yml`：定时工作流，每个交易日 18:30（UTC+8）自动更新。

## 本地运行

1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
2. 运行流水线：
   ```bash
   python scripts/fetch_cn_csindex.py
   python scripts/fetch_hk_hsi.py
   python scripts/fetch_us_yf.py
   python scripts/compute_metrics.py
   python scripts/build_assets.py
   ```
3. 本地预览（避免跨域）：
   ```bash
   python -m http.server 8000 --directory docs
   ```
   浏览器访问 `http://localhost:8000`.

> **注意**：抓数脚本依赖外部数据源，需要可访问互联网的环境。

## 数据抓取注意事项

- 中证指数估值接口依赖 `www.csindex.com.cn` / `oss-ch.csindex.com.cn`，部分网络环境会直接返回 403；如遇到该问题，请切换出口或暂时将对应指数的 `pe_source/pb_source/dp_source` 设为 `none`，让评分逻辑自动降权。
- 指标文件可能以 HTML / 旧式 Excel 等格式返回，脚本会尝试多种解析方式；仍失败时请在 `data/raw/cn_csi/` 查看 `*_valuation_missing.log`，确认文件内容后可在 `config/indices.yaml` 补充 `indicator_symbol` 或自行维护估值数据。
- 恒指 factsheet 路径调整频繁，可在配置中把 `factsheet_url` 改为列表，脚本会依次尝试；继续 404 时请到恒指官网查找最新链接并补充进去。
- 美股指数已默认在 `etf_proxies` 中包含 ETF 兜底符号（如 XLV），若主指数代码再次失效，可继续添加备用 ETF。

## 自动化部署

- GitHub Pages：在仓库 Settings → Pages 选择 `main` 分支 `/docs` 目录即可对外发布。
- 工作流会在有数据更新时提交 `docs/assets.csv` 与 `data/`，便于持续累积估值历史。

## 后续扩展

- 若恒生或 AKShare 接口结构变动，可在 `scripts/` 中调整解析逻辑。
- 可在 `config/indices.yaml` 补充 `etf_display` 字段，实现仪表盘展示更友好的 ETF 名称。
- 若需要额外指数，只需在配置表添加条目并重新运行流水线。
