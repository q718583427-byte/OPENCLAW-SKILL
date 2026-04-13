---
name: email-triage-openclaw
description: Find what needs attention first across recent email threads, avoid missed deadlines, and get Chinese reply-ready summaries, dashboards, and draft suggestions. This is an Open CLAW compatible version of email-triage with platform-agnostic capability requirements.
metadata:
  nanobot:
    # Tool interfaces declared here represent capability contracts.
    # Open CLAW compatible runtimes should provide equivalent tools.
    tools:
      - email_fetch       # Fetch emails by date range, account, with body truncation
      - email_attachment_extract  # Read PDF/DOCX/XLSX attachment content
      - email_thread_inspect      # Inspect thread history and sent items
capabilities:
  email_accounts:
    description: "支持多邮箱账号配置（IMAP + SMTP），支持 QQ/163/Gmail 等主流邮箱"
    fields:
      - imap_host
      - imap_port
      - imap_username
      - imap_password
      - smtp_host
      - smtp_port
      - smtp_username
      - smtp_password
  email_fetch:
    description: "按时间范围获取邮件列表，支持多账号聚合、邮件正文截断、附件元数据提取"
    features:
      - recent_mode
      - between_mode
      - body_truncation
      - attachment_metadata
      - reply_headers
  attachment_extract:
    description: "读取 PDF/DOCX/XLSX 附件正文内容"
    formats:
      - PDF
      - DOCX
      - XLSX
  thread_inspect:
    description: "检查邮件线程历史，支持 INBOX/Sent 等文件夹，获取 reply headers 和已发邮件证据"
---

# Email Triage and Priority Reply

## 目标
帮助用户快速看清近 7 日邮件里：
- 哪些必须先回
- 哪些值得尽快处理
- 哪些只是信息同步
- 哪些已经闭环可以放心归档

目标不是"更复杂地分析邮件"，而是"更少漏事、更少反复翻邮箱、更快进入处理状态"。

## 用户价值
使用这个技能时，用户应当直接得到这些收益：
- 不必逐封翻看邮件，先拿到"今天先处理什么"的清单
- 更早发现 deadline、补件、确认、排期等容易漏掉的动作项
- 快速知道"这封要不要回""为什么要回""可以怎么回"
- 对求职、学校、工作协作邮件优先聚焦，把低价值通知自动降到后面
- 直接获得中文回复提纲和看板，减少从判断到行动之间的切换成本

本技能对用户的交付物应尽量稳定为：
- 一份可直接执行的优先回复列表
- 一份按优先级整理的线程看板
- 每个线程的简短判断依据
- 需要时可直接改写使用的中文回复草稿

本技能专注：
- 线程优先级分类（`high|medium|low`）
- 待回复识别（`need_reply: yes|no`）
- 线程闭环检测（`is_closed: true|false` + `closure_signal`）
- 关键信息提取（deadline、待办、实体、附件元数据）
- 中文回复提纲生成（默认草稿，不自动发送）
- 今日看板整理（优先回复、高优未处理、含 deadline、已闭环、分组概览）

能力边界说明：
- `email_fetch` 默认提供的是"邮件级证据 + reply headers + 附件元数据"，不是邮箱服务端原生 thread API
- 本技能可基于 `messageId / inReplyTo / references / 标题归一化` 做**近似线程归并**，但不得宣称与邮件客户端完全一致
- 附件正文默认不直接可见；需调用 `attachment_extract` 才能读取 `PDF / DOCX / XLSX`
- "用户是否已经回过"不能仅靠猜测；需要优先调用 `thread_inspect` 获取发件箱/回复头证据

## 触发场景与非适用场景
适用请求示例：
- "整理今天邮件并告诉我先处理什么"
- "帮我找出最近 7 天最容易漏掉的 deadline 和待回复"
- "判断这个线程要不要回复，并给我一个能直接改的中文草稿"
- "按优先级汇总我最近 7 天邮件，给我一个看板"

非适用或低优先场景：
- 直接代替邮件客户端做完整收发管理
- 对复杂长附件做专业审阅结论
- 未经确认自动发送邮件
- 对实时政策/法律/合同条款做最终背书

## 输入槽位与先追问规则
优先抽取槽位：
- `window_days`（默认 7）
- `accounts`（可选，多账号；对应 `email_fetch.accounts`）
- `mailboxes`（可选，邮箱文件夹范围；仅用于 `thread_inspect`，如 `INBOX` / `Sent`）
- `focus`（规范值固定为 `求职/学校/工作/通用`；若输入为 `job_search/school/work/general`，必须先归一化为对应中文值再继续判断）
- `response_window_days`（可选，覆盖超时推断与跟进窗口）
- `target_thread`（单线程模式）
- `user_rules`（用户个人优先级规则，支持发件人/域名/关键词覆盖）

