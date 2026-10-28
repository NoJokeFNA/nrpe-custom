# Interactive terminal menu

The menu is an optional frontend to the same controller used by direct commands.
It does not implement separate build, locking, or cleanup behavior.

Local retention cleanup is available through `python3 nrpe.py clean`; see the
[cleanup reference](local-cleanup.md). Its preview is read-only, and deletion
requires a separate CLI invocation with `--apply`.

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
3. Choose whether to check for updated base images. Optionally browse for a
   public PEM/DER company CA certificate, or enter/paste its path directly.
4. Review the action, targets, base-image refresh, certificate path and output
   replacement. Cancel is selected by default. SLE-15 media selection was retired.
5. Select Run. Existing outputs are rebuilt only after this explicit confirmation.
6. Read the result and return to the menu.

The certificate default follows `NRPE_CA_CERT`, if configured.
See [company CA trust](network.md#optional-company-ca-certificate) for scope and image-cache details.

Diagnostics, status, and logs are available directly from the home screen.
A failed command returns to the menu after its result is acknowledged. Closing
the menu does not turn a failed workflow into a passed run: inspect its exit
message, report, or status. For automation, use direct commands and their exit
codes rather than the menu session's exit code.

## Enter or paste a path

The certificate browser includes **Enter or paste a path...**. A file selects
that certificate; a directory opens that location. A direct certificate-path
option is also available from the source menu.

Paste paths as plain text, for example `C:\Certificates\Company Root.cer`, or
with matching quotes as copied by Explorer's **Copy as path**. Backslashes and
spaces are preserved; paths are never evaluated as shell commands. `~` and
native environment-variable syntax are expanded (for example `%USERPROFILE%`
on Windows). Relative paths entered in a browser are relative to its current
directory; direct source-menu entry is relative to the process working directory.
Tab offers path completion. Enter accepts; Escape or an empty value cancels.
Cancelling returns to the existing browser location. Missing paths and incorrect
file/directory types show an error with options to retry or cancel. Certificate
contents still undergo regular validation.

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
