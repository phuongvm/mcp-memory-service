#!/usr/bin/env python3
"""
Cursor IDE Memory Awareness Hooks Installer
===========================================

Cross-platform installer for Cursor IDE memory awareness hooks.
Installs hooks in workspace .cursor/hooks/ directory (project-scoped).

Based on Claude Code hooks with adaptations for Cursor IDE v1.7+.

Usage:
    python install_cursor_hooks.py --workspace /path/to/project
    python install_cursor_hooks.py --workspace . (for current directory)
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    BLUE = '\033[0;34m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color


class CursorHookInstaller:
    """Cursor IDE hook installer for workspace-scoped memory awareness."""

    def __init__(self, workspace_path: Path):
        self.script_dir = Path(__file__).parent.absolute()
        self.platform_name = platform.system().lower()
        self.workspace = workspace_path.absolute()
        self.hooks_dir = self.workspace / '.cursor' / 'hooks'
        self.backup_dir = None

    def info(self, message: str) -> None:
        """Print info message."""
        print(f"{Colors.GREEN}[INFO]{Colors.NC} {message}")

    def warn(self, message: str) -> None:
        """Print warning message."""
        print(f"{Colors.YELLOW}[WARN]{Colors.NC} {message}")

    def error(self, message: str) -> None:
        """Print error message."""
        print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")

    def success(self, message: str) -> None:
        """Print success message."""
        print(f"{Colors.BLUE}[SUCCESS]{Colors.NC} {message}")

    def header(self, message: str) -> None:
        """Print header message."""
        print(f"\n{Colors.CYAN}{'=' * 60}{Colors.NC}")
        print(f"{Colors.CYAN} {message}{Colors.NC}")
        print(f"{Colors.CYAN}{'=' * 60}{Colors.NC}\n")

    def check_prerequisites(self) -> bool:
        """Check system prerequisites for hook installation."""
        self.info("Checking prerequisites...")
        all_good = True

        # Check Node.js (required for hooks)
        try:
            result = subprocess.run(['node', '--version'],
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.strip()
                major_version = int(version.replace('v', '').split('.')[0])
                if major_version >= 18:
                    self.success(f"Node.js found: {version} (compatible)")
                else:
                    self.error(f"Node.js {version} found, but version 18+ required")
                    all_good = False
            else:
                self.error("Node.js version check failed")
                all_good = False
        except (subprocess.SubprocessError, FileNotFoundError, subprocess.TimeoutExpired):
            self.error("Node.js not found - required for hook execution")
            self.info("Please install Node.js 18+ from https://nodejs.org/")
            all_good = False

        # Check Python version
        if sys.version_info < (3, 7):
            self.error(f"Python {sys.version} found, but Python 3.7+ required")
            all_good = False
        else:
            self.success(f"Python {sys.version_info.major}.{sys.version_info.minor} found (compatible)")

        # Check workspace exists
        if not self.workspace.exists():
            self.error(f"Workspace directory does not exist: {self.workspace}")
            all_good = False
        else:
            self.success(f"Workspace found: {self.workspace}")

        return all_good

    def create_backup(self) -> None:
        """Create backup of existing hooks installation if present."""
        if not self.hooks_dir.exists():
            self.info("No existing hooks installation found - no backup needed")
            return

        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
        self.backup_dir = self.workspace / '.cursor' / f'hooks-backup-{timestamp}'

        try:
            shutil.copytree(self.hooks_dir, self.backup_dir)
            self.success(f"Backup created: {self.backup_dir}")
        except Exception as e:
            self.warn(f"Failed to create backup: {e}")
            self.warn("Continuing without backup...")

    def install_core_hooks(self) -> bool:
        """Install core hook files."""
        self.info("Installing core hooks...")

        try:
            # Create directory structure
            (self.hooks_dir / 'core').mkdir(parents=True, exist_ok=True)
            (self.hooks_dir / 'utilities').mkdir(parents=True, exist_ok=True)
            (self.hooks_dir / 'tests').mkdir(parents=True, exist_ok=True)

            # Copy core hooks
            core_files = ['agent-start.js', 'agent-complete.js']
            for file in core_files:
                src = self.script_dir / 'core' / file
                dst = self.hooks_dir / 'core' / file
                if src.exists():
                    shutil.copy2(src, dst)
                    self.success(f"  Installed: core/{file}")
                else:
                    self.error(f"  Missing: core/{file}")
                    return False

            # Copy utilities
            utility_files = [
                'cursor-adapter.js',
                'project-detector.js',
                'memory-scorer.js',
                'context-formatter.js',
                'git-analyzer.js',
                'mcp-client.js',
                'memory-client.js'
            ]
            for file in utility_files:
                src = self.script_dir / 'utilities' / file
                dst = self.hooks_dir / 'utilities' / file
                if src.exists():
                    shutil.copy2(src, dst)
                else:
                    self.warn(f"  Utility not found: {file}")

            # Copy tests
            test_files = ['test-basic-functionality.js']
            for file in test_files:
                src = self.script_dir / 'tests' / file
                dst = self.hooks_dir / 'tests' / file
                if src.exists():
                    shutil.copy2(src, dst)

            self.success("Core hooks installed successfully")
            return True

        except Exception as e:
            self.error(f"Failed to install core hooks: {e}")
            return False

    def install_configuration(self, api_key: Optional[str] = None) -> bool:
        """Install configuration files."""
        self.info("Installing configuration...")

        try:
            # Load template configuration
            template_src = self.script_dir / 'templates' / 'config.json.template'
            if not template_src.exists():
                self.error("Configuration template not found")
                return False

            with open(template_src, 'r') as f:
                config = json.load(f)

            # Update with provided API key if available
            if api_key:
                config['memoryService']['http']['apiKey'] = api_key

            # Update default tags with workspace name
            workspace_name = self.workspace.name
            if workspace_name:
                config['memoryService']['defaultTags'] = ['cursor', workspace_name.lower().replace(' ', '-')]

            # Write configuration
            config_dst = self.hooks_dir / 'config.json'
            with open(config_dst, 'w') as f:
                json.dump(config, f, indent=2)

            self.success("Configuration installed")

            # Install hooks.json (hook registration)
            hooks_json_src = self.script_dir / 'templates' / 'hooks.json.template'
            hooks_json_dst = self.workspace / '.cursor' / 'hooks.json'

            if hooks_json_src.exists():
                shutil.copy2(hooks_json_src, hooks_json_dst)
                self.success("Hook registration installed (.cursor/hooks.json)")
            else:
                self.warn("hooks.json template not found")

            return True

        except Exception as e:
            self.error(f"Failed to install configuration: {e}")
            return False

    def run_tests(self) -> bool:
        """Run basic functionality tests."""
        self.info("Running installation tests...")

        test_script = self.hooks_dir / 'tests' / 'test-basic-functionality.js'
        if not test_script.exists():
            self.warn("Test script not found - skipping tests")
            return True

        try:
            result = subprocess.run(
                ['node', str(test_script)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.hooks_dir)
            )

            if result.returncode == 0:
                self.success("All tests passed ✅")
                return True
            else:
                self.warn("Some tests failed")
                if result.stdout:
                    print(result.stdout)
                return False

        except Exception as e:
            self.warn(f"Could not run tests: {e}")
            return True  # Don't fail installation if tests can't run

    def show_next_steps(self) -> None:
        """Display next steps for the user."""
        self.header("Installation Complete!")

        print(f"✅ Cursor memory hooks installed to: {self.hooks_dir}\n")

        print("📋 Next Steps:\n")
        print("1. Configure your memory service API key:")
        print(f"   Edit: {self.hooks_dir / 'config.json'}")
        print(f"   Set: memoryService.http.apiKey\n")

        print("2. Open your project in Cursor IDE:")
        print(f"   cursor {self.workspace}\n")

        print("3. Invoke Cursor Agent (Cmd/Ctrl+K or Composer)")
        print("   You should see relevant memories injected!\n")

        print("4. Verify installation:")
        print(f"   Check: {self.workspace / '.cursor' / 'hooks.json'}")
        print(f"   Check: {self.hooks_dir / 'config.json'}\n")

        print("📖 Documentation:")
        print(f"   {self.script_dir / 'README.md'}\n")

        print("🐛 Troubleshooting:")
        print("   - Ensure Node.js 18+ is installed")
        print("   - Ensure MCP Memory Service is running")
        print("   - Check memory service endpoint in config.json")
        print("   - Test manually: node .cursor/hooks/core/agent-start.js\n")


def main():
    """Main installer function."""
    parser = argparse.ArgumentParser(
        description="Install Cursor IDE Memory Awareness Hooks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python install_cursor_hooks.py --workspace /path/to/project
  python install_cursor_hooks.py --workspace . --api-key YOUR_KEY
  python install_cursor_hooks.py -w ~/projects/my-app
  python install_cursor_hooks.py --workspace . --force

The installer creates project-scoped hooks in .cursor/hooks/
        """
    )

    parser.add_argument('-w', '--workspace',
                        required=True,
                        help='Path to workspace/project directory')
    parser.add_argument('--api-key',
                        help='Memory service API key (optional, can configure later)')
    parser.add_argument('--force',
                        action='store_true',
                        help='Force installation even if prerequisites fail')
    parser.add_argument('--no-tests',
                        action='store_true',
                        help='Skip running tests after installation')

    args = parser.parse_args()

    # Resolve workspace path
    workspace_path = Path(args.workspace).expanduser().absolute()

    # Create installer instance
    installer = CursorHookInstaller(workspace_path)

    installer.header("Cursor IDE Memory Awareness Hooks Installer v1.0")
    installer.info(f"Workspace: {workspace_path}")
    installer.info(f"Platform: {installer.platform_name}")

    # Check prerequisites
    if not installer.check_prerequisites() and not args.force:
        installer.error("Prerequisites check failed. Use --force to continue anyway.")
        sys.exit(1)

    # Create backup if existing installation
    installer.create_backup()

    # Install core hooks
    if not installer.install_core_hooks():
        installer.error("Failed to install core hooks")
        sys.exit(1)

    # Install configuration
    if not installer.install_configuration(api_key=args.api_key):
        installer.error("Failed to install configuration")
        sys.exit(1)

    # Run tests unless skipped
    if not args.no_tests:
        installer.run_tests()

    # Show next steps
    installer.show_next_steps()

    installer.success("🎉 Installation complete!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Installation cancelled by user{Colors.NC}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {e}{Colors.NC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

