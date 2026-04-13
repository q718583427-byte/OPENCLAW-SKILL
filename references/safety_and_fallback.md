# Safety and Fallback Policy

## Auto-Send Policy
- Auto-send is OFF by default.
- Prefer draft/outline mode.
- Sending requires explicit user confirmation.

Never auto-send for:
- First-contact emails
- Payment-related emails
- Contract-related emails
- Identity/certificate/sensitive personal document emails
- Account security emails
- Ambiguous or low-confidence cases

## Draft Quality and Fallback
- Prefer a Chinese copy-ready draft when facts are sufficient.
- If the user explicitly asks for an outline, or facts are insufficient, return an outline plus a short "to confirm" list instead of forcing a full draft.
- Do not fabricate dates, attachments, amounts, promises, identities, availability, or meeting times.
- Avoid meta wording inside the draft body such as "here is a draft you can send".
- Keep the draft concise and directly responsive to the sender's asks.
- If placeholders are necessary, keep them explicit and minimal, and list them separately for user confirmation.
- If more than 3 key facts are missing, or the missing facts are sensitive, prefer outline mode over a send-ready draft.
- For first-contact, payment, contract, certificate, and account-security emails, keep wording conservative and require user review before any send action.

## Privacy Policy
- Minimize content exposure to third-party services.
- Extract only necessary fields when possible.
- Avoid retaining unnecessary raw sensitive content.
- Follow user/product privacy switches strictly.

## Attachment Safety
If attachment parsing is incomplete or unreliable:
- Keep file metadata (name/type)
- Do not fabricate details
- Mark `manual_review_needed = true`

## Conservative Downgrade Matrix

### Body parsing fails
Output only reliable metadata:
- sender
- timestamp
- subject
- mailbox/account metadata

Add note: "正文解析失败，请人工查看原邮件。"

### Attachment parsing fails
Output:
- attachment name
- attachment type

Set:
- `manual_review_needed = true`

### Low confidence
- Avoid strong conclusions.
- Prefer `priority = medium`.
- Set `review_needed = true`.
- Add short note: "优先级建议复核。"

### External intelligence unavailable
Fallback to:
- rule-based triage
- template extraction
- conservative labeling

Do not output fabricated confidence or fake extraction details.
