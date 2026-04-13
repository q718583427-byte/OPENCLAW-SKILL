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

## Installation

```bash
# Clone the skill
git clone -b master https://github.com/q718583427-byte/OPENCLAW-SKILL.git

# Install Python dependencies
cd OPENCLAW-SKILL/email-triage-openclaw
pip install -r requirements.txt
```

## IMAP Configuration

This skill supports multiple email providers. Configure your accounts in a JSON file:

### Gmail

```json
{
  "email_accounts": {
    "gmail": {
      "enabled": true,
      "consent_granted": true,
      "account_id": "gmail",
      "imap_host": "imap.gmail.com",
      "imap_port": 993,
      "imap_username": "your_email@gmail.com",
      "imap_password": "YOUR_APP_PASSWORD",
      "imap_mailbox": "INBOX",
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "smtp_username": "your_email@gmail.com",
      "smtp_password": "YOUR_APP_PASSWORD",
      "from_address": "your_email@gmail.com"
    }
  }
}
```

**Note:** Gmail requires an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular password. Enable 2FA first, then generate an App Password.

### Outlook / Hotmail

```json
{
  "email_accounts": {
    "outlook": {
      "enabled": true,
      "consent_granted": true,
      "account_id": "outlook",
      "imap_host": "outlook.office365.com",
      "imap_port": 993,
      "imap_username": "your_email@outlook.com",
      "imap_password": "YOUR_APP_PASSWORD",
      "imap_mailbox": "INBOX",
      "smtp_host": "smtp.office365.com",
      "smtp_port": 587,
      "smtp_username": "your_email@outlook.com",
      "smtp_password": "YOUR_APP_PASSWORD",
      "from_address": "your_email@outlook.com"
    }
  }
}
```

**Note:** Microsoft accounts may require an [App Password](https://support.microsoft.com/en-us/account-billing/how-to-get-two-step-verification-codes-6a18f098-d421-4e9d-b62a-6048dddf930c) if 2FA is enabled.

### 163.com (网易邮箱)

```json
{
  "email_accounts": {
    "163": {
      "enabled": true,
      "consent_granted": true,
      "account_id": "163",
      "imap_host": "imap.163.com",
      "imap_port": 993,
      "imap_username": "your_email@163.com",
      "imap_password": "YOUR_AUTHORIZATION_CODE",
      "imap_mailbox": "INBOX",
      "smtp_host": "smtp.163.com",
      "smtp_port": 465,
      "smtp_username": "your_email@163.com",
      "smtp_password": "YOUR_AUTHORIZATION_CODE",
      "from_address": "your_email@163.com"
    }
  }
}
```

**Note:** 163邮箱需要开启 IMAP/SMTP 服务并获取[授权码](https://mail.163.com/html/addition/2016/08/201608241726560011_0.html)。

### QQ 邮箱

```json
{
  "email_accounts": {
    "qq": {
      "enabled": true,
      "consent_granted": true,
      "account_id": "qq",
      "imap_host": "imap.qq.com",
      "imap_port": 993,
      "imap_username": "your_email@qq.com",
      "imap_password": "YOUR_AUTHORIZATION_CODE",
      "imap_mailbox": "INBOX",
      "smtp_host": "smtp.qq.com",
      "smtp_port": 587,
      "smtp_username": "your_email@qq.com",
      "smtp_password": "YOUR_AUTHORIZATION_CODE",
      "from_address": "your_email@qq.com"
    }
  }
}
```

**Note:** QQ邮箱需要开启 IMAP/SMTP 服务并获取[授权码](https://service.mail.qq.com/cgi-bin/help?subtype=1&&no=1001256&&id=28)。

### Multi-Account Configuration

```json
{
  "email_accounts": {
    "qq": {
      "enabled": true,
      "consent_granted": true,
      "account_id": "qq",
      "imap_host": "imap.qq.com",
      "imap_port": 993,
      "imap_username": "your_email@qq.com",
      "imap_password": "YOUR_AUTHORIZATION_CODE",
      "imap_mailbox": "INBOX",
      "smtp_host": "smtp.qq.com",
      "smtp_port": 587,
      "smtp_username": "your_email@qq.com",
      "smtp_password": "YOUR_AUTHORIZATION_CODE",
      "from_address": "your_email@qq.com"
    },
    "gmail": {
      "enabled": true,
      "consent_granted": true,
      "account_id": "gmail",
      "imap_host": "imap.gmail.com",
      "imap_port": 993,
      "imap_username": "your_email@gmail.com",
      "imap_password": "YOUR_APP_PASSWORD",
      "imap_mailbox": "INBOX",
      "smtp_host": "smtp.gmail.com",
      "smtp_port": 587,
      "smtp_username": "your_email@gmail.com",
      "smtp_password": "YOUR_APP_PASSWORD",
      "from_address": "your_email@gmail.com"
    }
  }
}
```

## Usage

### Using Scripts Directly

```bash
# Fetch emails from configured accounts
python scripts/email_fetch.py \
  --config config.json \
  --output emails.json \
  --days 7 \
  --limit 100

# Extract content from an attachment
python scripts/attachment_extract.py \
  --input document.pdf \
  --output content.json

# Inspect a thread by Message-ID
python scripts/thread_inspect.py \
  --config config.json \
  --message-id "<abc123@example.com>" \
  --output thread.json
```

### Trigger Examples

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
├── scripts/
│   ├── email_fetch.py            # Email fetching tool
│   ├── attachment_extract.py     # Attachment extraction tool
│   └── thread_inspect.py         # Thread inspection tool
├── references/
│   ├── output_schema.json        # JSON output schema
│   ├── output_example.json        # Output example
│   ├── priority_rules.md          # Detailed priority rules
│   └── safety_and_fallback.md     # Safety guidelines
└── requirements.txt              # Python dependencies
```

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| PyMuPDF | >=1.23.0 | PDF extraction |
| python-docx | >=1.0.0 | DOCX extraction |
| openpyxl | >=3.1.0 | XLSX extraction |

## License

MIT