术语归一化要求：
- 用户自然语言中提到"邮箱/账号/账户"，若语义是跨账号抓取范围，一律归一化为 `accounts`
- 只有当用户明确提到"收件箱 / 已发送 / 文件夹 / mailbox"时，才归一化为 `mailboxes`
- 不得把 `mailboxes` 当作多账号筛选字段传给 `email_fetch`

## `user_rules` 约定（初始版）

若用户没有提供 `user_rules`，必须使用内置默认优先级规则；不得因为缺少个性化配置而跳过 `priority` 判断。

推荐的初始结构：

```json
{
  "user_rules": {
    "default_priority": "medium",
    "response_window_days": 5,
    "sender_rules": [
      {
        "match": "boss@company.com",
        "priority": "high",
        "need_reply": "yes",
        "reason": "直属老板"
      }
    ],
    "domain_rules": [
      {
        "match": "university.edu",
        "priority": "high",
        "reason": "学校域名"
      }
    ],
    "keyword_rules": [
      {
        "match": "面试",
        "priority": "high"
      },
      {
        "match": "newsletter",
        "priority": "low",
        "need_reply": "no"
      }
    ]
  }
}
```

解释规则：
- `default_priority` 是用户个人默认优先级；未提供时回退到系统默认 `medium`
- `response_window_days` 用于定义"超过多久可视为超出预期响应窗口"；未提供时按 `focus` 动态取默认值
- `sender_rules` 用于最强覆盖，适合老板、导师、客户、家人等固定对象
- `domain_rules` 适合学校、公司、政府、平台等整域规则
- `keyword_rules` 适合"面试""补件""发票""推广"等主题词
- 同时命中多个用户规则时，固定优先级为：`sender_rules > domain_rules > keyword_rules`
- 用户规则只覆盖已声明字段；未声明字段继续走系统默认规则

## 首次使用个性化规则软引导

为避免用户长期停留在默认规则，首次使用 `email-triage` 且未提供 `user_rules` 时，必须采用"先完成分诊，再轻量引导"的方式，而不是先用配置问题打断主任务。

触发条件：
- 当前请求未提供 `user_rules`
- 长期记忆中不存在已确认的 email-triage 个性化偏好
- 用户请求属于"完整分诊""近 7 日整理""看板""优先回复列表"这类多线程任务

不触发条件：
- 单线程判断、单封邮件回复草稿、一次性问答类请求
- 用户已明确拒绝配置或明确表示"不需要记住规则"
- 当前轮已经提供 `user_rules`

执行顺序：
1. 先按内置默认规则完成本次分诊
2. 再在自然语言结果末尾追加一个简短的"首次使用建议"区块
3. 建议只包含 1-3 个最高价值的配置方向，不进入长问卷

首次使用建议的输出要求：
- 必须放在主结论之后，不得抢占主结果
- 必须明确说明"当前结果已基于默认规则完成"
- 必须明确说明"如果用户愿意，下一轮可以帮助其保存个性化规则"
- 不直接要求用户填写完整 JSON；优先用自然语言引导
- 建议内容固定围绕以下三类：
  - 哪些发件人应长期高优先
  - 哪些域名通常高优先
  - 哪些关键词通常低优先或无需回复

建议文案应尽量接近：
- "本次结果已按默认规则完成。"
- "如果你愿意，下次我可以记住你的偏好，例如：老板/导师长期高优先、学校域名高优先、newsletter 默认低优先。"

若用户明确拒绝配置：
- 本轮仍正常完成分诊
- 当前会话中不重复主动引导
- 不写入任何长期偏好

## 长期记忆中的 email-triage 偏好

当用户明确确认 email-triage 偏好后，可以将其写入长期记忆，作为后续未提供 `user_rules` 时的缺省个性化补全。

长期记忆规则：
- 只有用户明确确认的规则才能写入长期记忆
- 不得根据单次 triage 结果自动推断并保存用户偏好
- 保存内容应为稳定偏好摘要，而不是整段原始对话
- 后续请求若未提供 `user_rules`，可先读取长期记忆中的 email-triage 偏好并重建有效规则
- 当前请求显式提供的 `user_rules` 永远优先于长期记忆中的历史偏好
- 长期记忆只用于"缺省个性化补全"，不是强覆盖来源
- 若长期记忆与当前任务明显不匹配，可保守回退到内置默认规则，并设置 `review_needed = true`

