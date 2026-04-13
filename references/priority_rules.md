# Priority and Reply Rules

This file refines the inline rules in `SKILL.md`. If this file is missing or fails to load, the agent must still complete triage by following the inline rules in `SKILL.md`; `priority` and `need_reply` may not be left undefined.

## Rule Precedence
Always apply rules in this order:
1. Explicit user rules in the current request
2. Confirmed email-triage preferences from long-term memory
3. Built-in default rules (importance assessment, urgency assessment, and priority mapping)
4. `need_reply` assessment
5. Contextual AI judgment
6. Conservative downgrade when confidence is low

If explicit rules conflict with memory preferences or AI judgment, explicit rules win. Long-term memory may fill missing fields, but must not override explicit current-request rules.

## Default Baseline
- Start with `priority = explicit_user_rules.default_priority`; if absent, fall back to `memory_user_rules.default_priority`; if still absent, use `medium`.
- Start with `need_reply = no`.
- Internally separate `importance` and `urgency` even though the outward schema still returns only `priority`.
- When confidence is low, prefer `priority = medium` plus `review_needed = true`.
- Do not promote to `high` based on weak inference alone.

## User Rules Contract
Use `user_rules` as the user's personal priority profile. Recommended initial structure:

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
        "priority": "high"
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

Apply user rules in this order:
1. `sender_rules`
2. `domain_rules`
3. `keyword_rules`
4. `default_priority`

User rules only override fields they explicitly provide. Missing fields continue through the built-in default flow.
`response_window_days` is treated as a scalar default used for timeout and follow-up timing rather than as a per-message matching rule.

## Long-Term Memory Preferences

Use confirmed long-term memory preferences only as a default personalization layer for future triage runs.

Rules:
- Only explicitly confirmed preferences may be saved
- Do not auto-infer and persist preferences from a single triage result
- Reconstruct memory preferences into the same effective shape as `user_rules` when needed
- Current-request explicit rules always override memory preferences
- If memory preferences are clearly mismatched to the current task, fall back conservatively to built-in defaults and set `review_needed = true`

Recommended stable memory summary:
- `default_priority`
- `response_window_days`
- high-priority senders
- high-priority domains
- low-priority / no-reply keywords
- applicable `focus` using Chinese canonical values such as `求职`, `学校`, `工作`, or `通用`

## First-Use Soft Onboarding

When the user has not provided `user_rules` and no confirmed email-triage preferences exist in long-term memory, use soft onboarding for multi-thread triage requests.

Trigger when all are true:
- no explicit `user_rules`
- no confirmed email-triage preferences in long-term memory
- request is a multi-thread task such as full triage, recent 7-day review, dashboard, or priority reply list

Do not trigger when any is true:
- single-thread judgment or single-email draft request
- one-off Q&A request
- user already refused preference setup
- current request already includes `user_rules`

Output policy:
- Complete the triage first using built-in defaults
- Then append a short "first-use suggestion" block at the end of the natural-language response
- Keep the suggestion to 1-3 high-value setup directions only
- State that the current result has already been completed with default rules
- Invite the user to save preferences next time using natural language rather than requiring full JSON
- Do not change the JSON schema for onboarding
- If the user refuses setup, do not repeat the prompt again in the same session

## Thread-Level Policy
- Default to message-level evidence and only do heuristic thread grouping when `messageId / inReplyTo / references / normalized subject` support it.
- Do not claim exact mailbox-native thread reconstruction unless the underlying tool explicitly provides it.
- Default analysis window is recent 7 days.
- For cross-account triage scope, use `accounts` as the account-selection field for `email_fetch`.
- Use `mailboxes` only for mailbox-folder inspection such as `INBOX` or `Sent` when calling `email_thread_inspect`; do not treat `mailboxes` as a multi-account filter.
- If the user says "邮箱/账号/账户" in the sense of which account to inspect, normalize that request to `accounts`; only map to `mailboxes` when the user clearly means folders like inbox, sent, or mailbox names.

## Fetch Coverage Policy
- For recent 7-day complete triage, keep `limit=100` per account and use `bodyMaxChars=1500` as the default fetch depth.
- Coverage comes before body depth: do not sacrifice account/date coverage in order to read longer bodies in the first pass.
- If the deduplicated message set is still large, perform first-pass triage using `sender / subject / date / reply headers / body snippet / attachment metadata`.
- Only deepen inspection for high-priority candidates, reply-needed candidates, closure-ambiguous threads, or cases that clearly depend on full body / attachment details.

## Response Window Policy

