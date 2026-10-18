# 小米手环 10 高保真 Web 3D 配置器

基于 Vite + React + React Three Fiber + drei 的可交互 3D 查看器，加载真实比例 GLB 模型，
支持配色切换、表带材质切换、上传自定义屏幕表盘、360° 旋转缩放、截图保存、相机预设。

## 快速开始

```bash
npm install
npm run dev        # 本地开发，默认 http://localhost:5173/mi-band10-configurator/
npm run build      # 生产构建到 dist/
npm run preview    # 预览构建产物
```

打开浏览器即可交互。

## 目录结构

- `references/` — 官方/拆解参考图与尺寸、配色、材质清单（第一阶段产物）
- `model/` — GLB 生成脚本（`generate_model.py`）与 glTF 校验脚本（`validate_glb.mjs`）
- `public/models/mi_band10.glb` — 导出的真实比例 GLB（毫米建模，导出时缩放到米）
- `public/textures/` — 各部位 PBR 贴图（BaseColor / Roughness+Metalness / Normal / AO）
- `src/` — React 交互页面（Viewer / Controls / store）
- `tests/` — Playwright 自动检测脚本（`snapshot.test.mjs`）
- `snapshots/` — 自动检测多机位截图证据
- `CHANGELOG.md` — 自动检测迭代记录

## 重新生成模型（可选）

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python model/generate_model.py   # 导出 + 自交检测 + glTF 校验
```

模型结构：主机身（屏幕玻璃 + 金属/陶瓷边框 + 后盖 + 背部传感器 + 充电触点）
与四套独立表带（TPU / 金属链式 / 皮革 / 编织），均对照 `references/` 中的参考图与尺寸表。

## 自动化检测

```bash
npm run test:e2e    # 需要 xvfb：xvfb-run -a npm run test:e2e
```

遍历 5 配色 × 4 表带 × 7 机位 + 8 随机角度截图，输出到 `snapshots/`，
逐张检查加载/亮度，结果追加到 `CHANGELOG.md`。

## 部署（GitHub Pages）

已包含 `.github/workflows/deploy.yml`（Actions 部署到 Pages）。
推送到 `main` 分支后，Actions 自动构建并发布；
或在仓库 Settings → Pages 选择 `GitHub Actions` 作为来源。

> 模型资源统一放在 `public/`，由 Vite 以仓库名为 base 提供，GitHub Pages 路径为
> `https://<user>.github.io/mi-band10-configurator/`。