推荐保存的长期偏好结构：
- `default_priority`
- `response_window_days`
- 高优先发件人列表
- 高优先域名列表
- 低优先关键词 / 无需回复关键词
- 适用 `focus`（长期记忆中统一保存中文规范值：如 `求职` / `学校` / `工作` / `通用`）

## 邮箱账号配置（channels_config）

EmailFetchTool 通过 `channels_config` 获取邮箱账号配置，支持两种格式：

### 多账号格式
```json
{
  "email_accounts": {
    "qq": {
      "enabled": true,
      "consent_granted": true,
      "account_id": "qq",
      "imap_host": "imap.qq.com",
      "imap_port": 993,
      "imap_username": "user@qq.com",
      "imap_password": "...",
      "imap_mailbox": "INBOX",
      "smtp_host": "smtp.qq.com",
      "smtp_port": 587,
      "smtp_username": "user@qq.com",
      "smtp_password": "...",
      "from_address": "user@qq.com"
    },
    "163": {
      "enabled": true,
      "consent_granted": true,
      "account_id": "163",
      "imap_host": "imap.163.com",
      "imap_port": 993,
      "imap_username": "user@163.com",
      "imap_password": "...",
      "imap_mailbox": "INBOX",
      "smtp_host": "smtp.163.com",
      "smtp_port": 587,
      "smtp_username": "user@163.com",
      "smtp_password": "...",
      "from_address": "user@163.com"
    }
  }
}
```

### 单账号格式
```json
{
  "email": {
    "enabled": true,
    "consent_granted": true,
    "account_id": "default",
    "imap_host": "imap.example.com",
    "imap_port": 993,
    "imap_username": "user@example.com",
    "imap_password": "...",
    "imap_mailbox": "INBOX",
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "smtp_username": "user@example.com",
    "smtp_password": "...",
    "from_address": "user@example.com"
  }
}
```

### 必填字段验证
账号配置必须满足以下条件才会被使用：
1. `enabled = true` — 账号已启用
2. `consent_granted = true` — 用户已明确授权
3. `imap_host` / `imap_username` / `imap_password` — IMAP 收件配置完整
4. `smtp_host` / `smtp_username` / `smtp_password` — SMTP 发件配置完整

### 可选配置项
| 字段 | 默认值 | 说明 |
|------|--------|------|
| `imap_port` | 993 | IMAP 端口 |
| `imap_mailbox` | "INBOX" | 邮箱文件夹 |
| `imap_use_ssl` | true | 是否使用 SSL |
| `smtp_port` | 587 | SMTP 端口 |
| `smtp_use_tls` | true | 是否使用 TLS |
| `smtp_use_ssl` | false | 是否使用 SSL |
| `mark_seen` | true | 获取邮件后标记为已读 |
| `max_body_chars` | 12000 | 正文最大字符数 |

### 获取可用账号列表
调用 `email_fetch` 时：
- 不指定 `accounts` 参数：自动获取所有已配置的账号
- 指定 `accounts=["qq", "163"]`：只获取指定账号
- 未知账号会返回错误，并列出可用账号

必须先追问的情况：
- 用户明确要求自定义分析范围（如指定某个时间范围、某个邮箱、某个账号或排除某些账号），但约束信息不足，无法安全确定抓取范围
- 用户要求生成回复内容，但未提供目标线程或上下文不足
- 用户要求生成可直接发送的中文草稿，但缺失关键事实（如时间、附件、金额、承诺内容）且无法安全用简短占位符表示
- 用户要求发送邮件，但未给出显式确认

追问原则：
- 一次最多 3 个问题
- 优先问影响最大的范围约束
- 问题简短，不重复

## 近 7 日防遗漏抓取策略（必执行）

当用户要求"整理近 7 日邮件/今日看板/完整分诊"时，必须按以下顺序抓取，避免漏邮件：

- 若用户仅说"完整分诊""整理邮件""今日看板""优先回复列表"等总览型请求，且未显式限定时间范围或邮箱范围，则默认按"近 7 日 + 所有已配置账号"执行，不先追问范围问题。
- 只有当用户明确要求自定义范围，而所需时间范围 / 账号范围信息又不足时，才先追问并缩小范围。

1. **首轮全量抓取（所有账号）**
- 调用 `email_fetch`：`mode="recent"`、`windowDays=7`、`limit=100`、`bodyMaxChars=1500`。
- 不传 `accounts`（默认抓取所有已配置账号）。

2. **覆盖检查（逐账号）**
- 检查每个账号的返回：`status`、`count`、`error`。
- 若某账号 `status = failed`，必须在结果中明确标注"该账号抓取失败 + 原始错误"，且不得宣称"全量覆盖完成"。
- 若某账号 `count == 100`，视为"可能触达单次上限"，不能直接判定为已完整覆盖。

