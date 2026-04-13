#!/usr/bin/env python3
"""
thread_inspect - Inspect email thread history and sent items.

Usage:
    python thread_inspect.py --config CONFIG --message-id ID --output OUTPUT

Options:
    --config CONFIG       JSON file with email account configuration
    --message-id ID       Message-ID of the email to inspect
    --output OUTPUT       Output JSON file for thread results
    --account ACCOUNT     Account ID to search in [default: all]

Example:
    python thread_inspect.py --config emails.json --message-id "<abc@example.com>" --output thread.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import imaplib
    import email
    from email.header import decode_header
except ImportError:
    print("Error: 'email' and 'imaplib' modules are required.")
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
    try:
        return email.utils.parsedate_to_datetime(date_str).replace(tzinfo=None)
    except Exception:
        return None


def normalize_subject(subject):
    """Normalize subject for thread matching."""
    # Remove Re:, Fwd:, [List], etc.
    normalized = re.sub(r'^(Re:|Fwd?:|\[.*?\])\s*', '', subject, flags=re.IGNORECASE)
    return normalized.strip().lower()


def extract_references(message_id, in_reply_to, references):
    """Extract all referenced message IDs."""
    ref_ids = []

    if references:
        # References can be a space-separated list
        ref_ids.extend(references.strip().split())

    if in_reply_to:
        ref_ids.append(in_reply_to)

    return ref_ids


def search_in_mailbox(mail, mailbox, query):
    """Search emails in a mailbox."""
    try:
        status, message_ids = mail.search(None, query)
        if status != "OK":
            return []
        return message_ids[0].split()
    except Exception:
        return []


def inspect_thread(account_config, target_message_id, mailboxes):
    """Inspect thread for a specific message ID."""
    results = {
        "account_id": account_config.get("account_id", "unknown"),
        "target_message_id": target_message_id,
        "status": "success",
        "sent_items": [],
        "thread_replies": [],
        "user_replied": False,
        "error": None
    }

    try:
        host = account_config["imap_host"]
        port = account_config.get("imap_port", 993)
        username = account_config["imap_username"]
        password = account_config["imap_password"]
        use_ssl = account_config.get("imap_use_ssl", True)

        if use_ssl:
            mail = imaplib.IMAP4_SSL(host, port)
        else:
            mail = imaplib.IMAP4(host, port)

        mail.login(username, password)

        # Parse target message references
        ref_ids = [target_message_id]
        target_normalized_subject = None

        # Search in each mailbox
        for mailbox_name in mailboxes:
            try:
                status, _ = mail.select(mailbox_name)
                if status != "OK":
                    continue

                # Method 1: Search by Message-ID in References
                query = f'HEADER References "{target_message_id}"'
                found_ids = search_in_mailbox(mail, mailbox_name, query)

                # Method 2: Search by In-Reply-To
                if not found_ids:
                    query = f'HEADER In-Reply-To "{target_message_id}"'
                    found_ids = search_in_mailbox(mail, mailbox_name, query)

                # Method 3: Search Sent items by subject similarity
                if mailbox_name.upper() in ("SENT", "已发送", '"Sent"'):
                    # Get target subject first by searching message-id directly
                    query = f'HEADER Message-ID "{target_message_id}"'
                    direct_ids = search_in_mailbox(mail, mailbox_name, query)

                    if direct_ids:
                        status, msg_data = mail.fetch(direct_ids[0], '(RFC822.2)')
                        if status == "OK":
                            raw_email = msg_data[0][1]
                            msg = email.message_from_bytes(raw_email)
                            target_normalized_subject = normalize_subject(
                                decode_email_header(msg.get("Subject", ""))
                            )

                    # Search for replied emails with same subject
                    if target_normalized_subject:
                        # Search all sent emails
                        status, all_sent = mail.search(None, "ALL")
                        if status == "OK":
                            for email_id in all_sent[0].split()[:500]:  # Limit search
                                status, msg_data = mail.fetch(email_id, '(RFC822.2)')
                                if status != "OK":
                                    continue
                                raw_email = msg_data[0][1]
                                msg = email.message_from_bytes(raw_email)
                                subject = decode_email_header(msg.get("Subject", ""))
                                if normalize_subject(subject) == target_normalized_subject:
                                    found_ids.append(email_id)

                # Fetch found emails
                for email_id in found_ids[:50]:  # Limit results
                    try:
                        status, msg_data = mail.fetch(email_id, '(RFC822.2)')
                        if status != "OK":
                            continue

                        raw_email = msg_data[0][1]
                        msg = email.message_from_bytes(raw_email)

                        email_info = {
                            "message_id": msg.get("Message-ID", ""),
                            "subject": decode_email_header(msg.get("Subject", "")),
                            "sender": decode_email_header(msg.get("From", "")),
                            "to": decode_email_header(msg.get("To", "")),
                            "date": None,
                            "in_reply_to": msg.get("In-Reply-To", ""),
                            "references": msg.get("References", ""),
                            "is_user_sent": False
                        }

                        date = parse_email_date(msg.get("Date", ""))
                        if date:
                            email_info["date"] = date.isoformat()

                        # Check if this is from user (sent items)
                        if mailbox_name.upper() in ("SENT", "已发送", '"Sent"'):
                            email_info["is_user_sent"] = True
                            results["sent_items"].append(email_info)

                            # Check if user replied
                            if email_info["in_reply_to"] == target_message_id:
                                results["user_replied"] = True
                        else:
                            results["thread_replies"].append(email_info)

                    except Exception:
                        continue

            except Exception as e:
                results["error"] = str(e)
                continue

        mail.logout()

    except Exception as e:
        results["status"] = "failed"
        results["error"] = str(e)

    return results


def main():
    parser = argparse.ArgumentParser(description="Inspect email thread history")
    parser.add_argument("--config", required=True, help="JSON config file with email accounts")
    parser.add_argument("--message-id", required=True, help="Message-ID to inspect")
    parser.add_argument("--output", required=True, help="Output JSON file")
    parser.add_argument("--account", default=None, help="Account ID to search [default: all]")

    args = parser.parse_args()

    # Load config
    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Error: Config file not found: {args.config}")
        sys.exit(1)

    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # Get accounts
    email_accounts = config.get("email_accounts", {})
    if "email" in config and "email" not in email_accounts:
        email_accounts = {"default": config.get("email")}

    # Default mailboxes to search
    default_mailboxes = ["INBOX", "SENT", "已发送"]

    all_results = []

    for account_id, account_config in email_accounts.items():
        if not account_config.get("enabled", False):
            continue
        if not account_config.get("consent_granted", False):
            continue

        if args.account and args.account != account_id:
            continue

        account_config["account_id"] = account_id
        result = inspect_thread(account_config, args.message_id, default_mailboxes)
        all_results.append(result)

    # Write output
    output_data = {
        "target_message_id": args.message_id,
        "accounts": all_results
    }

    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)

    print(f"Thread inspection saved to {args.output}")


if __name__ == "__main__":
    main()
