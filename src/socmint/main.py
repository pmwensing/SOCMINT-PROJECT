#!/usr/bin/env python3
"""
SOCMINT Dossier Generator

This script generates a full profile dossier using open-source tools.
"""

import argparse
import subprocess
import json
import re
import logging
import sys
import tempfile
import os
import secrets
import string
from email_validator import validate_email, EmailNotValidError
import phonenumbers
from .backup import create_backup, restore_backup
from .config import configure_logging, load_settings
from .database import (
    configure_database,
    create_user,
    get_dossier,
    get_user_by_username,
    save_dossier,
)
from .enrichment import enrich_dossier
from .dashboard import create_app

logger = logging.getLogger(__name__)


def generate_password(length=24):
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    while True:
        password = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in password)
            and any(c.isupper() for c in password)
            and any(c.isdigit() for c in password)
            and any(c in "!@#$%^&*()-_=+" for c in password)
        ):
            return password


def generate_secrets():
    return {
        "SOCMINT_SECRET_KEY": secrets.token_urlsafe(48),
        "SOCMINT_ADMIN_PASSWORD": generate_password(),
        "SOCMINT_SIGNUP_INVITE_CODE": secrets.token_urlsafe(24),
        "SOCMINT_BACKUP_PASSPHRASE": secrets.token_urlsafe(48),
        "POSTGRES_PASSWORD": generate_password(32),
    }


def validate_target(target):
    if not target or len(target) > 100:
        raise ValueError("Target must be 1-100 characters.")
    if re.search(r"[;&|]", target):  # Block shell metachars
        raise ValueError("Invalid characters in target.")
    return target


def detect_type(target):
    try:
        validate_email(target, check_deliverability=False)
        return "email"
    except EmailNotValidError:
        pass
    try:
        parsed = phonenumbers.parse(target)
        if phonenumbers.is_valid_number(parsed):
            return "phone"
    except phonenumbers.NumberParseException:
        pass
    if re.match(r"^[a-zA-Z0-9_.-]+$", target):  # Basic username check
        return "username"
    raise ValueError("Invalid target format.")


def run_command(command, tool_name):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            error_text = (
                result.stderr.strip()
                or f"{tool_name} failed with exit code {result.returncode}"
            )
            logging.error(f"{tool_name} error: {error_text}")
            return error_text
        logging.info(f"{tool_name} completed successfully")
        return result.stdout
    except subprocess.TimeoutExpired:
        logging.error(f"{tool_name} timed out")
        return f"{tool_name} timed out"
    except FileNotFoundError:
        logging.warning(f"{tool_name} not installed")
        return f"{tool_name} not installed. Install the required package."
    except Exception as e:
        logging.error(f"Error running {tool_name}: {e}")
        return f"Error running {tool_name}: {str(e)}"


def run_sherlock(username):
    return run_command(["sherlock", username], "Sherlock")


def run_theharvester(domain):
    return run_command(["theHarvester", "-d", domain, "-b", "all"], "theHarvester")


def run_holehe(email):
    return run_command(["holehe", email], "Holehe")


def run_maigret(username):
    return run_command(["python", "-m", "maigret", username, "--json"], "Maigret")


def run_socialscan(username):
    return run_command(["socialscan", username, "--json"], "Socialscan")


def run_social_analyzer(username):
    return run_command(
        ["social-analyzer", "--username", username, "--metadata"], "Social Analyzer"
    )


def run_instaloader(username):
    return run_command(["instaloader", username, "--json"], "Instaloader")


def run_spiderfoot(target):
    return run_command(
        ["spiderfoot", "-s", target, "-t", "all", "-f", "json"], "Spiderfoot"
    )


def run_recon_ng(target):
    script_path = None
    try:
        script = (
            f"workspaces create {target}\n"
            f"use recon/domains-hosts/bing_domain_web\n"
            f"set SOURCE {target}\n"
            "run\n"
            "exit"
        )
        with tempfile.NamedTemporaryFile(
            "w", prefix="socmint-recon-", suffix=".rc", delete=False
        ) as f:
            script_path = f.name
            f.write(script)
        os.chmod(script_path, 0o600)
        return run_command(["recon-ng", "-r", script_path], "Recon-ng")
    except FileNotFoundError:
        return "Recon-ng not installed. sudo apt install recon-ng"
    except Exception as e:
        logging.error(f"Error running Recon-ng: {e}")
        return f"Error: {str(e)}"
    finally:
        if script_path and os.path.exists(script_path):
            os.unlink(script_path)