3. **分日补抓（仅对触达上限账号）**
- 对该账号按天补抓近 7 日：循环 7 次调用 `email_fetch`，使用 `mode="between"`，每次 `startDate=endDate=该日`，`limit=100`，`accounts=[account_id]`。
- 补抓结果与首轮结果合并后去重。

4. **去重键（严格顺序）**
- 一级键：`accountId + messageId`（优先）。
- 二级键：`accountId + uid`（当 `messageId` 缺失）。
- 三级键：`accountId + sender + subject + date`（兜底，防重复展示）。

5. **覆盖声明（必须写入自然语言说明）**
- 必须明确说明：抓取账号数、每账号抓取条数、是否触达上限、是否执行分日补抓。
- 若分日补抓后仍出现某天 `count == 100`，必须明确标注"该天可能仍有遗漏"，并提示用户可进一步缩小范围或分批次复查。

6. **覆盖优先于正文深度（强制）**
- 完整分诊默认优先保证"近 7 日 + 所有目标账号"的覆盖，不得为了读取更长正文而牺牲覆盖范围。
- 若去重后消息量仍很大，首轮分诊只使用 `sender / subject / date / reply headers / body snippet / attachments metadata`。
- 只有对高优先、待回复、闭环证据不足、或高度依赖附件/正文细节的候选线程，才继续深读正文、调用 `attachment_extract` 或调用 `thread_inspect`。
- 不得把"长正文已读"表述成完整覆盖的前提；完整覆盖与正文深读是两个阶段。

7. **时间边界约束（强制）**
- 先从首个成功的 `email_fetch` 结果读取一次 `localDate` 作为唯一锚点日 `anchor_date`（格式 `YYYY-MM-DD`）；本轮所有后续计算都复用该锚点，禁止中途重新取"今天"。
- 近 7 日窗口固定为：`start_date = anchor_date - 6 days`，`end_date = anchor_date`（两端都包含）。
- `between` 调用必须使用日期粒度：`startDate` 与 `endDate` 都是 `YYYY-MM-DD`，且按"包含起止日"解释。
- 单日补抓时必须写成：`startDate = D` 且 `endDate = D`，表示只抓这一天，不能写 `D+1`。
- 7 日补抓日序列必须严格为：`anchor_date-6, anchor_date-5, ..., anchor_date`（共 7 天，不能 6 天或 8 天）。
- 若 `anchor_date = 2026-04-03`，则合法窗口仅为 `2026-03-28` 到 `2026-04-03`（包含两端）。
- 若执行过程中跨午夜，仍沿用原 `anchor_date`；本轮不得切换到新日期，避免多一天或少一天。

## 近似线程工作流（规则优先）
1. 默认以"邮件消息"为基础单元；仅在证据足够时，基于 `messageId / inReplyTo / references / 标题归一化` 做近似线程归并。
2. 不得宣称"邮箱原生线程已精确还原"；若仅靠标题匹配，必须在自然语言说明中使用"近似归并 / 可能相关线程"之类表述。
3. 先应用当前请求显式用户规则，再补充长期记忆中已确认的偏好规则。
4. 在显式规则与长期记忆偏好都不足时，再识别重要发件人/域名与动作信号（deadline、确认请求、提交材料、面试/会议等）。
5. 产出 `priority` 与 `need_reply`。
6. 提取摘要、待办、deadline、实体、附件元数据。
7. 若需要读取 `PDF / DOCX / XLSX` 附件内容，必须调用 `attachment_extract`；不得把附件名当作正文内容。
8. 若需要判断"用户是否已经回过 / user_handled / 强闭环证据"，必须优先调用 `thread_inspect`；没有工具证据时只能保守输出。
9. 输出建议动作（`draft_reply`、`add_todo`、`archive`、`snooze`）。

固定决策顺序：
1. 当前请求显式用户规则
2. 长期记忆中已确认的 email-triage 偏好
3. 重要性判定（发件人、域名、关系、事项价值）
4. 紧急性判定（deadline、催办、阻塞、等待回复）
5. `importance × urgency -> priority` 映射
6. `need_reply` 判定
7. 上下文 AI 校正（不得推翻显式用户规则，也不得覆盖已确认的长期偏好）
8. 低置信度保守降级

## 默认优先级、重要性与个性化覆盖（主文档内联，缺失引用文件时也必须执行）

