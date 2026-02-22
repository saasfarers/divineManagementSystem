#!/usr/bin/env python3
import argparse
import os
import subprocess
import sys

def cprint(*args, level: int = 1):
    CRED = "\033[31m"
    CGRN = "\33[92m"
    CYLW = "\33[93m"
    reset = "\033[0m"
    message = " ".join(map(str, args))
    if level == 1:
        print(CRED, message, reset)
    if level == 2:
        print(CGRN, message, reset)
    if level == 3:
        print(CYLW, message, reset)

def set_git_auto_setup_remote():
    try:
        subprocess.check_call(["git", "config", "--global", "push.autoSetupRemote", "true"])
        cprint("Successfully set git global config auto setup remote", level=3)
    except subprocess.CalledProcessError as e:
        cprint(f"Failed to set git global config: {e}", level=1)

def run_subprocess(command, cwd=None, env=None, check=True):
    try:
        subprocess.run(command, cwd=cwd, env=env, check=check)
    except subprocess.CalledProcessError as e:
        cprint(f"Command failed: {' '.join(command)}", level=1)
        sys.exit(1)

def main():
    parser = get_args_parser()
    args = parser.parse_args()
    set_git_auto_setup_remote()
    init_bench_if_not_exist(args)
    create_site_in_bench(args)

def get_args_parser():
    token = os.getenv("DEVELOPER_TOKEN")
    parser = argparse.ArgumentParser()
    parser.add_argument("-j", "--apps-json", type=str, default=None)
    parser.add_argument("-b", "--bench-name", type=str, default="development-bench")
    parser.add_argument("-s", "--site-name", type=str, default="development.divine")
    parser.add_argument("-r", "--frappe-repo", type=str, default=f"https://github.com/frappe/frappe.git")
    parser.add_argument("-t", "--frappe-branch", type=str, default="develop")
    parser.add_argument("-p", "--py-version", type=str, default=None)
    parser.add_argument("-n", "--node-version", type=str, default=None)
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("-a", "--admin-password", type=str, default="admin")
    parser.add_argument("-d", "--db-type", type=str, default="mariadb")
    parser.add_argument("--db-root-username", type=str, default="root")  # Added
    parser.add_argument("--db-root-password", type=str, default="123")   # Added
    return parser

def init_bench_if_not_exist(args):
    if os.path.exists(args.bench_name):
        cprint("Bench already exists. Only site will be created", level=3)
        return
    env = os.environ.copy()
    init_command = ""
    if args.node_version:
        init_command += f"nvm use {args.node_version};"
    if args.py_version:
        init_command += f"PYENV_VERSION={args.py_version} "
    init_command += "bench init --skip-redis-config-generation "
    init_command += "--verbose " if args.verbose else ""
    init_command += f"--frappe-path={args.frappe_repo} "
    init_command += f"--frappe-branch={args.frappe_branch} "
    if args.apps_json:
        init_command += f"--apps_path={args.apps_json} "
    init_command += args.bench_name

    run_subprocess(["/bin/bash", "-i", "-c", init_command], env=env, cwd=os.getcwd())

    # Basic bench config
    config_pairs = [
        ("db_type", args.db_type),
        ("redis_cache", "redis://redis-cache:6379"),
        ("redis_queue", "redis://redis-queue:6379"),
        ("redis_socketio", "redis://redis-socketio:6379"),
        ("developer_mode", "1"),
    ]
    for key, value in config_pairs:
        run_subprocess(["bench", "set-config", "-g", key, value], cwd=os.path.join(os.getcwd(), args.bench_name))

def create_site_in_bench(args):
    token = os.getenv("DEVELOPER_TOKEN")
    apps_to_get = [
        ("payments", f"https://github.com/frappe/payments.git", "develop"),
        ("erpnext", f"https://github.com/frappe/erpnext.git", "develop"),
        ("hrms", f"https://github.com/frappe/hrms.git", "develop"),
        ("telephony", f"https://github.com/frappe/telephony.git", "develop"),
        ("crm", f"https://github.com/frappe/crm.git", "develop"),
        ("helpdesk", f"https://github.com/frappe/helpdesk.git", "develop"),
        ("lms", f"https://github.com/frappe/lms.git", "develop"),
    ]

    # Fetch apps
    for app_name, app_repo, app_branch in apps_to_get:
        cprint(f"Fetching app {app_name} ...", level=2)
        run_subprocess(
            ["bench", "get-app", "--branch", app_branch, app_repo],
            cwd=os.path.join(os.getcwd(), args.bench_name),
        )

    # Create site properly
    db_host = "mariadb" if args.db_type == "mariadb" else "postgresql"
    new_site_cmd = [
        "bench", "new-site",
        f"--db-type={args.db_type}",
        f"--db-host={db_host}",
        f"--db-root-username={args.db_root_username}",
        f"--db-root-password={args.db_root_password}",
        f"--admin-password={args.admin_password}",
        "--mariadb-user-host-login-scope=%",
        "--set-default",
        args.site_name,
    ]

    cprint(f"Creating Site {args.site_name} ...", level=2)
    run_subprocess(
        new_site_cmd,
        cwd=os.path.join(os.getcwd(), args.bench_name),
    )

    # Install apps
    for app_name, _, _ in apps_to_get:
        cprint(f"Installing app {app_name} ...", level=2)
        run_subprocess(
            ["bench", "--site", args.site_name, "install-app", app_name],
            cwd=os.path.join(os.getcwd(), args.bench_name),
        )

    cprint("Set site developer_mode", level=3)
    run_subprocess(
        ["bench", "--site", args.site_name, "set-config", "developer_mode", "1"],
        cwd=os.path.join(os.getcwd(), args.bench_name),
    )

if __name__ == "__main__":
    main()
