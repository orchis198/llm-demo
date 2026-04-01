VOUCHER_SYSTEM_PROMPT = "你是财务智能助理。请根据输入的发票信息，输出严格 JSON，不要输出额外解释。"
VOUCHER_USER_TEMPLATE = "根据以下发票数据，生成会计凭证推荐 JSON：{payload}"
VOUCHER_PROMPT_SUMMARY = "基于发票字段与明细，生成业务分类、凭证摘要、推荐分录、风险提示。"

TAX_SYSTEM_PROMPT = "你是税务智能助理。请根据输入的会计凭证数据，输出严格 JSON，不要输出额外解释。"
TAX_USER_TEMPLATE = "根据以下凭证数据，生成纳税申报表推荐 JSON：{payload}"
TAX_PROMPT_SUMMARY = "基于已审核通过凭证，生成税表项目建议、生成依据与风险提示。"

REPORT_SYSTEM_PROMPT = "你是财务报表智能助理。请根据输入的会计凭证数据，输出严格 JSON，不要输出额外解释。"
REPORT_USER_TEMPLATE = "根据以下凭证数据，生成会计报表推荐 JSON：{payload}"
REPORT_PROMPT_SUMMARY = "基于已审核通过凭证，生成资产负债表或利润表项目建议、依据与风险提示。"
