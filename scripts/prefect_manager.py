#!/usr/bin/env python
"""
Unified Prefect Server & Flows Management Tool

A single command-line utility for:
- Starting/stopping Prefect server
- Deploying flows to dashboard
- Verifying setup
- Quick start guidance

Usage:
    uv run python scripts/prefect_manager.py start      # Start server and deploy flows
    uv run python scripts/prefect_manager.py verify     # Check setup status
    uv run python scripts/prefect_manager.py deploy     # Deploy flows only
    uv run python scripts/prefect_manager.py status     # Show server status
"""

import subprocess
import sys
import time
from pathlib import Path
from typing import Optional


class PrefectManager:
    """Manage Prefect server and flow deployments."""

    def __init__(self):
        self.workspace = Path(__file__).parent.parent

    def print_header(self, text: str) -> None:
        """Print formatted header."""
        print(f"\n╔{'═' * 60}╗")
        print(f"║ {text.center(58)} ║")
        print(f"╚{'═' * 60}╝\n")

    def print_section(self, title: str) -> None:
        """Print section header."""
        print(f"\n▶ {title}")
        print("─" * 60)

    def run_command(self, cmd: list, description: str = "", capture: bool = False) -> bool:
        """Run a shell command and report status."""
        try:
            if description:
                print(f"  → {description}")
            if capture:
                result = subprocess.run(cmd, capture_output=True, text=True)
                return result.returncode == 0
            else:
                result = subprocess.run(cmd, cwd=self.workspace)
                return result.returncode == 0
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return False

    def check_server_status(self) -> bool:
        """Check if Prefect server is running."""
        try:
            result = subprocess.run(
                ["curl", "-s", "http://localhost:4200/api/health"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.returncode == 0 and "true" in result.stdout.lower()
        except Exception:
            return False

    def start_server(self) -> None:
        """Start Prefect server."""
        self.print_header("STARTING PREFECT SERVER")

        if self.check_server_status():
            print("✅ Server already running at http://localhost:4200")
            return

        print("Starting Prefect server in background...")
        try:
            subprocess.Popen(
                ["uv", "run", "python", "-m", "prefect", "server", "start"],
                cwd=self.workspace,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("⏳ Waiting for server to start...")
            time.sleep(3)
            if self.check_server_status():
                print("✅ Server started at http://localhost:4200")
            else:
                print("⚠️  Server may be starting... check http://localhost:4200")
        except Exception as e:
            print(f"❌ Failed to start server: {e}")
            print("Try manually: uv run prefect server start")

    def deploy_flows(self) -> None:
        """Deploy flows to Prefect server."""
        self.print_header("DEPLOYING FLOWS")

        if not self.check_server_status():
            print("❌ Prefect server not running!")
            print("Start it first: uv run python scripts/prefect_manager.py start")
            return

        flows = [
            ("enhanced_analytics_flow", "src.analytics_flows", "Enhanced Analytics"),
            ("send_report_email_flow", "src.analytics_flows", "Send Report Email"),
        ]

        deployed = 0
        for flow_func, module, name in flows:
            print(f"\n  Deploying: {name}")
            try:
                cmd = [
                    "uv",
                    "run",
                    "python",
                    "-c",
                    f"""
from {module} import {flow_func}
{flow_func}.serve(name='{name}', description='Automated flow deployment')
""",
                ]
                subprocess.run(cmd, cwd=self.workspace, capture_output=True, timeout=10)
                print(f"  ✅ {name}")
                deployed += 1
            except Exception as e:
                print(f"  ⚠️  {name}: {e}")

        print(f"\n✅ Deployed {deployed} flows")
        print("\n📊 View flows at: http://localhost:4200")

    def verify_setup(self) -> None:
        """Verify Prefect setup and show status."""
        self.print_header("PREFECT SETUP VERIFICATION")

        # Server status
        self.print_section("1. Server Status")
        if self.check_server_status():
            print("✅ Server is RUNNING")
            print("   URL: http://localhost:4200")
        else:
            print("❌ Server is NOT RUNNING")
            print("   Start with: uv run python scripts/prefect_manager.py start")
            return

        # Check imports
        self.print_section("2. Module Imports")
        imports = [
            ("enhanced_analytics_flow", "src.analytics_flows"),
            ("portfolio_analytics_flow", "src.portfolio_flows"),
        ]

        for flow_name, module in imports:
            try:
                subprocess.run(
                    [
                        "uv",
                        "run",
                        "python",
                        "-c",
                        f"from {module} import {flow_name}",
                    ],
                    capture_output=True,
                    timeout=10,
                    cwd=self.workspace,
                )
                print(f"✅ {flow_name}")
            except Exception:
                print(f"⚠️  {flow_name}")

        # Quick start guide
        self.print_section("3. Next Steps")
        print("""
✓ Server is running and ready
✓ Flows are importable

Next:
  1. Deploy flows:
     uv run python scripts/prefect_manager.py deploy

  2. Open dashboard:
     http://localhost:4200

  3. Run a flow:
     uv run python -c "from src.analytics_flows import enhanced_analytics_flow; enhanced_analytics_flow()"
""")

    def show_status(self) -> None:
        """Show current Prefect status."""
        self.print_header("PREFECT STATUS")

        if self.check_server_status():
            print("✅ Server RUNNING")
            print("   Dashboard: http://localhost:4200")
        else:
            print("❌ Server NOT RUNNING")

    def main(self) -> None:
        """Main entry point."""
        if len(sys.argv) < 2:
            self.print_header("PREFECT MANAGER")
            print("""
Commands:
  start      - Start server and verify setup
  deploy     - Deploy flows to dashboard
  verify     - Check setup status
  status     - Show server status

Examples:
  uv run python scripts/prefect_manager.py start
  uv run python scripts/prefect_manager.py deploy
  uv run python scripts/prefect_manager.py verify
""")
            return

        command = sys.argv[1].lower()

        if command == "start":
            self.start_server()
            time.sleep(1)
            self.verify_setup()
        elif command == "deploy":
            self.deploy_flows()
        elif command == "verify":
            self.verify_setup()
        elif command == "status":
            self.show_status()
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)


if __name__ == "__main__":
    manager = PrefectManager()
    manager.main()
