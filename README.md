# email-triage-openclaw

Platform-agnostic email triage skill compatible with Open CLAW and other CLAW-compatible agent runtimes.

## Overview

This skill helps you quickly identify which emails need attention across recent threads, avoid missed deadlines, and get Chinese reply-ready summaries, dashboards, and draft suggestions.

## Features

- **Thread Priority Classification** — `high | medium | low`
- **Reply Detection** — `need_reply: yes | no`
- **Thread Closure Detection** — `is_closed: true | false` with closure signals
- **Key Information Extraction** — deadlines, todos, entities, attachment metadata
- **Chinese Reply Draft Generation** — draft-ready, not auto-sent
- **Dashboard Organization** — priority lists, deadline threads, closed threads

## Capability Requirements

This skill requires an email runtime with these capabilities:

| Capability | Description |
|------------|-------------|
| `email_accounts` | IMAP + SMTP multi-account configuration (QQ, 163, Gmail, etc.) |
| `email_fetch` | Fetch emails by date range, account filtering, body truncation, attachment metadata |
| `attachment_extract` | Read PDF / DOCX / XLSX attachment content |
| `thread_inspect` | Inspect thread history, access INBOX/Sent folders, get reply headers |

## Usage

Trigger with `$email-triage-openclaw` or `$email-triage-openclaw <request>`.

### Examples

```
整理今天邮件并告诉先处理什么
帮我找出最近7天最容易漏掉的deadline和待回复
判断这个线程要不要回复，给我一个能直接改的中文草稿
按优先级汇总最近7天邮件，给我一个看板
```

## Files

```
email-triage-openclaw/
├── SKILL.md                      # Main skill definition
└── references/
    ├── output_schema.json         # JSON output schema
    ├── output_example.json        # Output example
    ├── priority_rules.md          # Detailed priority rules
    └── safety_and_fallback.md     # Safety guidelines
```

## Output Format

The skill outputs:
1. Natural language summary (Chinese)
2. Structured JSON dashboard with priority classifications

## License

MIT
