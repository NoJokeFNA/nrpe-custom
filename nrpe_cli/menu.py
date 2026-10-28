"""Optional terminal interface; workflow execution stays in the CLI/controller."""

import os
from pathlib import Path
import string

from .state import reports
from .targets import TARGETS, package_files


def choose(title, options, *, multiple=False, selected=()):
    """Select values using arrows/Enter, returning None on Back/Escape."""
    try:
        from prompt_toolkit.application import Application
        from prompt_toolkit.formatted_text import to_formatted_text
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.layout import HSplit, Layout, Window
        from prompt_toolkit.layout.controls import FormattedTextControl
        from prompt_toolkit.layout.dimension import Dimension
        from prompt_toolkit.output import ColorDepth
        from prompt_toolkit.styles import Style
    except ImportError as exc:
        raise RuntimeError(
            "The arrow-key menu requires its optional dependencies. Run "
            "python3 -m pip install -r requirements-menu.txt, or use "
            "python3 nrpe.py --help for dependency-free commands."
        ) from exc

    # Titles and labels may contain filesystem names or report data. Render them
    # as plain formatted text, never as HTML or ANSI escape sequences.
    def safe(value):
        return ''.join(char if char.isprintable() else '?' for char in str(value))

    position = 0
    marked = set(selected)
    message = ''
    bindings = KeyBindings()

    def render():
        lines = []
        for index, (value, label) in enumerate(options):
            active = index == position
            if active:
                lines.append(('[SetCursorPosition]', ''))
            prefix = ('[x] ' if value in marked else '[ ] ') if multiple else ''
            lines.append(('class:selected' if active else '',
                          ('> ' if active else '  ') + prefix + safe(label) + '\n'))
        return to_formatted_text(lines)

    @bindings.add('up')
    def up(event):
        nonlocal position
        position = (position - 1) % len(options)

    @bindings.add('down')
    def down(event):
        nonlocal position
        position = (position + 1) % len(options)

    @bindings.add('home')
    def first(event):
        nonlocal position
        position = 0

    @bindings.add('end')
    def last(event):
        nonlocal position
        position = len(options) - 1

    @bindings.add(' ')
    def toggle(event):
        nonlocal message
        if multiple:
            message = ''
            value = options[position][0]
            if value in marked:
                marked.remove(value)
            else:
                marked.add(value)

    @bindings.add('a')
    @bindings.add('A')
    def select_all(event):
        nonlocal message
        if multiple:
            message = ''
            marked.update(value for value, _ in options)

    @bindings.add('enter')
    def accept(event):
        nonlocal message
        if multiple:
            values = [value for value, _ in options if value in marked]
            if not values:
                message = 'Select at least one target with Space.'
                return
            event.app.exit(result=values)
        else:
            event.app.exit(result=options[position][0])

    @bindings.add('escape')
    @bindings.add('q')
    def back(event):
        event.app.exit(result=None)

    @bindings.add('c-c')
    def interrupt(event):
        event.app.exit(exception=KeyboardInterrupt())

    @bindings.add('c-d')
    def eof(event):
        event.app.exit(exception=EOFError())

    control = FormattedTextControl(render, focusable=True, show_cursor=False)
    keys = 'Up/Down: move   Enter: select   Esc/Q: back   Ctrl+C: quit'
    if multiple:
        keys = 'Arrows: move   Space: toggle   A: all   Enter: continue   Esc: back'
    heading = '\n'.join(safe(line) for line in title.splitlines())
    layout = Layout(HSplit([
        Window(FormattedTextControl([('class:title', heading)]),
               wrap_lines=True, dont_extend_height=True, height=Dimension(min=2, max=10)),
        Window(control, wrap_lines=True, allow_scroll_beyond_bottom=False),
        Window(FormattedTextControl(lambda: [('class:error', message)]), height=1),
        Window(FormattedTextControl(keys), height=1),
    ]), focused_element=control)
    monochrome = 'NO_COLOR' in os.environ or os.environ.get('TERM') == 'dumb'
    app = Application(
        layout=layout, key_bindings=bindings, full_screen=True,
        style=Style.from_dict({'title': 'bold ansicyan', 'selected': 'reverse',
                              'error': 'bold ansired'}),
        color_depth=ColorDepth.DEPTH_1_BIT if monochrome else None,
        mouse_support=False,
    )
    return app.run()