为避免把"重要但不急"和"紧急但不重要"混为一谈，内部必须先拆分两个维度：
- `importance`：这条线程本身是否值得高度关注
- `urgency`：这条线程是否需要尽快处理
- 对外仍只输出 `priority`（`high|medium|low`）；`importance` 与 `urgency` 用于内部判定与 `reasoning_summary`

最小可执行规则：
1. 先按以下顺序确定默认来源：当前请求显式 `user_rules` > 长期记忆中已确认的 email-triage 偏好 > 内置默认规则
2. 先设 `priority = explicit_user_rules.default_priority`；若未提供，则回退到 `memory_user_rules.default_priority`；仍未提供时默认 `priority = medium`
3. 先设 `need_reply = no`
4. 先应用当前请求显式提供的用户规则：`sender_rules > domain_rules > keyword_rules`
5. 若显式用户规则未得出最终结论，再应用长期记忆中已确认的偏好规则：`sender_rules > domain_rules > keyword_rules`
6. 若显式规则和长期记忆偏好仍未得出最终结论，再分别判定 `importance` 与 `urgency`
7. 通过固定映射表将 `importance` 与 `urgency` 合成为最终 `priority`
8. 若信息不足或置信度低，不得凭猜测升为 `high`；默认保守输出 `priority = medium`，并设置 `review_needed = true`

### 重要性（`importance`）判定

`importance = high`：
- 发件人为老师、导师、HR、招聘方、面试官、直属经理、客户、核心合作方
- 主题涉及求职结果、学校事务、合同、付款、报销、账号安全、审批、签字等高价值事项
- 用户是该线程的主要责任人，且处理结果会显著影响工作、求学、合作或资金

`importance = medium`：
- 与学校、求职、工作协作、项目推进相关，但影响范围有限
- 发件人为同事、同学、普通合作方、常规业务联系人
- 线程值得查看和跟进，但不是关键关系或关键事项

`importance = low`：
- 营销、推广、订阅、群发通知
- 常规系统通知、物流提醒、例行账单、优惠活动
- 抄送型线程，且用户不是主要处理人
- 纯信息同步，无明确业务价值或决策价值

### 紧急性（`urgency`）判定

`urgency = high`：
- 存在明确 deadline，且通常在 72 小时内，或邮件明确写明"今天/明天/尽快"
- 对方要求确认、回复、补件、排期、参会、付款、审批等即时动作
- 该线程阻塞后续流程，等待用户给出答案、材料、时间或选择
- 同一事项已被催办、提醒，或已经超出合理回复窗口

`urgency = medium`：
- 存在"本周内/尽快/有空回复"一类软时限，但非立即阻塞
- 需要用户处理，但暂时不构成当日风险
- 需要排期、确认或继续跟进，但短时间内不回复也不会立刻造成损失

`urgency = low`：
- 没有明确 deadline，也没有直接动作请求
- 主要用于知会、归档、参考或背景同步
- 线程已闭环，或用户不是主要行动人

### `priority` 固定映射

按以下规则将 `importance` 与 `urgency` 映射为最终 `priority`：

| `importance` | `urgency` | `priority` |
|---|---|---|
| `high` | `high` | `high` |
| `high` | `medium` | `high` |
| `high` | `low` | `medium` |
| `medium` | `high` | `high` |
| `medium` | `medium` | `medium` |
| `medium` | `low` | `low` |
| `low` | `high` | `medium` |
| `low` | `medium` | `low` |
| `low` | `low` | `low` |

补充规则：
- 当前请求显式用户规则可直接覆盖 `priority` 和 `need_reply`
- 长期记忆中的已确认偏好只补全未声明字段，不得覆盖当前请求的显式规则
- 重要发件人不等于必然 `high`；若事项不紧急，仍可落到 `medium`
- 紧急系统提醒不等于高重要性；若价值较低，最高只升到 `medium`
- 若信号冲突且无显式用户规则，优先选择更保守的结果

## 响应窗口与超时推断策略

为避免将"3 天无新消息"写死为统一阈值，必须先计算有效响应窗口 `effective_response_window_days`，再用于：
- "是否已超出预期响应窗口"的紧急性判断
- `need_reply` 中的跟进提醒判断
- `timeout_inactive` 的闭环推断

有效响应窗口按以下顺序确定：
1. 当前请求显式提供的 `response_window_days`
2. 当前请求显式 `user_rules.response_window_days`
3. 长期记忆中已确认偏好的 `response_window_days`
4. 按 `focus` 动态取默认值
5. 若仍缺失，则回退到 `5`

按 `focus` 的默认响应窗口：

| `focus` | `effective_response_window_days` |
|---|---|
| `求职` | `7` |
| `学校` | `5` |
| `工作` | `3` |
| `通用` | `5` |

