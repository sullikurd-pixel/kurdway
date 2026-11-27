"""Opt-in SMTP delivery for loopback development. Credentials never in repository."""
import os, json, ssl, smtplib, getpass
from pathlib import Path
from email.message import EmailMessage
from email_validator import validate_email

CONFIG = Path.home()/".kurdway"/"smtp.json"

def settings():
    if not CONFIG.exists():
        return None
    if CONFIG.is_symlink() or CONFIG.stat().st_mode & 0o077:
        raise RuntimeError("SMTP config must be private")
    return json.loads(CONFIG.read_text())

def tls_context():
    context = ssl.create_default_context()
    try:
        import certifi
    except ImportError:
        return context
    context.load_verify_locations(cafile=certifi.where())
    return context

def deliver(email,code,config):
    message=EmailMessage()
    message["From"]=config["sender"]
    message["To"]=email
    message["Subject"]="KURDWAY | Your sign-in code"
    message.set_content("Your KURDWAY sign-in code is "+code+". It expires in five minutes. Do not share it. If you did not request it, ignore this email.")
    with smtplib.SMTP(config["host"],587,timeout=10) as smtp:
        smtp.ehlo()
        smtp.starttls(context=tls_context())
        smtp.ehlo()
        smtp.login(config["username"],config["password"])
        smtp.send_message(message)

def setup():
    from database import initialize
    initialize()
    host=input("SMTP host [smtp.simply.com]: ").strip() or "smtp.simply.com"
    username=input("SMTP username [post@kurdway.com]: ").strip() or "post@kurdway.com"
    sender=validate_email((input("Authorized sender email [post@kurdway.com]: ").strip() or "post@kurdway.com"),check_deliverability=False).normalized
    password=getpass.getpass("Mailbox password (hidden): ")
    if not host or not username or not password:
        raise SystemExit("Missing settings")
    with smtplib.SMTP(host,587,timeout=10) as smtp:
        smtp.ehlo()
        smtp.starttls(context=tls_context())
        smtp.ehlo()
        smtp.login(username,password)
    fd=os.open(CONFIG,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,"w") as f:
        json.dump(dict(host=host,username=username,sender=sender,password=password),f)
    print("SMTP authentication successful. Restart KURDWAY. Delivery still needs testing.")

if __name__=="__main__":
    try:
        setup()
    except ssl.SSLCertVerificationError:
        raise SystemExit("TLS certificate verification failed. Update trusted CA certificates; never disable verification.")
    except smtplib.SMTPAuthenticationError:
        raise SystemExit("SMTP authentication failed. Check mailbox credentials in Simply Webmail.")
    except (OSError, smtplib.SMTPException):
        raise SystemExit("SMTP connection failed. Check server settings and network.")
