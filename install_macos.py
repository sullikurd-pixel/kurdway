"""Install a local macOS LaunchAgent for KURDWAY. No sudo required."""
import os, sys, plistlib, subprocess, time, json, urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LABEL = "com.kurdway.local"
DOMAIN = f"gui/{os.getuid()}"
TARGET = f"{DOMAIN}/{LABEL}"
HOME = Path.home()
PLIST = HOME / "Library/LaunchAgents" / (LABEL + ".plist")
LOG = HOME / ".kurdway" / "logs"
PORT = 8769

def run(*args, check=True):
    return subprocess.run(args, text=True, capture_output=True, check=check)

def listeners():
    return run("/usr/sbin/lsof", "-nP", "-iTCP:8769", "-sTCP:LISTEN", "-t", check=False).stdout.split()

def main():
    if sys.platform != "darwin":
        raise SystemExit("macOS only")
    from server import app
    from database import initialize
    initialize()
    LOG.mkdir(mode=0o700, exist_ok=True)
    if LOG.is_symlink() or PLIST.is_symlink():
        raise SystemExit("Unsafe path")
    os.chmod(LOG, 0o700)
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    # Stop only our own previously installed agent.
    run("/bin/launchctl", "bootout", TARGET, check=False)
    for _ in range(20):
        if not listeners():
            break
        time.sleep(.25)
    # Identify the prior listener and its launchd job, if any.
    jobs = run("/bin/launchctl", "list").stdout.splitlines()
    for pid in listeners():
        command = run("/bin/ps", "-ww", "-p", pid, "-o", "command=", check=False).stdout.strip()
        cwd = run("/usr/sbin/lsof", "-a", "-p", pid, "-d", "cwd", "-Fn", check=False).stdout
        print("Existing listener:", pid, command, cwd)
        if "uvicorn" not in command or "server:app" not in command or not any(
            line.startswith("n"+str(HOME/"KURDWAY")+"/") for line in cwd.splitlines()
        ):
            raise SystemExit("Unknown listener. No process stopped. Send this output.")
        labels = [parts[2] for line in jobs if len(parts:=line.split())==3 and parts[0]==pid]
        if labels:
            for label in labels:
                if "kurdway" not in label.lower():
                    raise SystemExit("Unknown launch agent: "+label+"; no process stopped.")
                run("/bin/launchctl","disable", f"{DOMAIN}/{label}")
                run("/bin/launchctl","bootout", f"{DOMAIN}/{label}")
        else:
            run("/bin/kill","-TERM",pid)
    for _ in range(40):
        if not listeners():
            break
        time.sleep(.25)
    if listeners():
        raise SystemExit("Port still occupied; old supervisor may be restarting. No new service installed.")
    config = {"Label": LABEL, "ProgramArguments": [sys.executable,"-m","uvicorn","server:app","--host","127.0.0.1","--port","8769","--no-proxy-headers"],"WorkingDirectory":str(ROOT),"RunAtLoad":True,"KeepAlive":True,"ThrottleInterval":10,"StandardOutPath":str(LOG/"server.log"),"StandardErrorPath":str(LOG/"error.log"),"Umask":63}
    tmp = PLIST.with_suffix(".tmp")
    fd = os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_TRUNC|os.O_NOFOLLOW,0o600)
    with os.fdopen(fd,"wb") as out:
        plistlib.dump(config,out)
    os.replace(tmp,PLIST)
    run("/bin/launchctl","enable",TARGET)
    run("/bin/launchctl","bootstrap",DOMAIN,str(PLIST))
    for _ in range(30):
        try:
            with urllib.request.urlopen("http://127.0.0.1:8769/api/health",timeout=1) as r:
                health=json.load(r)
            with urllib.request.urlopen("http://127.0.0.1:8769/admin",timeout=1) as r:
                if health.get("version")==app.version and r.status==200:
                    print("KURDWAY READY:", health)
                    run("/usr/bin/open","http://127.0.0.1:8769/admin")
                    return
        except (OSError,ValueError):
            pass
        time.sleep(1)
    raise SystemExit("Startup not verified. Inspect "+str(LOG/"error.log"))

if __name__=="__main__":
    main()
