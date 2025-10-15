# ETF 指数估值仪表盘（自动更新版）

这是一个自动化维护的 ETF 指数估值仪表盘。GitHub Actions 每个交易日抓取估值与行情数据，生成 `docs/assets.csv`，通过 GitHub Pages 暴露 `docs/index.html`，让访问者直接看到最新的打分结果。

## 项目速览

- 在线仪表盘（启用 GitHub Pages 后）：`https://<your-account>.github.io/etf_dashboard/`
- 更新频率：工作日北京时间 18:30 左右完成一次全量刷新
- 覆盖对象：A 股中证系列、恒生系列、美股核心指数及对应 ETF 代理

## 功能亮点

- 自动数据管线：`config/indices.yaml` 描述 25 个指数的行情与估值来源，`scripts/` 目录按顺序抓取并计算分位。
- 多市场覆盖：AKShare（中证估值）、恒指官网 Factsheet、Yahoo Finance 共同提供 A 股 / 港股 / 美股数据。
- 评分模型透明：PE、PB、股息率百分位 + 近十年最大回撤，一目了然衡量“贵或便宜”。
- 弹性降权：某些指标缺失时自动降权并归一，保证仪表盘始终可用。

## 快速上手

### 在线查看

1. 在仓库 Settings → Pages 启用 `main` 分支 `/docs` 目录。
2. 等待 Actions 生成最新 `docs/assets.csv`（首次部署可手动触发一次工作流）。
3. 访问 Pages 链接即可看到仪表盘，浏览器缓存可用 `Shift + F5` 强刷。

### 本地运行

```bash
pip install -r requirements.txt
python scripts/fetch_djeva.py
python scripts/fetch_cn_csindex.py
python scripts/fetch_hk_hsi.py
python scripts/fetch_us_yf.py
python scripts/compute_metrics.py
python scripts/build_assets.py
```

运行完成后，`docs/assets.csv` 会被刷新，随即可在本地或 Pages 上查看。

### 本地预览

```bash
python -m http.server 8000 --directory docs
```

打开浏览器访问 `http://localhost:8000`，即可模拟线上效果。

> 抓数脚本需要外网访问权限；如在 CI 或内网环境执行，请确保出口可访问相应数据源。

## 数据口径与限制

- **中证系指数**：AKShare 调用中证官网估值接口；若站点返回 403，可在配置里暂时将 `pe_source/pb_source/dp_source` 设为 `none`，脚本会自动降权。
- **恒生系列**：通过恒指官网 Factsheet PDF 抽取 PE/PB/Dividend Yield，补充 Yahoo Finance 行情；月度资料若暂未发布，会沿用上一次值。
- **美股指数**：使用 Yahoo Finance 指数行情，ETF 代理（如 SPY、QQQ、XLV）提供股息率序列。
- **缺失处理**：脚本会记录日志到 `data/raw/*`，必要时可手动补数据或新增 `indicator_symbol`。

## 自动化与部署

### GitHub Actions：`Update ETF dashboard data`

- 触发：工作日 UTC 10:30（北京时间 18:30）+ `workflow_dispatch`
- 步骤：Checkout → 安装依赖 → 执行抓数脚本 → 生成 `docs/assets.csv` → 提交更新
- 验证：在 Actions 页面手动触发一次，确认日志无误并检查 `docs/assets.csv` 时间戳。

### GitHub Pages

1. 打开 Settings → Pages → `Build and deployment`
2. 选择 `Deploy from a branch`
3. Branch 选 `main`，目录选 `/docs`
4. 保存后等待几分钟，页面即可对外提供 `docs/index.html`

## 常见问题

- **工作流失败怎么办？** 打开 Actions 日志，通常是网络超时或数据源变动；根据提示修正配置或重试。
- **指数想要扩充？** 在 `config/indices.yaml` 新增条目并指定行情/估值来源，重跑脚本或等定时任务即可。
- **本地运行缺乏网络？** 先在外网机器运行脚本生成 `data/` 与 `docs/assets.csv`，再同步到目标环境读取。