`focus` 归一化要求：
- 中文规范值固定为：`求职` / `学校` / `工作` / `通用`
- 若收到英文别名，先归一化后再用于响应窗口、语气选择、长期记忆写入与 `user_rules` 重建：
  - `job_search -> 求职`
  - `school -> 学校`
  - `work -> 工作`
  - `general -> 通用`
- 若读取到未知 `focus` 值，保守按 `通用` 处理

解释原则：
- 统一按自然日计算；除非用户明确要求，否则不引入工作日逻辑
- 若存在明确 deadline，则 deadline 优先于响应窗口；不得仅因超过响应窗口就忽略明确 deadline
- 若线程中仍存在未回答的直接问题、未完成待办、未来 deadline、或用户已承诺的下一步动作，则不得仅凭时间流逝判定 `is_closed = true`
- `timeout_inactive` 只能用于"无新消息 + 无待办 + 无直接未答问题 + 无更强开启信号"的保守闭环推断
- 当使用 `timeout_inactive` 或"超过响应窗口"作为依据时，`reasoning_summary` 或 `closure_reason` 必须说明本次使用的 `effective_response_window_days` 及其来源（显式设置 / 长期记忆 / `focus` 默认）

`need_reply = yes` 的默认条件：
- 对方提出直接问题
- 对方要求确认、回复、补充材料、提供时间或可用性
- 用户是 deadline 绑定动作的主要执行人，且 `urgency != low`
- `priority = high` 且线程在超过 `effective_response_window_days` 后仍处于未处理状态

`need_reply = no` 的默认条件：
- 单向通知、FYI、营销、系统提醒
- 线程已闭环，或邮件明确写明"无需回复"
- 用户不是主要处理人，且没有明确动作要求
- 仅需归档、参考或记录，无需用户继续推进

透明性要求：
- `reasoning_summary` 至少说明本次判断主要来自：当前请求显式规则 / 长期记忆偏好 / 内置默认规则
- `reasoning_summary` 至少分别说明 `importance` 与 `urgency` 的核心判定信号
- `reasoning_summary` 至少说明最终 `priority` 的映射结果
- 若发生保守降级，必须说明是因低置信度回退到 `medium`

## 线程闭环检测流程
在完成优先级和待回复判断后，必须判断线程是否已闭环：

闭环保护门（对所有闭环信号都生效）：
- 只要线程中仍存在未答直接问题、开放待办、未来 deadline、或用户已承诺但未完成的下一步动作，就不得仅凭确认语、结论语或时间流逝判定 `is_closed = true`
- `timeout_inactive` 继续使用最严格门槛；不得绕过上述保护门
- 只有 `explicit_close` 可以在存在历史事项时覆盖关闭，且关闭表达必须明确表示该事项已取消、完结或无需继续推进

1. **确认信号检测** — 对方明确表示"已处理"、"已完成"、"没问题"等，或仅表示"收到"、"好的"、"同意"、"已知悉"但同时不存在任何未完成事项时，才可作为 `confirmed_by_recipient`
2. **用户处理检测** — 仅当 `thread_inspect` 或用户显式提供的上下文显示用户已回复/已处理时，才可判定 `user_handled`
3. **完成信号检测** — 待办已被标记完成、已取消、已超时失效
4. **超时推断** — 线程超过有效响应窗口（`effective_response_window_days`）无新消息，且无未答问题、无待办、无未来 deadline、无更强开启信号
5. **显式关闭** — 对方或用户明确说"关闭"、"完结"、"无需回复"，或明确表示事项已取消、不再推进
6. **结论性内容** — 线程中存在决策、答案、解决方案等结论

`is_closed = true` 时，`recommended_actions` 中必须包含 `archive`，且 `need_reply = no`。

## 附件处理

- `email_fetch` 默认仅提供附件元数据（名称、类型、大小等）；不默认承诺"已读过附件正文"。
- 对 `PDF / DOCX / XLSX` 附件，如判断高度依赖附件内容，必须调用 `attachment_extract` 后再下结论。
- 遇到 `.caj` 或疑似学术论文附件时，不在本技能内深度解析正文或提取论文元数据。
- 保留附件名称/类型并设置 `manual_review_needed = true`。
- 在自然语言说明或 `brief` 中提示：建议人工查看，或切换到 `$caj-reader` 处理 CAJ 文档。

## 中文回复草稿质量规范

当用户明确要求"生成回复""给草稿""给提纲"，或线程结果中的 `recommended_actions` 包含 `draft_reply` 时，必须遵守以下质量约束。

### 草稿输出目标

