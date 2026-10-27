# Interactive terminal menu

The menu is an optional frontend to the same controller used by direct commands.
It does not implement separate build, locking, or cleanup behavior.

## Install and start

From the repository root, install the pinned host-only dependencies:

```sh
python3 -m pip install -r requirements-menu.txt
python3 nrpe.py
```

If your Python installation is managed by the operating system, use a virtual
environment instead of overriding its package protections:

```sh
python3 -m venv .venv
```

Activate with `. .venv/bin/activate` on Linux/macOS, or
`.venv\Scripts\Activate.ps1` in PowerShell. Then run the installation command
above. The active interpreter must be available as `python3`. If a Windows
virtual environment does not provide that alias, use its explicit interpreter
`.venv\Scripts\python.exe` for both pip and `nrpe.py`, or configure a local
`python3` alias for it. No particular editor is required.

The menu uses prompt_toolkit for terminal input and rendering. This dependency
is not installed in build containers. Direct commands such as
`python3 nrpe.py verify debian12` continue to use only the Python standard library.

## Controls

| Key | Action |
| --- | --- |
| Up / Down | Move selection; long lists scroll |
| Home / End | Jump to the first / last item |
| Enter | Select an action or accept selected targets |
| Space | Toggle a target in the multi-selection screen |
| A | Select all targets in the multi-selection screen |
| Escape / Q | Go back; on the home screen, exit |
| Ctrl+C | Exit the menu; during a workflow, interrupt its command and clean up its container |
| Ctrl+D | End the menu at a selection prompt |

After a workflow or inspection command finishes, its ordinary output remains
visible in the terminal. Scroll through it, then press Enter to return. Logs are
also available from the run-selection screen or `logs --run <id>`.

## Workflow

1. Choose build and test, build only, or test existing packages.
2. Select one or more targets with Space, then Enter. No target is preselected.
3. Choose whether to check for updated base images. For SLES, optionally browse
   extracted official installation media. The browser shows directories, includes
   a parent entry, and lists available drives on Windows.
   Optionally choose a company CA certificate from its file browser; only public
   PEM/DER certificates are accepted.
4. Review the action, targets, base-image refresh, media/certificate paths, and any replacement
   of existing package outputs. Cancel is selected by default.
5. Select Run. Existing outputs are rebuilt only after this explicit confirmation.
6. Read the result and return to the menu.

SLES media selection is validated before use. Selecting the default source resets
to online repositories plus `SLES_MEDIA_DIR`, if that environment variable is set.
The certificate default similarly follows `NRPE_CA_CERT`, if configured.
The menu does not clear inherited environment configuration or download an ISO.
See [company CA trust](network.md#optional-company-ca-certificate) for scope and image-cache details.

Diagnostics, status, and logs are available directly from the home screen.
A failed command returns to the menu after its result is acknowledged. Closing
the menu does not turn a failed workflow into a passed run: inspect its exit
message, report, or status. For automation, use direct commands and their exit
codes rather than the menu session's exit code.

## Terminal behavior

Use an interactive terminal on Windows, Linux, or macOS. `NO_COLOR` requests
monochrome rendering; selection remains visible through an arrow and reverse
video, rather than color alone. `TERM=dumb` also disables color, but a terminal
with cursor-control support is still needed for the menu. Use direct commands
for restricted terminals, screen-reader workflows where full-screen interfaces
are unsuitable, redirected output, and CI.

With no terminal attached, launching without arguments prints CLI help without
importing the optional dependencies or prompting. If a terminal is attached but
the dependencies are missing, the CLI prints the installation command.