def run_phoneinfoga(phone):
    return run_command(["phoneinfoga", "scan", "-n", phone, "--json"], "PhoneInfoga")


def serve_dashboard():
    app = create_app()
    app.run(host="127.0.0.1", port=5000)


def init_admin(username, password):
    configure_database(load_settings(require_secret=False).database_url)
    if get_user_by_username(username):
        print(f"Admin user already exists: {username}")
        return
    create_user(username, password, is_admin=True)
    print(f"Admin user created: {username}")


def should_run_tool(tool_name, enabled_tools):
    return enabled_tools is None or tool_name in enabled_tools


def build_dossier(target, target_type, enabled_tools=None):
    dossier = {"target": target, "data": {}}

    if target_type == "email":
        email = target
        username = email.split("@")[0]
        domain = email.split("@")[1]
        dossier.update(
            {"type": "email", "email": email, "username": username, "domain": domain}
        )
        if should_run_tool("holehe", enabled_tools):
            dossier["data"]["holehe"] = run_holehe(email)
        if should_run_tool("theharvester", enabled_tools):
            dossier["data"]["theharvester"] = run_theharvester(domain)
        if should_run_tool("sherlock", enabled_tools):
            dossier["data"]["sherlock"] = run_sherlock(username)
        if should_run_tool("maigret", enabled_tools):
            dossier["data"]["maigret"] = run_maigret(username)
        if should_run_tool("socialscan", enabled_tools):
            dossier["data"]["socialscan"] = run_socialscan(username)
        if should_run_tool("social_analyzer", enabled_tools):
            dossier["data"]["social_analyzer"] = run_social_analyzer(username)
        if should_run_tool("instaloader", enabled_tools):
            dossier["data"]["instaloader"] = run_instaloader(username)
        if should_run_tool("spiderfoot", enabled_tools):
            dossier["data"]["spiderfoot"] = run_spiderfoot(email)
        if should_run_tool("recon_ng", enabled_tools):
            dossier["data"]["recon_ng"] = run_recon_ng(domain)
    elif target_type == "phone":
        dossier.update({"type": "phone", "phone": target})
        if should_run_tool("phoneinfoga", enabled_tools):
            dossier["data"]["phoneinfoga"] = run_phoneinfoga(target)
    elif target_type == "username":
        dossier.update({"type": "username", "username": target})
        if should_run_tool("sherlock", enabled_tools):
            dossier["data"]["sherlock"] = run_sherlock(target)
        if should_run_tool("maigret", enabled_tools):
            dossier["data"]["maigret"] = run_maigret(target)
        if should_run_tool("socialscan", enabled_tools):
            dossier["data"]["socialscan"] = run_socialscan(target)
        if should_run_tool("social_analyzer", enabled_tools):
            dossier["data"]["social_analyzer"] = run_social_analyzer(target)
        if should_run_tool("instaloader", enabled_tools):
            dossier["data"]["instaloader"] = run_instaloader(target)
        if should_run_tool("spiderfoot", enabled_tools):
            dossier["data"]["spiderfoot"] = run_spiderfoot(target)
        if should_run_tool("recon_ng", enabled_tools):
            dossier["data"]["recon_ng"] = run_recon_ng(target)
    else:
        raise ValueError(f"Unknown target type: {target_type}")

    return dossier


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "generate-secrets":
        for key, value in generate_secrets().items():
            print(f"{key}={value}")
        return

    configure_logging(load_settings(require_secret=False))

    if len(sys.argv) > 1 and sys.argv[1] == "process-jobs":
        from .jobs import process_scan_jobs

        parser = argparse.ArgumentParser(description="Process queued SOCMINT scan jobs")
        parser.add_argument("--max-jobs", type=int, default=1)
        args = parser.parse_args(sys.argv[2:])
        configure_database(load_settings(require_secret=False).database_url)
        processed = process_scan_jobs(max_jobs=args.max_jobs)
        print(json.dumps(processed, indent=2))
        return

    if len(sys.argv) > 1 and sys.argv[1] == "dashboard":
        parser = argparse.ArgumentParser(description="Launch the SOCMINT dashboard")
        parser.add_argument("--host", default="127.0.0.1", help="Dashboard bind host")
        parser.add_argument(
            "--port", default=5000, type=int, help="Dashboard bind port"
        )
        args = parser.parse_args(sys.argv[2:])
        app = create_app()
        app.run(host=args.host, port=args.port)
        return

    if len(sys.argv) > 1 and sys.argv[1] == "init-admin":
        parser = argparse.ArgumentParser(description="Create a SOCMINT admin user")
        parser.add_argument("username", help="Admin username")
        parser.add_argument("password", help="Admin password")
        args = parser.parse_args(sys.argv[2:])
        init_admin(args.username, args.password)
        return

    if len(sys.argv) > 1 and sys.argv[1] == "backup":
        parser = argparse.ArgumentParser(
            description="Create an encrypted SOCMINT database backup"
        )
        parser.add_argument("destination", help="Backup output path")
        parser.add_argument(
            "--no-encrypt", action="store_true", help="Write an unencrypted backup"
        )
        args = parser.parse_args(sys.argv[2:])
        output = create_backup(args.destination, encrypt=not args.no_encrypt)
        print(f"Backup written to {output}")
        return

    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        parser = argparse.ArgumentParser(
            description="Restore a SOCMINT database backup"
        )
        parser.add_argument("source", help="Backup path to restore")
        parser.add_argument(
            "--no-decrypt", action="store_true", help="Restore an unencrypted backup"
        )
        args = parser.parse_args(sys.argv[2:])
        database_url = restore_backup(args.source, encrypted=not args.no_decrypt)
        print(f"Restored backup into {database_url}")
        return

    parser = argparse.ArgumentParser(
        description="SOCMINT Full Profile Dossier Generator"
    )
    parser.add_argument(
        "target", nargs="?", help="Target username, email, or phone for dossier"
    )
    parser.add_argument(
        "--retrieve",
        action="store_true",
        help="Retrieve existing dossier from database",
    )
    parser.add_argument(
        "--serve", action="store_true", help="Launch the local dashboard"
    )
    parser.add_argument(
        "--no-enrich", action="store_true", help="Skip enrichment and media scraping"
    )
    parser.add_argument(
        "--tools",
        help="Comma-separated tool names to run, for example sherlock,maigret",
    )
    parser.add_argument(
        "--output-json",
        action="store_true",
        help="Print only the generated dossier JSON",
    )
    parser.add_argument(
        "--export", help="Write the generated dossier JSON to the given path"
    )
    args = parser.parse_args()

    if args.serve:
        print("Starting SOCMINT dashboard on http://127.0.0.1:5000")
        serve_dashboard()
        return

    if args.retrieve:
        if not args.target:
            print("Error: Provide target to retrieve")
            return
        dossier = get_dossier(args.target)
        if dossier:
            print("Retrieved dossier:")
            print(json.dumps(dossier, indent=4))
        else:
            print(f"No dossier found for {args.target}")
        return

    if not args.target:
        print("Error: Provide target")
        return

    try:
        args.target = validate_target(args.target)
        target_type = detect_type(args.target)
    except ValueError as e:
        print(f"Error: {e}")
        return

    enabled_tools = None
    if args.tools:
        enabled_tools = {tool.strip() for tool in args.tools.split(",") if tool.strip()}

    if not args.output_json:
        print(f"Generating dossier for {args.target}")
    dossier = build_dossier(args.target, target_type, enabled_tools=enabled_tools)

    if not args.no_enrich:
        dossier = enrich_dossier(dossier)

    output = json.dumps(dossier, indent=4)
    if args.export:
        with open(args.export, "w") as f:
            f.write(output)
            f.write("\n")

    if args.output_json:
        print(output)
    else:
        print("Dossier generated:")
        print(output)
    save_dossier(dossier)


if __name__ == "__main__":
    main()