Before using inactivity for urgency escalation, follow-up judgment, or closure detection, compute `effective_response_window_days`.

Precedence:
1. explicit `response_window_days` in the current request
2. `explicit_user_rules.response_window_days`
3. `memory_user_rules.response_window_days`
4. focus default
5. fallback default of `5`

Focus defaults:

| `focus` | `effective_response_window_days` |
|---|---|
| `求职` | `7` |
| `学校` | `5` |
| `工作` | `3` |
| `通用` | `5` |

Rules:
- Treat Chinese values as the only canonical stored form for `focus` in memory and rebuilt `user_rules`.
- Accept English aliases only as input normalization before judgment:
  - `job_search -> 求职`
  - `school -> 学校`
  - `work -> 工作`
  - `general -> 通用`
- If `focus` is unknown after normalization, fall back conservatively to `通用`.
- Interpret the window in natural calendar days unless the user explicitly asks for business-day logic.
- An explicit deadline overrides the generic response window.
- Do not mark a thread closed by inactivity if there is still an unanswered direct question, an open todo, a future deadline, or a promised next step.
- When timeout or overdue status is used in reasoning, mention both the value and the source of `effective_response_window_days`.

## Priority Decision Flow
1. Initialize `priority` from `explicit_user_rules.default_priority`; if absent, use `memory_user_rules.default_priority`; if still absent, use `medium`.
2. Initialize `need_reply = no`.
3. Initialize `effective_response_window_days` using the policy above.
4. Apply current-request explicit rules in the fixed order: `sender_rules > domain_rules > keyword_rules`.
5. If explicit rules do not fully determine the result and confirmed memory preferences exist, apply memory rules in the same fixed order.
6. If explicit rules and memory preferences do not fully determine the result, assess `importance` separately from `urgency`.
7. Map `importance` and `urgency` into final `priority` using the fixed matrix below.
8. If multiple signals conflict, prefer explicit user rules first, then confirmed memory preferences, otherwise prefer the more conservative built-in result.

## Importance Assessment

### `importance = high`
Use `high` importance when the thread itself is strategically important:
- Important sender: teacher, HR, interviewer, manager, client, core partner, user whitelist
- Important domain or institution: school, employer, government, finance, user-marked domain
- High-value topic: application outcome, approval, contract, payment, reimbursement, signature, account security
- The user is the primary owner and the outcome materially affects work, study, money, or collaboration

### `importance = medium`
Use `medium` importance when the thread matters but is not critical:
- School/job/work collaboration without major consequences
- Known teammate, classmate, vendor, or operational contact
- Worth reviewing and following up, but not a key relationship or key decision

### `importance = low`
Use `low` importance for low-value informational traffic:
- Marketing, promotion, newsletter, broadcast announcement
- Routine system notification, logistics reminder, ordinary billing notice
- CC-style thread where the user is not the main actor
- Pure background sync without clear business value

## Urgency Assessment

### `urgency = high`
Use `high` urgency when quick action is needed:
- Hard deadline, especially within 72 hours, or wording like "today", "tomorrow", "ASAP"
- Explicit request to confirm, reply, submit materials, schedule, approve, pay, or attend
- The thread blocks the next step and is waiting on the user
- Reminder/chaser signals exist, or `effective_response_window_days` has already been exceeded

### `urgency = medium`
Use `medium` urgency when action is needed soon but not immediately:
- Soft deadline such as "this week" or "when convenient"
- User action is needed, but not acting today is unlikely to cause immediate damage
- Scheduling, confirmation, or follow-up is needed without hard blocking pressure

### `urgency = low`
Use `low` urgency when no prompt action is required:
- No explicit deadline and no direct action request
- Informational, archival, reference-only, or passive update content
- Thread is already closed, or the user is not the primary actor

## Priority Mapping

Map the two internal dimensions to the outward `priority` field:

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

Additional rules:
- Current-request explicit user rules may directly override `priority` and `need_reply`.
- Confirmed memory preferences only fill gaps and must not override explicit current-request rules.
- Important sender alone does not automatically mean `priority = high`; low urgency can still map to `medium`.
- Urgent but low-value system traffic should not jump to `high`; cap it at `medium` unless user rules say otherwise.
- If the thread is not clearly classifiable, keep `priority = medium`.

## `need_reply` Binary Policy
Only use:
- `yes`
- `no`

Set `need_reply = yes` when:
- The sender asks a direct question
- Confirmation is requested
- Materials/availability/missing info are requested
- User is primary actor for a deadline-bound action and `urgency != low`
- A high-priority thread remains unhandled past `effective_response_window_days`

