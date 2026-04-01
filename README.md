# demoV1

## 1. 项目简介

`demoV1` 是一个面向财务流程演示的 Streamlit Demo，核心目标是展示：

- 发票/凭证采数
- 三单核对
- 会计凭证生成与人工审核
- 纳税申报表承接
- 会计报表承接
- 官方参考件预览
- 打印预览

项目同时支持两种运行模式：

- **演示模式**：无需 API，可直接用于本地展示
- **完整模式**：需用户自行配置 API，启用 LLM 能力

项目还支持：

- 源码运行
- 双击 `exe` 启动
- GitHub 分发
- U 盘便携展示

---

## 2. Demo 功能

### 2.1 发票/凭证采数
- 支持示例文件与上传文件两种导入方式
- 支持原件快照/分页预览
- 支持字段级人工审核
- 支持明细级人工审核
- 支持“正常 / 存疑 / 有误 / 待补充”状态标记
- 支持审核差异展示
- 支持辅助信息与发票查验
- 支持确认采数结果并进入下一环节

### 2.2 三单核对
- 展示发票、合同、入库单的三单核对结论
- 展示差异字段与说明
- 支持人工填写审核说明
- 支持确认三单核对结果并进入会计凭证

### 2.3 会计凭证
- 根据已确认采数结果生成凭证建议
- 左侧展示：
  - 推荐分录
  - 推荐依据
  - 智能体任务卡
  - LLM 元数据
- 右侧支持人工编辑分录
- 支持审核校验
- 支持审核通过（并入账）
- 支持打印预览
- 支持进入纳税申报表 / 会计报表

### 2.4 纳税申报表
- 当前按**官方主表结构**承接
- 左侧展示：
  - 推荐申报项
  - 推荐依据
  - 智能体任务卡
  - LLM 元数据
- 右侧支持官方主表编辑
- 支持打印预览
- 支持查看 show 参考件与官方样例

### 2.5 会计报表
- 当前支持：
  - **资产负债表主体结构**
  - **利润表主体结构**
- 左侧展示：
  - 推荐报表项
  - 推荐依据
  - 智能体任务卡
  - LLM 元数据
- 右侧支持主体结构编辑
- 支持打印预览
- 支持查看 show 参考件与官方样例

### 2.6 参考件与预览
- 支持图片预览
- 支持 Excel 工作表切换预览
- 支持 docx 文本提取预览
- 税表/报表页面支持 **放大预览**

### 2.7 打印预览
- 会计凭证、纳税申报表、会计报表均支持打印预览
- 打印视图尽量贴近当前 demo 中的业务表头和主体结构

---

## 3. 项目结构

```text
.demoV1/
├─ app.py
├─ launcher.py
├─ main.py
├─ README.md
├─ requirements.txt
├─ .env.example
├─ .gitignore
├─ demoV1.spec
├─ build_exe.bat
├─ build_portable_release.bat
├─ assemble_portable_release.py
│
├─ config/
│  ├─ __init__.py
│  └─ settings.py
│
├─ data/
│  └─ show/
│     ├─ manifests/
│     ├─ raw/
│     └─ derived/
│
├─ domain/
│  ├─ __init__.py
│  ├─ models.py
│  └─ flow_models.py
│
├─ engines/
│  ├─ __init__.py
│  ├─ invoice_parser.py
│  ├─ matching_engine.py
│  ├─ accounting_engine.py
│  ├─ tax_report_engine.py
│  └─ reporting_engine.py
│
├─ example/
│  └─ reference/
│     ├─ 记账凭证.png
│     ├─ 增值税及附加税费申报表（一般纳税人适用）.xls
│     ├─ A06155《资产负债表（适用执行企业会计制度的企业）》.docx
│     └─ A06156《利润表（适用执行企业会计制度的企业）》.docx
│
├─ llm/
│  ├─ __init__.py
│  ├─ client.py
│  ├─ prompts.py
│  ├─ provider_info.py
│  ├─ schemas.py
│  └─ service.py
│
├─ services/
│  ├─ __init__.py
│  ├─ demo_flow_service.py
│  ├─ intake_service.py
│  ├─ matching_service.py
│  ├─ show_dataset_service.py
│  ├─ voucher_service.py
│  ├─ tax_service.py
│  └─ report_service.py
│
├─ stage_pages/
│  ├─ __init__.py
│  ├─ intake_page.py
│  ├─ matching_page.py
│  ├─ voucher_page.py
│  ├─ tax_declaration_page.py
│  └─ financial_report_page.py
│
├─ tests/
│  ├─ __init__.py
│  ├─ test_invoice_parser.py
│  ├─ test_matching_engine.py
│  ├─ test_accounting_engine.py
│  ├─ test_tax_report_engine.py
│  ├─ test_reporting_engine.py
│  └─ test_llm_client.py
│
└─ ui/
   ├─ __init__.py
   ├─ session_state.py
   └─ components/
      ├─ __init__.py
      ├─ file_preview.py
      ├─ print_views.py
      └─ status_cards.py
```