- 默认交付物应是"可直接改写使用的中文回复草稿"，而不是只有几个零散要点
- 若用户明确要求"提纲"或信息不足以安全生成可直接发送文本，可降级为"回复提纲 + 待确认信息"
- 草稿默认不自动发送；仅供用户审阅、修改和确认

### 默认输出结构

除非用户明确要求极简回复，否则自然语言结果中的草稿部分应尽量包含三段：
1. `回复目标`：用一句话说明这封回复要完成什么
2. `中文回复草稿`：提供可直接复制改写的正文
3. `待确认信息`：仅在存在缺失事实上出现

`中文回复草稿` 本身应尽量具备以下结构：
- 称呼
- 核心回应：直接回答对方问题、确认事项或说明下一步
- 收尾：礼貌结束语或下一步安排

除非用户明确要求改写主题行，否则默认不生成新 subject。

### 语气与风格

默认中文草稿必须满足：
- 清晰、礼貌、克制，避免"AI 腔"和过度修饰
- 优先回应对方最关心的问题，不先写空泛寒暄
- 能短则短，但不能短到遗漏关键信息

按 `focus` 与关系调整语气：
- `focus = 求职` 或 `学校`：正式、礼貌、积极，优先使用"您"
- `focus = 工作`：专业、简洁、行动导向，少客套、重结论
- `focus = 通用`：自然、清晰、不过分热情
- 若原线程明显是平辈且语气轻松，可适度放松；若对方为上级、HR、导师、客户，默认保持正式

### 长度与组织

- 简单确认、收到、时间确认类回复：通常 1 段，约 50-120 个中文字符
- 常规工作 / 学校 / 求职回复：通常 2-3 段短段落，约 80-220 个中文字符
- 多事项回复：优先按对方问题顺序逐项回应；仅当原邮件本身是多点清单时，才在草稿中使用简短条目
- 未经用户要求，不写成长篇说明，不复制原邮件内容，不加入与问题无关的背景铺垫

### 内容完整性要求

- 必须直接覆盖对方邮件中的核心问题、请求、deadline 或待确认事项
- 若对方提出多个明确问题，草稿应按原顺序逐项回应，避免漏答
- 若邮件要求提供材料、时间、可用性、确认或下一步动作，草稿中必须体现回应或说明何时补充
- 若用户需要延后、拒绝或暂时无法完成，草稿应给出简短说明与下一步安排；不得只说"收到"
- 若附件尚未准备好，草稿只能说明"稍后补充"或"待补充"，不得假装已附上

### 占位符与缺失信息处理

- 默认尽量避免模板占位符，已知事实应直接写入
- 若缺少关键事实但仍可先给草稿，最多允许 3 个显式占位符，例如：
  - `[可参加时间待确认]`
  - `[附件名称待补充]`
  - `[具体金额待确认]`
- 出现占位符时，必须同时提供 `待确认信息` 列表，明确哪些内容需要用户补齐
- 若缺失事实超过 3 项，或缺的是高风险信息（付款、合同条款、身份信息、正式承诺），不得输出可直接发送草稿，应降级为"回复提纲 + 待确认信息"

### 禁止事项

以下内容不得出现在草稿正文中：
- "以下是一封邮件草稿""你可以这样回复"等元话术
- 无依据的承诺、日期、金额、附件、身份信息、会议时间
- 过度吹捧、空泛寒暄、明显机器化套话
- 未经请求的英文模板腔或中英混杂
- 与原线程无关的延伸建议

### 何时不应直接给草稿

- `need_reply = no` 时，默认不生成草稿；除非用户明确要求
- `is_closed = true` 时，默认不生成草稿；除非用户明确要求补发礼貌性回复
- 信息不足且无法安全补齐时，应输出"回复提纲 + 待确认信息"，而不是硬写完整邮件
- 首次联系、付款、合同、证件、账号安全类邮件，即使生成草稿，也必须保持保守、正式，并优先提示用户人工确认

## 待办提取规范（严格）

**核心原则：只提取原文明确写明的待办，不推测，不过度解读。**

### 明确要求的待办（`origin: explicit`）
原文出现以下句式时提取：
- "请 XXX"、"请于 X 日前完成 XXX"
- "需要您 XXX"、"需要准备 XXX"
- "麻烦 XXX"、"期待 XXX"、"希望 XXX"
- 明确指令句式："发送 XXX"、"回复 XXX"、"提交 XXX"

### 可推断的待办（`origin: inferred`）
需要同时满足：① 对方提出具体问题或要求 ② 用户尚未回复或处理：
- 对方提问，等待用户给出答案/选择
- 对方提供清单，等待用户确认

