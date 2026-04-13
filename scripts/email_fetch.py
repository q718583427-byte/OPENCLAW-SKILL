#!/usr/bin/env python3
"""
email_fetch - Fetch emails by date range, account, with body truncation.

Usage:
    python email_fetch.py --config CONFIG --output OUTPUT [--days DAYS]

Options:
    --config CONFIG       JSON file with email account configuration
    --output OUTPUT       Output JSON file for fetched emails
    --days DAYS           Number of days to look back [default: 7]
    --account ACCOUNT     Specific account ID to fetch [default: all]
    --limit LIMIT         Max emails per account [default: 100]
    --body-chars CHARS    Max body characters [default: 1500]

Example CONFIG format:
{
    "email_accounts": {
        "qq": {
            "enabled": true,
            "consent_granted": true,
            "imap_host": "imap.qq.com",
            "imap_port": 993,
            "imap_username": "user@qq.com",
            "imap_password": "...",
            "imap_mailbox": "INBOX"
        }
    }
}
"""

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    import imaplib
    import email
    from email.header import decode_header
except ImportError:
    print("Error: 'email' and 'imaplib' modules are required. Run: pip install imaplib-email")
    sys.exit(1)


def decode_email_header(header):
    """Decode email header."""
    if header is None:
        return ""
    decoded_parts = []
    for part, charset in decode_header(header):
        if isinstance(part, bytes):
            charset = charset or 'utf-8'
            try:
                decoded_parts.append(part.decode(charset, errors='replace'))
            except (LookupError, UnicodeDecodeError):
                decoded_parts.append(part.decode('utf-8', errors='replace'))
        else:
            decoded_parts.append(str(part))
    return ''.join(decoded_parts)


def parse_email_date(date_str):
    """Parse email date string to datetime."""
    formats = [
        '%a, %d %b %Y %H:%M:%S %z',
        '%d %b %Y %H:%M:%S %z',
        '%a, %d %b %Y %H:%M:%S %Z',
        '%d %b %Y %H:%M:%S %Z',
    ]
    date_str = date_str.strip()
    for fmt in formats:
        try:
            return datetime.strptime(date_str, fmt).replace(tzinfo=None)
        except ValueError:
            continue
    # Try generic parsing
    try:
        return email.utils.parsedate_to_datetime(date_str).replace(tzinfo=None)
    except Exception:
        return None


def fetch_emails_from_account(account_config, days, limit, body_chars):
    """Fetch emails from a single email account."""
    results = {
        "account_id": account_config.get("account_id", "unknown"),
        "status": "success",
        "count": 0,
        "emails": [],
        "error": None
    }

    try:
        # Connect to IMAP server
        host = account_config["imap_host"]
        port = account_config.get("imap_port", 993)
        username = account_config["imap_username"]
        password = account_config["imap_password"]
        mailbox = account_config.get("imap_mailbox", "INBOX")
        use_ssl = account_config.get("imap_use_ssl", True)

        if use_ssl:
            mail = imaplib.IMAP4_SSL(host, port)
        else:
            mail = imaplib.IMAP4(host, port)

        mail.login(username, password)
        mail.select(mailbox)

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Search emails by date
        date_str = start_date.strftime("%d-%b-%Y")
        status, message_ids = mail.search(None, f'SINCE {date_str}')

        if status != "OK":
            results["status"] = "failed"
            results["error"] = f"Search failed: {message_ids}"
            return results

        email_ids = message_ids[0].split()
        results["count"] = len(email_ids)

        # Fetch emails up to limit
        for email_id in email_ids[:limit]:
            try:
                status, msg_data = mail.fetch(email_id, '(RFC822.2)')
                if status != "OK":
                    continue

                raw_email = msg_data[0][1]
                msg = email.message_from_bytes(raw_email)

                # Extract email metadata
                subject = decode_email_header(msg.get("Subject", ""))
                sender = decode_email_header(msg.get("From", ""))
                date = parse_email_date(msg.get("Date", ""))
                message_id = msg.get("Message-ID", "")
                in_reply_to = msg.get("In-Reply-To", "")
                references = msg.get("References", "")

                # Extract body
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        content_type = part.get_content_type()
                        if content_type == "text/plain":
                            charset = part.get_content_charset() or 'utf-8'
                            try:
                                body = part.get_payload(decode=True).decode(charset, errors='replace')[:body_chars]
                            except Exception:
                                body = str(part.get_payload(decode=True))[:body_chars]
                            break
                else:
                    charset = msg.get_content_charset() or 'utf-8'
                    try:
                        body = msg.get_payload(decode=True).decode(charset, errors='replace')[:body_chars]
                    except Exception:
                        body = str(msg.get_payload())[:body_chars]

                # Extract attachments metadata
                attachments = []
                for part in msg.walk():
                    content_disposition = part.get("Content-Disposition", "")
                    if "attachment" in content_disposition:
                        filename = decode_email_header(part.get_filename("") or "")
                        if filename:
                            attachments.append({
                                "name": filename,
                                "type": part.get_content_type(),
                                "size": len(part.get_payload(decode=True) or b'')
                            })

                # Extract reply headers
                reply_headers = {
                    "message_id": message_id,
                    "in_reply_to": in_reply_to,
                    "references": references
                }

                email_data = {
                    "message_id": message_id,
                    "account_id": account_config.get("account_id", "unknown"),
                    "subject": subject,
                    "sender": sender,
                    "date": date.isoformat() if date else None,
                    "body_snippet": body[:500] if body else "",
                    "body_full": body,
                    "reply_headers": reply_headers,
                    "attachments": attachments,
                    "uid": email_id.decode() if isinstance(email_id, bytes) else str(email_id)
                }

                results["emails"].append(email_data)

            except Exception as e:
                continue

        mail.logout()

    except Exception as e:
        results["status"] = "failed"
        results["error"] = str(e)

    return results


def main():
    parser = argparse.ArgumentParser(description="Fetch emails from configured accounts")
    parser.add_argument("--config", required=True, help="JSON config file with email accounts")
    parser.add_argument("--output", required=True, help="Output JSON file")
    parser.add_argument("--days", type=int, default=7, help="Days to look back [default: 7]")
    parser.add_argument("--account", default=None, help="Specific account ID [default: all]")
    parser.add_argument("--limit", type=int, default=100, help="Max emails per account [default: 100]")
    parser.add_argument("--body-chars", type=int, default=1500, help="Max body characters [default: 1500]")

    args = parser.parse_args()

    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {args.config}")
        sys.exit(1)

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Get accounts to fetch
    email_accounts = config.get("email_accounts", {})
    if "email" in config and "email" not in email_accounts:
        # Single account format
        email_accounts = {"default": config.get("email")}

    all_results = []
    anchor_date = None

    for account_id, account_config in email_accounts.items():
        # Skip disabled or no consent accounts
        if not account_config.get("enabled", False):
            continue
        if not account_config.get("consent_granted", False):
            continue

        # Skip if specific account requested
        if args.account and args.account != account_id:
            continue

        account_config["account_id"] = account_id
        result = fetch_emails_from_account(account_config, args.days, args.limit, args.body_chars)

        if result["status"] == "success" and result["emails"]:
            if anchor_date is None:
                # Use first successful fetch date as anchor
                for email_data in result["emails"]:
                    if email_data.get("date"):
                        anchor_date = email_data["date"][:10]
                        break

        all_results.append(result)

    # Write output
    output_data = {
        "status": "completed",
        "window_days": args.days,
        "anchor_date": anchor_date,
        "accounts": all_results
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"Fetched emails saved to {args.output}")


if __name__ == "__main__":
    main()