### 3.1 根目录文件说明
- `app.py`：Streamlit 主入口，负责阶段导航与页面路由
- `launcher.py`：启动器入口，用于 `exe` 方式双击启动
- `main.py`：简单控制台入口/基础信息输出
- `README.md`：项目说明文档
- `requirements.txt`：Python 依赖列表
- `.env.example`：配置模板，用户需复制为 `.env`
- `.gitignore`：Git 仓库忽略规则
- `demoV1.spec`：PyInstaller 打包配置
- `build_exe.bat`：基础 exe 打包脚本
- `build_portable_release.bat`：便携发布包打包脚本
- `assemble_portable_release.py`：组装便携发布目录

### 3.2 目录说明
- `config/`：配置读取与运行模式判断
- `data/`：项目内置演示数据（show 场景）
- `domain/`：领域模型和流程模型定义
- `engines/`：核心业务引擎，负责解析、核对、凭证、税表、报表计算
- `example/`：官方参考件与示例原件
- `llm/`：LLM 调用、提示词、元信息与 schema
- `services/`：页面与 engine 之间的中间层，负责组装 recommendation / draft
- `stage_pages/`：五阶段业务页面
- `tests/`：测试用例
- `ui/`：共享 UI 状态与组件

### 3.3 各核心模块功能解释
#### `engines/`
- `invoice_parser.py`：发票文本/PDF/表格等解析
- `matching_engine.py`：三单核对规则
- `accounting_engine.py`：凭证推荐、分录校验、合计计算
- `tax_report_engine.py`：纳税申报表官方主表结构承接
- `reporting_engine.py`：资产负债表 / 利润表主体结构承接

#### `services/`
- `intake_service.py`：采数页数据准备、审核定稿、提交流程
- `matching_service.py`：三单核对服务封装
- `voucher_service.py`：会计凭证 recommendation 与 draft 生成
- `tax_service.py`：税表 recommendation 与 draft 生成
- `report_service.py`：会计报表 recommendation 与 draft 生成
- `show_dataset_service.py`：show manifest、参考件路径和文本读取
- `demo_flow_service.py`：阶段选项与流程辅助

#### `ui/components/`
- `file_preview.py`：参考件预览、放大预览、文档/图片/Excel 承接
- `print_views.py`：打印预览与打印壳子
- `status_cards.py`：状态卡、信息块、元数据表

#### `stage_pages/`
- `intake_page.py`：发票/凭证采数页
- `matching_page.py`：三单核对页
- `voucher_page.py`：会计凭证页
- `tax_declaration_page.py`：纳税申报表页
- `financial_report_page.py`：会计报表页

---

## 4. API 配置

### 4.1 配置文件
先复制：

- `.env.example` → `.env`