### 禁止提取的待办
- "可能"、"也许"、"可以考虑"等模糊表述
- 对方自己的计划或动作（非用户动作）
- 泛泛的工作建议、方向性讨论
- 纯情绪表达，无具体行动

**宁可漏提取，不可错误提取。**
每次输出必须包含两部分：
1. 面向用户的自然语言说明（默认中文）
2. 结构化 JSON（字段结构、必填项和枚举约束遵循 `references/output_schema.json`；若需要参考输出外形，读取 `references/output_example.json`）

强约束：
- `need_reply` 只能是 `yes|no`
- `is_closed` 只能是 `true|false`
- `closure_signal` 必须为六类之一：`confirmed_by_recipient|user_handled|action_completed|timeout_inactive|explicit_close|resolution_detected`
- `todo_items` 中每项必须有 `origin`（`explicit|inferred`）和 `confidence`（`high|medium`），禁止出现无 origin 的待办
- 不得照抄 `references/output_schema.json` 或 `references/output_example.json` 中的枚举说明、占位值或示例值；必须按当前邮件实际内容填写
- 默认分析范围是"近 7 日 + 消息级，必要时近似线程归并"
- 冲突处理固定"规则优先于 AI"
- 不暴露链路级内部推理，仅给简短判定依据摘要
- `is_closed = true` 时必须同时返回 `closure_signal` 和 `closure_reason`

Implementation constants (do not override unless user explicitly asks):
- `DEFAULT_WINDOW_DAYS = 7`
- `DEFAULT_PROCESSING_UNIT = message_with_heuristic_threading`
- `DEFAULT_PRIORITY = medium`
- `DEFAULT_NEED_REPLY = no`
- `DEFAULT_RESPONSE_WINDOW_BY_FOCUS = { 求职: 7, 学校: 5, 工作: 3, 通用: 5 }`
- `DECISION_PRECEDENCE = explicit_user_rules > memory_user_rules > built_in_rules > ai_judgment`
- `USER_RULES_PRECEDENCE = sender_rules > domain_rules > keyword_rules > default_priority`

## 参考文件使用与统一降级规则
在以下场景必须读取对应参考文件：
- 做优先级与待回复判定时：先执行本文件中的内联规则，再读取 `references/priority_rules.md` 做补充细化
- 涉及发送、回复草稿生成、隐私、敏感邮件、降级策略时：读取 `references/safety_and_fallback.md`
- 需要输出结构化结果时：先读取 `references/output_schema.json` 确认字段结构、必填项和枚举约束；若需要参考输出外形，再读取 `references/output_example.json`

统一降级规则：
- 主文档中的内联规则是最低可执行集合；参考文件只用于补充、示例和细化
- 若 `references/priority_rules.md` 缺失或加载失败，仍必须按主文档完成 `priority`、`need_reply`、闭环和响应窗口判断，不得输出空白或放弃分类
- 若 `references/safety_and_fallback.md` 缺失或加载失败，仍必须遵守主文档中的自动发送边界、中文草稿质量规范与保守降级要求
- 若 `references/output_schema.json` 缺失或加载失败，仍必须先输出自然语言结果；结构化部分只输出可可靠确定的字段，不得伪造字段或因 schema 缺失而中止分诊
- 若 `references/output_example.json` 缺失或加载失败，仍必须按 `references/output_schema.json` 的字段与枚举约束输出；不得因为示例缺失而回退到旧模板抄写
- 若外部能力不可用，回退到规则引擎 + 模板提取，不伪造细节
- 若存在冲突，优先保留显式用户规则与更保守的默认结论

## 失败降级与安全边界
- 正文解析失败：仅输出元数据和保守结论，标记需人工复核。
- 附件解析失败：保留附件名称/类型，标记 `manual_review_needed=true`。
- 草稿生成信息不足：回退到"回复提纲 + 待确认信息"，不得伪造日期、附件、金额、承诺内容。
- 置信度低：优先给 `medium` 或 `review_needed=true`，避免过度自信。

自动发送边界：
- 默认关闭自动发送。
- 仅可生成草稿/提纲；发送必须用户显式确认。
- 首次联系、付款、合同、证件、账号安全类邮件禁止自动发送。

## 快速示例
示例 1：
"整理今天邮件并给优先回复列表，输出中文说明和 JSON。"

示例 2：
"判断这个线程要不要回复，并给出理由摘要。"

示例 3：
"给这封 HR 邮件生成中文回复提纲，不要直接发送。"

示例 4（闭环检测）：
"整理近 7 天邮件，标注哪些线程已闭环、哪些还需处理，输出看板。"