def _prompt_path(title):
    """Read a literal path with completion; Escape cancels this input only."""
    from prompt_toolkit import prompt
    from prompt_toolkit.completion import PathCompleter
    from prompt_toolkit.key_binding import KeyBindings

    bindings = KeyBindings()

    @bindings.add('escape')
    def cancel(event):
        event.app.exit(result=None)

    return prompt(title + ' (Esc to cancel): ',
                  completer=PathCompleter(expanduser=True), key_bindings=bindings)


def _path_text(value):
    # Accept Explorer's Copy as path and shell-style quoted paths without
    # interpreting backslashes or treating user input as a shell command.
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        value = value[1:-1]
    return value


def enter_path(title, *, base=None, kind='any'):
    """Resolve an existing typed/pasted path without losing browser location."""
    while True:
        text = _prompt_path(title)
        if text is None or not text.strip():
            return None
        try:
            value = _path_text(text)
            if not value:
                return None
            selected = Path(os.path.expandvars(value)).expanduser()
            if not selected.is_absolute():
                selected = (base or Path.cwd()) / selected
            selected = selected.resolve(strict=True)
            if kind == 'file' and not selected.is_file():
                raise ValueError('Select a file, not a directory.')
            if kind == 'directory' and not selected.is_dir():
                raise ValueError('Select a directory, not a file.')
            if not selected.is_file() and not selected.is_dir():
                raise ValueError('Select a regular file or directory.')
            return selected
        except (OSError, ValueError, RuntimeError) as exc:
            if choose(f'Cannot use path: {exc}',
                      [('retry', 'Enter another path'), (None, 'Cancel')]) is None:
                return None


def _browse(start=None, *, select_file=False):
    """Navigate local directories and optional public certificate files."""
    current = Path(start or Path.home()).expanduser().resolve()
    while True:
        try:
            children = sorted((p for p in current.iterdir()
                               if p.is_dir() or (select_file and p.is_file()
                                   and p.suffix.lower() in (".cer", ".crt", ".pem"))),
                              key=lambda p: (not p.is_dir(), p.name.casefold()))
        except OSError as exc:
            choose(f'Cannot read {current}: {exc}', [(None, 'Back')])
            return None
        options = [('parent', '.. (parent directory)'),
                   ('path', 'Enter or paste a path...')]
        if not select_file:
            options.insert(0, ('use', 'Use this directory'))
        if os.name == 'nt':
            options.extend((f'drive:{drive}', f'{drive}:\\')
                           for drive in string.ascii_uppercase
                           if Path(f'{drive}:\\').is_dir())
        options.extend((str(index), child.name + ('/' if child.is_dir() else ''))
                       for index, child in enumerate(children))
        label = 'Company CA certificate' if select_file else 'Directory'
        answer = choose(f'{label}: {current}', options)
        if answer is None:
            return None
        if answer == 'use':
            return current
        if answer == 'path':
            selected = enter_path(label, base=current,
                                  kind='any' if select_file else 'directory')
            if selected is not None:
                if select_file and selected.is_file():
                    return selected
                current = selected
        elif answer == 'parent':
            current = current.parent
        elif answer.startswith('drive:'):
            current = Path(answer[-1] + ':\\')
        else:
            selected = children[int(answer)].resolve()
            if select_file and selected.is_file():
                return selected
            current = selected


def browse_directory(start=None):
    return _browse(start)


def browse_certificate(start=None):
    location = Path(start).expanduser() if start else None
    if location is not None and location.is_file():
        location = location.parent
    return _browse(location, select_file=True)