### 4.2 示例
```env
LLM_ENABLED=true
LLM_PROVIDER=openai-compatible
LLM_MODEL=your_model_name
LLM_API_BASE=https://your-api-base/v1
LLM_API_KEY=your_api_key_here
LLM_TIMEOUT=60
LLM_TEMPERATURE=0.2
LLM_MAX_TOKENS=1200
LLM_FALLBACK_TO_RULES=true
DEMO_RUN_MODE=demo
```

### 4.3 说明
- **演示模式**：无需 API，可直接启动
- **完整模式**：必须先配置 API
- 不会分发任何真实 API

---

## 5. 启动方式

## 5.1 源码运行
```bash
pip install -r requirements.txt
streamlit run app.py
```

源码运行时：
- 默认可通过 `.env` 控制运行模式
- 如果想完整模式，请在 `.env` 中设置：

```env
DEMO_RUN_MODE=full
```

## 5.2 exe 运行
双击打包后的：
- `demoV1-launcher.exe`

启动器会先让您选择：
1. 演示模式
2. 完整模式

- 演示模式：无需 API
- 完整模式：需先配置 `.env`

## 5.3 便携版运行
便携版目录中会包含：
- `demoV1-launcher.exe`
- `runtime/`
- `app.py`
- `data/`
- `example/`
- `.env.example`
- `README.md`

使用时必须保留整个目录结构，**不能只单独拷 exe**。

---

## 6. GitHub 分发方式

### 6.1 仓库里放什么
GitHub 仓库建议放：
- 全部源码
- `.env.example`
- `README.md`
- 打包脚本和 `spec`
- `data/`
- `example/`

### 6.2 仓库里不要放什么
不要提交：
- `.env`
- `.claude/`
- `dist/`
- `build/`
- `dist_release*/`
- `dist_portable_launcher/`
- `portable_release/`
- 缓存文件和日志

### 6.3 GitHub Releases 建议
建议上传：
- `portable_release/demoV1-portable/` 压缩包

例如：
- `demoV1-portable-win64.zip`

---

## 7. U 盘展示方式

直接拷贝整个：
- `portable_release/demoV1-portable/`

### 7.1 演示模式
- 适合现场快速展示
- 无需 API

### 7.2 完整模式
- 先复制 `.env.example` 为 `.env`
- 填写自己的 API
- 再双击 exe 并选择完整模式

---

## 8. 打包说明

### 8.1 基础 launcher 打包
```bash
pyinstaller demoV1.spec
```
或：
```bash
build_exe.bat
```

### 8.2 便携发布包组装
```bash
python assemble_portable_release.py
```
或：
```bash
build_portable_release.bat
```

组装完成后，便携目录位于：
- `portable_release/demoV1-portable/`

---

## 9. 常见问题

### Q1. 没有 API 能用吗？
可以。
- 选择**演示模式**即可。

### Q2. 完整模式为什么进不去？
通常是：
- 没有 `.env`
- `.env` 没填 API
- `LLM_ENABLED` 没设为 `true`

### Q3. 为什么不能只拷 exe？
因为便携版还依赖：
- `runtime/`
- `app.py`
- `data/`
- `example/`
- 其它模块目录

### Q4. `.env` 放哪里？
放在：
- `demoV1-launcher.exe` 同级目录

### Q5. GitHub 版和 U 盘版有什么区别？
- GitHub 仓库：放源码
- GitHub Releases：放便携压缩包
- U 盘版：直接拷贝便携目录

---

## 10. 当前建议的最终分发方式

### GitHub
- 仓库上传源码
- Releases 上传便携包 zip

### U 盘
- 拷贝整个 `demoV1-portable/`

### 本地演示
- 双击 `demoV1-launcher.exe`
- 选演示模式

---

## 11. 备注
本项目当前重点是：
- 演示流程可走通
- 关键页面可对照官方参考件
- 支持便携展示

如继续迭代，可继续增强：
- 纳税申报表附列资料承接
- 财务报表更完整官方行结构
- 发布包自动化构建与版本化发布