Set `need_reply = no` when:
- One-way announcement or FYI
- Thread is already closed
- The user is not the primary actor and no direct action is required
- The message is for archive/reference only

## Transparency Requirement
`reasoning_summary` should briefly state:
- whether the result mainly came from current-request explicit rules, long-term memory preferences, or built-in default rules
- the main signals that set `importance` and `urgency`
- how those two dimensions mapped into final `priority`
- when timeout or overdue logic is used, the applied `effective_response_window_days` and its source
- whether low confidence caused a conservative fallback

## Important Sender Identification
Treat sender as important if any is true:
- Explicit user whitelist match
- Teacher/school/university context
- HR/recruiter/interviewer/manager/client context
- User-marked important domain
- Historical user behavior repeatedly upgrades similar senders

Important sender is a strong `importance` cue, not an automatic `high` priority result by itself.

## Dashboard Modules
When user asks for inbox review, organize results into:
1. 今日优先回复
2. 高优先级未处理
3. 含 deadline 的线程
4. 已闭环线程（标注 closure_signal）
5. 按优先级分组概览
6. 待回复清单

## Thread Closure Detection

Apply this global protection gate before closing a thread:
- If there is still an unanswered direct question, an open todo, a future deadline, or a promised next step that has not been completed, do not mark `is_closed = true` from acknowledgment wording, conclusive wording, or inactivity alone.
- `timeout_inactive` must satisfy the strictest version of this gate and may not bypass it.
- Only `explicit_close` may close a thread that contains historical action items, and only when the close language clearly states the item is cancelled, finished, or no further action is needed.

Mark `is_closed = true` when any of the following signals is detected:

| closure_signal | Trigger Condition | Priority |
|----------------|-------------------|----------|
| `confirmed_by_recipient` | Recipient explicitly indicates handling/completion, or uses weak acknowledgments like "收到"、"好的"、"同意"、"已知悉" only when no unanswered question, open todo, future deadline, or promised next step remains | Highest |
| `user_handled` | `email_thread_inspect` or explicit user context confirms the user already replied/handled it | Highest |
| `action_completed` | Todo items marked as completed, cancelled, or expired | High |
| `timeout_inactive` | Thread has no new messages beyond `effective_response_window_days`, and also has no unanswered direct question, open todo, future deadline, or other strong open-thread signal | Medium |
| `explicit_close` | Any party explicitly states: "关闭"、"完结"、"无需回复"、"close"、"resolved", or clearly says the matter is cancelled or no longer needs follow-up | Highest |
| `resolution_detected` | Thread contains conclusive content: decision, answer, solution, final answer | High |

### Decision Rules
- If multiple signals conflict, use the **highest priority** signal.
- `is_closed = true` implies `need_reply = no` and `recommended_actions` must include `archive`.
- If no closure signal is detected, `is_closed = false` by default.
- When uncertain (low confidence), set `is_closed = false` and add `review_needed = true`.

## Todo Extraction Rules

**核心原则：只提取原文明确写明的待办，不推测，不过度解读。**

### 原文明确要求的待办（`origin: explicit`）
直接从邮件正文中提取以下句式：
- "请 XXX"、"请于 X 日前完成 XXX"
- "需要您 XXX"、"需要准备 XXX"
- "麻烦 XXX"、"麻烦尽快 XXX"
- "期待 XXX"、"希望 XXX"
- 明确的指令句式："发送 XXX"、"回复 XXX"、"提交 XXX"、"完成 XXX"

### 可以推断的待办（`origin: inferred`）
基于明确前提条件推断：
- 对方提出问题，等待用户给出答案/选择 → 推断"需要回复"（显式推断）
- 对方提供了材料清单，用户尚未确认 → 推断"需要确认材料"（低置信）

### 不应提取的待办
- "可能"、"也许"、"可以考虑"等模糊表述
- 对方自己的计划或动作（非用户动作）
- 泛泛的工作建议、方向性讨论
- 对方表达情绪或状态但不涉及具体行动

### 输出格式
```json
{
  "todo_items": [
    {
      "content": "请于周五前提交季度报告",
      "origin": "explicit",
      "deadline": "周五",
      "confidence": "high"
    },
    {
      "content": "需要确认对方是否收到材料",
      "origin": "inferred",
      "deadline": null,
      "confidence": "medium"
    }
  ]
}
```

### 置信度规则
- `high`：原文明确指令，有具体动作和对象
- `medium`：有明确前提条件支撑的推断，且逻辑链短
- `low`：模糊推断，仅凭"可能"类词汇，绝不生成低置信待办条目
