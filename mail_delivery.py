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

def send(email,subject,plain,html,config):
    from email.utils import formataddr
    message=EmailMessage()
    message["From"]=formataddr(("KURDWAY",config["sender"]))
    message["To"]=email
    message["Subject"]=subject
    message.set_content(plain)
    logo=Path.home()/".kurdway"/"brand-logo.jpg"
    logo_bytes=logo.read_bytes() if logo.is_file() and not logo.is_symlink() and logo.stat().st_size<2_000_000 else None
    if logo_bytes:
        html=html.replace("▲ KURDWAY",'<img src="cid:kurdway-brand" width="120" height="120" alt="KurdWay logo"><br>KURDWAY')
    message.add_alternative(html,subtype="html")
    if logo_bytes:
        message.get_payload()[-1].add_related(logo_bytes,maintype="image",subtype="jpeg",cid="<kurdway-brand>",disposition="inline")
    with smtplib.SMTP(config["host"],587,timeout=10) as smtp:
        smtp.ehlo()
        smtp.starttls(context=tls_context())
        smtp.ehlo()
        smtp.login(config["username"],config["password"])
        smtp.send_message(message)

def layout(title,body):
    return """<!doctype html><html lang="en"><body style="margin:0;background:#edf2ee;font-family:Arial,sans-serif;color:#18382b"><table role="presentation" width="100%" cellpadding="20"><tr><td align="center"><table role="presentation" width="100%" style="max-width:560px;background:white;border-radius:16px"><tr><td style="background:#153d2c;color:white;padding:30px;border-radius:16px 16px 0 0"><span style="font-size:28px;font-weight:bold">▲ KURDWAY</span><br><span style="font-size:13px">Nature belongs to everyone.</span></td></tr><tr><td style="padding:30px"><h1 style="font-size:24px">"""+title+"""</h1>"""+body+"""</td></tr><tr><td style="padding:24px;background:#f2f6f3;font-size:12px;color:#40584b">KURDWAY · Founder &amp; Developer: Sulli Kurd<br>Independent outdoor platform · Local development preview</td></tr></table></td></tr></table></body></html>"""

def deliver(email,code,config):
    if len(code)!=6 or not code.isascii() or not code.isdigit():
        raise ValueError("Invalid code")
    plain="Your KURDWAY sign-in code is "+code+". It expires in five minutes. Do not share it. If you did not request it, ignore this email."
    html=layout("Your sign-in code","<p>Enter this code in KURDWAY to verify your email and sign in.</p><p style='background:#e9f3ec;font-size:34px;font-weight:bold;letter-spacing:7px;padding:20px;text-align:center'>"+code+"</p><p>Valid for five minutes. Never share this code with anyone.</p><p>If you did not request this code, ignore this email.</p>")
    send(email,"KURDWAY | Your sign-in code",plain,html,config)

def welcome(email,config):
    plain="Welcome to KURDWAY! Your free account is ready. Save favorite places, record completed hikes and view your personal statistics. This is a local development preview, not a verified navigation service."
    html=layout("Welcome to KURDWAY","<p>Your free account is ready.</p><ul><li>Save your favorite places</li><li>Record your completed hikes</li><li>View your personal statistics</li></ul><p>We are building an independent outdoor community. This is a local development preview, not a verified navigation service.</p>")
    send(email,"Welcome to KURDWAY",plain,html,config)

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