def workflow(root, action):
    targets = choose('Select targets', [(name, name) for name in TARGETS], multiple=True)
    if targets is None:
        return None
    pull = False
    certificate = os.environ.get("NRPE_CA_CERT")
    while True:
        options = [
            ('run', 'Continue to review'),
            ('pull', f'Check for updated base images: {"yes" if pull else "no"}'),
            ('certificate', f'Company CA certificate: {certificate or "none"}'),
        ]
        answer = choose('Workflow options', options)
        if answer is None:
            return None
        if answer == 'pull':
            pull = not pull
        elif answer == 'certificate':
            source = choose('Company CA certificate', [
                ('default', 'Default (NRPE_CA_CERT if configured; otherwise none)'),
                ('browse', 'Browse a public .cer/.crt/.pem certificate'),
                ('path', 'Enter or paste a certificate path')])
            if source == 'default':
                certificate = os.environ.get('NRPE_CA_CERT')
                continue
            if source is None:
                continue
            selected = (enter_path('Company CA certificate', kind='file')
                        if source == 'path' else browse_certificate(certificate))
            if selected is not None:
                from .certificates import prepared_certificate
                try:
                    with prepared_certificate(selected):
                        certificate = str(selected)
                except (OSError, RuntimeError) as exc:
                    choose(f'Invalid CA certificate: {exc}', [(None, 'Back to options')])
        else:
            break
    existing = [name for name in targets if package_files(root, name)]
    replacing = action in ('build', 'verify') and bool(existing)
    review = (f'Review workflow\nAction: {action}\nTargets: {", ".join(targets)}'
              f'\nUpdate base images: {pull}'
              + (f'\nCompany CA certificate: {certificate}' if certificate else '')
              + (f'\nRebuild existing packages: {", ".join(existing)}' if replacing else ''))
    if choose(review, [(False, 'Cancel'), (True, 'Run selected workflow')]) is not True:
        return None
    arguments = [action, *targets]
    if pull:
        arguments.append('--pull')
    if certificate:
        arguments.extend(["--ca-cert", certificate])
    if replacing:
        # The review above is the explicit rebuild confirmation. Do not prompt
        # again through input(), which would break arrow-only navigation.
        arguments.append('--rebuild')
    return arguments


def run_menu(root, dispatch):
    """Keep returning to the menu after each command, including failures."""
    actions = [('verify', 'Build and test packages'), ('build', 'Build packages'),
               ('test', 'Test existing packages'), ('doctor', 'Diagnose Docker'),
               ('status', 'Show package and test status'), ('logs', 'View run logs'),
               ('quit', 'Quit')]
    try:
        while True:
            action = choose('NRPE package controller', actions)
            if action is None or action == 'quit':
                return 0
            if action in ('verify', 'build', 'test'):
                arguments = workflow(root, action)
                if arguments is None:
                    continue
            elif action == 'logs':
                history = reports(root)
                if not history:
                    choose('No recorded runs', [(None, 'Back')])
                    continue
                run = choose('Select a run (newest first)', [
                    (item['id'], f'{item["id"]}: {item["action"]} ({item["status"]})')
                    for item in history])
                if run is None:
                    continue
                arguments = ['logs', '--run', run]
            else:
                arguments = [action]
            code = dispatch(arguments)
            # Output remains in terminal scrollback. This is a short non-fullscreen
            # pause so long logs can be read before the next screen is displayed.
            pause(code)
    except EOFError:
        return 0
    except KeyboardInterrupt:
        print('\nCancelled.')
        return 130


def pause(code):
    from prompt_toolkit import prompt
    from prompt_toolkit.key_binding import KeyBindings

    bindings = KeyBindings()

    @bindings.add('enter')
    def accept(event):
        event.app.exit(result='')

    @bindings.add('escape')
    def back(event):
        event.app.exit(result='')

    prompt(f'Command finished (exit {code}). Press Enter to return to the menu. ',
           key_bindings=bindings)
