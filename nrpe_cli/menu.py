"""Optional terminal interface; workflow execution stays in the CLI/controller."""

import os
from pathlib import Path

from .state import reports
from .targets import TARGETS, package_files


def safe(value):
    """Render local paths and logs as plain text, never terminal instructions."""
    return ''.join(char if char.isprintable() else '?' for char in str(value))


def compact(value, width=74):
    text = safe(value)
    if len(text) <= width:
        return text
    left = max(1, (width - 3) // 3)
    return text[:left] + '...' + text[-(width - left - 3):]


def choose(title, options, *, multiple=False, selected=(), state=None, description=''):
    """Keyboard selection with filtering, contextual help and retained focus."""
    try:
        from prompt_toolkit.application import Application
        from prompt_toolkit.filters import Condition
        from prompt_toolkit.formatted_text import to_formatted_text
        from prompt_toolkit.key_binding import KeyBindings
        from prompt_toolkit.layout import HSplit, Layout, Window
        from prompt_toolkit.layout.controls import FormattedTextControl
        from prompt_toolkit.layout.dimension import Dimension
        from prompt_toolkit.output import ColorDepth
        from prompt_toolkit.styles import Style
    except ImportError as exc:
        raise RuntimeError(
            'The arrow-key menu requires its optional dependencies. Run '
            'python3 -m pip install -r requirements-menu.txt, or use '
            'python3 nrpe.py --help for dependency-free commands.'
        ) from exc
    state = state if state is not None else {}
    options = [(option[0], option[1], option[2] if len(option) > 2 else '') for option in options]
    query = state.get('query', '')
    position = 0
    marked = set(selected)
    message = ''
    filtering = False
    help_open = False
    bindings = KeyBindings()

    def visible():
        return [item for item in options if query.casefold() in (safe(item[1]) + ' ' + safe(item[2])).casefold()]

    def remember():
        items = visible()
        state['focus'] = items[position][0] if items else None
        state['query'] = query

    items = visible()
    position = next((index for index, item in enumerate(items)
                     if 'focus' in state and item[0] == state['focus']), 0)

    def render():
        items = visible()
        if not items:
            return [('class:muted', '  No matches. Backspace edits the filter; Esc clears it.')]
        lines = []
        for index, (value, label, _) in enumerate(items):
            active = index == position
            if active:
                lines.append(('[SetCursorPosition]', ''))
            prefix = ('[x] ' if value in marked else '[ ] ') if multiple else ''
            lines.append(('class:selected' if active else '',
                          (' > ' if active else '   ') + prefix + safe(label) + '\n'))
        return to_formatted_text(lines)

    @bindings.add('up')
    @bindings.add('down')
    @bindings.add('home')
    @bindings.add('end')
    def move(event):
        nonlocal position
        count = len(visible())
        if count:
            key = event.key_sequence[-1].key
            position = (0 if key == 'home' else count - 1 if key == 'end'
                        else (position + (-1 if key == 'up' else 1)) % count)
            remember()

    @bindings.add(' ', filter=Condition(lambda: not filtering))
    def toggle(event):
        nonlocal message
        items = visible()
        if multiple and items:
            message = ''
            value = items[position][0]
            marked.symmetric_difference_update({value})

    @bindings.add('a', filter=Condition(lambda: not filtering))
    @bindings.add('A', filter=Condition(lambda: not filtering))
    def select_all(event):
        nonlocal message
        if multiple:
            message = ''
            marked.update(value for value, _, _ in visible())

    @bindings.add('/', filter=Condition(lambda: not filtering))
    def begin_filter(event):
        nonlocal filtering
        filtering = True

    @bindings.add('<any>', filter=Condition(lambda: filtering))
    def type_filter(event):
        nonlocal query, position
        query += ''.join(char for char in event.data if char.isprintable())
        position = 0
        remember()

    @bindings.add('tab', filter=Condition(lambda: filtering))
    def finish_filter(event):
        nonlocal filtering
        filtering = False

    @bindings.add('backspace')
    def erase_filter(event):
        nonlocal query, position
        query = query[:-1]
        position = 0
        remember()

    @bindings.add('?', filter=Condition(lambda: not filtering))
    def show_help(event):
        nonlocal help_open
        help_open = not help_open

    @bindings.add('enter')
    def accept(event):
        nonlocal message
        remember()
        if multiple:
            values = [value for value, _, _ in options if value in marked]
            if not values:
                message = 'Select at least one target with Space.'
                return
            event.app.exit(result=values)
        elif visible():
            event.app.exit(result=visible()[position][0])

    @bindings.add('escape')
    def escape(event):
        nonlocal query, filtering, position, help_open
        if help_open:
            help_open = False
        elif filtering or query:
            query, filtering, position = '', False, 0
            remember()
        else:
            remember()
            event.app.exit(result=None)

    @bindings.add('q', filter=Condition(lambda: not filtering))
    def back(event):
        remember()
        event.app.exit(result=None)

    @bindings.add('c-c')
    def interrupt(event):
        event.app.exit(exception=KeyboardInterrupt())

    @bindings.add('c-d')
    def eof(event):
        event.app.exit(exception=EOFError())

    def detail():
        items = visible()
        text = description
        if items:
            text = items[position][2] or description
        if help_open:
            text = ('Type / to filter, Backspace to edit, Tab to keep the filter; Esc clears it before going back. '
                    'Home/End jump. ' + ('Space toggles; A selects visible items. ' if multiple else '')
                    + 'Ctrl+C exits; no action starts before Enter.')
        return [('class:muted', safe(text))]

    control = FormattedTextControl(render, focusable=True, show_cursor=False)
    body = Window(control, wrap_lines=False, allow_scroll_beyond_bottom=False,
                  get_vertical_scroll=lambda window: state.get('scroll', 0))
    keys = 'Arrows: move  Enter: select  /: filter  ?: help  Esc: back'
    if multiple:
        keys = 'Arrows: move  Space: toggle  A: visible  Enter: next  Esc: back'
    layout = Layout(HSplit([
        Window(FormattedTextControl([('class:brand', ' NRPE CUSTOM  /  PACKAGE WORKSTATION')]), height=1),
        Window(FormattedTextControl([('class:title', '\n'.join(safe(line) for line in title.splitlines()))]),
               wrap_lines=True, dont_extend_height=True, height=Dimension(min=1, max=6)),
        Window(FormattedTextControl(lambda: [('class:muted',
            f' Filter: {safe(query)}' + ('_' if filtering else '') +
            (f'   Selected: {len(marked)}' if multiple else ''))]), height=1),
        body,
        Window(FormattedTextControl(detail), wrap_lines=True, height=Dimension(min=1, max=3)),
        Window(FormattedTextControl(lambda: [('class:error', message)]), height=1),
        Window(FormattedTextControl(keys), wrap_lines=True, height=Dimension(min=1, max=2)),
    ]), focused_element=control)
    monochrome = 'NO_COLOR' in os.environ or os.environ.get('TERM') == 'dumb'
    app = Application(
        layout=layout, key_bindings=bindings, full_screen=True,
        style=Style.from_dict({'brand': 'bold ansigreen', 'title': 'bold',
                              'selected': 'reverse', 'muted': 'ansibrightblack', 'error': 'bold ansired'}),
        color_depth=ColorDepth.DEPTH_1_BIT if monochrome else None,
        mouse_support=False,
    )
    app.after_render += lambda application: state.update(scroll=body.vertical_scroll)
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


def is_windows():
    return os.name == 'nt'


def windows_drives():
    """Enumerate root letters once on demand, without probing each filesystem."""
    if not is_windows():
        return []
    import ctypes
    mask = ctypes.windll.kernel32.GetLogicalDrives()
    return [f'{chr(65 + index)}:\\' for index in range(26) if mask & (1 << index)]


def drive_selector(current, state=None):
    drives = windows_drives()
    options = [(drive, drive + (' (current)' if Path(drive) == Path(current.anchor) else ''))
               for drive in drives]
    return choose('Switch drive', options + [(None, 'Back to directory')], state=state,
                  description='Use / to filter drive letters. A drive is opened only after selection.')


def view_text(title, text):
    """Scrollable, searchable plain text, including complete long paths."""
    from prompt_toolkit.application import Application
    from prompt_toolkit.key_binding import KeyBindings
    from prompt_toolkit.layout import HSplit, Layout, Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from prompt_toolkit.widgets import TextArea, SearchToolbar
    from prompt_toolkit.output import ColorDepth
    from prompt_toolkit.search import start_search, stop_search

    search = SearchToolbar()
    area = TextArea(text='\n'.join(safe(line) for line in text.splitlines()), read_only=True,
                    scrollbar=True, wrap_lines=True, search_field=search)
    bindings = KeyBindings()

    @bindings.add('escape', eager=True)
    @bindings.add('c-c')
    def close(event):
        if event.app.layout.has_focus(search):
            stop_search()
        else:
            event.app.exit()

    @bindings.add('c-f')
    def find(event):
        start_search(area.control)

    Application(layout=Layout(HSplit([
        Window(FormattedTextControl(safe(title)), height=1), area, search,
        Window(FormattedTextControl('Arrows/PageUp/PageDown: scroll  Ctrl+F: search  Esc: back'), height=1),
    ]), focused_element=area), key_bindings=bindings, full_screen=True,
        color_depth=ColorDepth.DEPTH_1_BIT if 'NO_COLOR' in os.environ or os.environ.get('TERM') == 'dumb' else None).run()


def _browse(start=None, *, select_file=False, extensions=None):
    """Keep drives out of ordinary directory listings and retain each location."""
    current = Path(start or Path.home()).expanduser().resolve()
    extensions = ('.cer', '.crt', '.pem') if extensions is None else extensions
    states, drive_state = {}, {}
    while True:
        try:
            children = sorted((p for p in current.iterdir()
                               if p.is_dir() or (select_file and p.is_file()
                                   and (not extensions or p.suffix.lower() in extensions))),
                              key=lambda p: (not p.is_dir(), p.name.casefold()))
        except OSError as exc:
            choose(f'Cannot read {compact(current)}: {exc}', [(None, 'Back')])
            return None
        options = [('parent', '.. (parent directory)'),
                   ('path', 'Enter or paste a path...'), ('full-path', 'Show complete current path')]
        if not select_file:
            options.insert(0, ('use', 'Use this directory'))
        if is_windows():
            options.append(('drives', 'Switch drive...'))
        options.extend((str(index), child.name + ('/' if child.is_dir() else ''))
                       for index, child in enumerate(children))
        label = 'Select a file' if select_file and not extensions else 'Company CA certificate' if select_file else 'Directory'
        answer = choose(f'{label}\n{compact(current)}', options,
                        state=states.setdefault(str(current), {}),
                        description='Only this directory is listed. / filters entries; paste a path for direct access.')
        if answer is None:
            return None
        if answer == 'use':
            return current
        if answer == 'full-path':
            view_text('Complete directory path', str(current))
            continue
        candidate = None
        if answer == 'path':
            candidate = enter_path(label, base=current,
                                   kind='any' if select_file else 'directory')
        elif answer == 'drives':
            drive = drive_selector(current, drive_state)
            if drive is not None:
                candidate = Path(drive)
        elif answer == 'parent':
            candidate = current.parent
        else:
            candidate = children[int(answer)]
        if candidate is None:
            continue
        try:
            candidate = candidate.resolve(strict=True)
            if select_file and candidate.is_file():
                return candidate
            if not candidate.is_dir():
                raise OSError('The selected directory is unavailable.')
            # Open only the selected location. Failed/disconnected drives retain
            # the old location and its focus rather than abandoning the browser.
            next(candidate.iterdir(), None)
        except (OSError, RuntimeError) as exc:
            choose(f'Cannot open {compact(candidate)}: {exc}', [(None, 'Back to directory')])
            continue
        current = candidate


def browse_directory(start=None):
    return _browse(start)


def browse_file(start=None):
    return _browse(start, select_file=True, extensions=())


def browse_certificate(start=None):
    location = Path(start).expanduser() if start else None
    if location is not None and location.is_file():
        location = location.parent
    return _browse(location, select_file=True)


TARGET_LABELS = {
    'debian11': 'Debian 11 / Bullseye', 'debian12': 'Debian 12 / Bookworm',
    'debian13': 'Debian 13 / Trixie', 'debian14': 'Debian 14 / Forky (testing)',
    'sles12sp3': 'SLES 12 SP3',
}


def new_session():
    certificate = os.environ.get('NRPE_CA_CERT')
    return {'targets': [], 'pull': False, 'certificate': certificate,
            'certificate_source': 'environment' if certificate else 'none'}


def certificate_settings(session):
    """Change public build-CA settings only after successful validation."""
    source = choose('Company CA certificate / this session', [
        ('none', 'Do not use a company CA for this session'),
        ('default', 'Use NRPE_CA_CERT from the environment'),
        ('browse', 'Browse a public .cer/.crt/.pem certificate'),
        ('path', 'Enter or paste a certificate path')],
        description='This CA trusts build downloads; it does not configure NRPE server/client TLS or Docker registry trust.')
    if source is None:
        return
    if source == 'none':
        session.update(certificate=None, certificate_source='disabled')
        return
    value = (os.environ.get('NRPE_CA_CERT') if source == 'default' else
             enter_path('Company CA certificate', kind='file') if source == 'path' else
             browse_certificate(session['certificate']))
    if value is None and source != 'default':
        return
    from .certificates import prepared_certificate
    try:
        with prepared_certificate(value):
            session.update(certificate=str(value) if value else None,
                           certificate_source='environment' if source == 'default' and value
                           else 'manual' if value else 'none')
    except (OSError, RuntimeError) as exc:
        choose(f'Invalid CA certificate: {exc}', [(None, 'Back to options')])


def workflow(root, action, session=None):
    session = new_session() if session is None else session
    states = [{}, {}]
    step = 0
    while True:
        if step == 0:
            options = [(name, TARGET_LABELS[name] + (' / package present' if package_files(root, name) else ''),
                        'linux/amd64; package presence is not a successful checksum or integration check.')
                       for name in TARGETS]
            targets = choose(f'1/3 / {action} / Select targets', options, multiple=True,
                             selected=session['targets'], state=states[0])
            if targets is None:
                return None
            session['targets'] = targets
            step = 1
        elif step == 1:
            source = session['certificate_source']
            certificate = session['certificate']
            options = [('run', 'Continue to review')]
            if action in ('build', 'verify'):
                options.append(('pull', f'Check for updated base images: {"yes" if session["pull"] else "no"}'))
            options.append(('certificate', f'Company CA [{source}]: {compact(certificate) if certificate else "none"}'))
            if certificate:
                options.append(('certificate-info', 'Show complete certificate path'))
            answer = choose(f'2/3 / {action} / Workflow options', options, state=states[1],
                            description='Esc returns to target selection without losing choices. Settings last only for this menu session.')
            if answer is None:
                step = 0
            elif answer == 'pull':
                session['pull'] = not session['pull']
            elif answer == 'certificate':
                certificate_settings(session)
            elif answer == 'certificate-info':
                view_text('Build CA certificate / ' + source, certificate)
            elif answer == 'run':
                # Environment defaults must also be validated before confirmation.
                from .certificates import prepared_certificate
                try:
                    with prepared_certificate(certificate):
                        pass
                except (OSError, RuntimeError) as exc:
                    choose(f'Invalid CA certificate: {exc}', [(None, 'Back to options')])
                    continue
                step = 2
        else:
            targets = session['targets']
            existing = [name for name in targets if package_files(root, name)]
            replacing = action in ('build', 'verify') and bool(existing)
            pull = session['pull'] and action != 'test'
            review = (f'3/3 / Review workflow\nAction: {action} / Targets: {", ".join(targets)}'
                      f'\nUpdate base images: {pull}'
                      f'\nCompany CA [{session["certificate_source"]}]: {compact(session["certificate"] or "none")}'
                      + (f'\nRebuild existing packages: {", ".join(existing)}' if replacing else ''))
            answer = choose(review, [(False, 'Cancel'), ('back', 'Back to options'),
                                    (True, 'Run selected workflow')],
                            description='Containers build/test packages; this never installs them on your workstation. Cancel is selected by default.')
            if answer == 'back':
                step = 1
                continue
            if answer is not True:
                return None
            arguments = [action, *targets]
            if pull:
                arguments.append('--pull')
            if session['certificate']:
                arguments.extend(['--ca-cert', session['certificate']])
            elif session['certificate_source'] == 'disabled':
                arguments.append('--no-ca-cert')
            if replacing:
                arguments.append('--rebuild')
            return arguments


class OutputTail:
    """Bounded UI text; complete Docker output remains in the controller log."""
    def __init__(self):
        from collections import deque
        self.lines = deque(maxlen=5)
        self.pending = ''

    def write(self, text):
        parts = (self.pending + text).split('\n')
        for line in parts[:-1]:
            self.lines.append(safe(line)[-1000:])
        self.pending = parts[-1][-1000:]
        return len(text)

    def flush(self):
        pass

    def isatty(self):
        return False


class LiveWorkflow:
    """Render events while dispatch and signal handling stay on the main thread."""
    def __init__(self, action):
        import time
        self.action = action
        self.started = time.monotonic()
        self.phase_started = self.started
        self.phase = 'Preparing workflow'
        self.run_id = None
        self.states = {}
        self.output = OutputTail()

    def event(self, kind, values):
        import time
        if kind == 'log':
            self.output.write(values['text'])
        elif kind == 'run':
            self.run_id = values['run_id']
        elif kind == 'phase':
            target, phase, status = values['target'], values['phase'], values['status']
            self.states = {**self.states, (target, phase): status}
            if status == 'running':
                self.phase = f'{target} / {phase}'
                self.phase_started = time.monotonic()
        elif kind == 'complete':
            report = values['report']
            self.phase = 'Finished / ' + report['status']
            self.states = {(target, phase): result.get(phase, 'not run')
                           for target, result in report['targets'].items()
                           for phase in ('build', 'package', 'test')}

    def render(self, width=90):
        import time
        elapsed = int(time.monotonic() - self.started)
        phase_elapsed = int(time.monotonic() - self.phase_started)
        lines = [f'NRPE CUSTOM / {self.action.upper()} / {elapsed}s elapsed',
                 f'Run: {self.run_id or "preparing"}', f'Current: {self.phase} ({phase_elapsed}s)', '']
        states = self.states
        targets = list(dict.fromkeys(target for target, _ in states if target != 'Docker'))
        for target in targets:
            lines.append(target + '  ' + '  '.join(
                phase + ': ' + states.get((target, phase), 'not run') for phase in ('build', 'package', 'test')))
        lines += ['', 'Recent output (full output is retained in the run log):']
        lines += list(self.output.lines)
        if self.output.pending:
            lines.append(self.output.pending)
        lines += ['', 'Ctrl+C: cancel safely / full logs retained']
        return '\n'.join(compact(line, max(12, width - 2)) for line in lines)


def dispatch_workflow(action, arguments, dispatch):
    """Optional live display; never move workflow/cancellation into a worker."""
    import contextlib
    import sys
    if not (sys.stdout.isatty() and sys.stdin.isatty()):
        return dispatch(arguments), None
    import threading
    from prompt_toolkit.application import Application
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import create_output, ColorDepth
    from prompt_toolkit.layout import Layout, Window
    from prompt_toolkit.layout.controls import FormattedTextControl
    from .progress import listen

    display = LiveWorkflow(action)
    output = create_output()
    ready = threading.Event()
    failures = []
    with create_pipe_input() as pipe:
        app = Application(input=pipe, output=output, full_screen=False, refresh_interval=0.25,
                          layout=Layout(Window(FormattedTextControl(
                              lambda: display.render(output.get_size().columns)), wrap_lines=False)),
                          color_depth=ColorDepth.DEPTH_1_BIT if 'NO_COLOR' in os.environ or os.environ.get('TERM') == 'dumb' else None)

        def render():
            try:
                app.run(pre_run=ready.set, handle_sigint=False)
            except Exception as exc:
                failures.append(exc)
            finally:
                ready.set()

        thread = threading.Thread(target=render, daemon=True)
        thread.start()
        try:
            if not ready.wait(5) or failures:
                raise RuntimeError('Could not start the live display; use a direct CLI command.')
            with contextlib.redirect_stdout(display.output), listen(display.event):
                code = dispatch(arguments)
        finally:
            if app.is_running:
                app.loop.call_soon_threadsafe(app.exit)
            thread.join(timeout=5)
        if failures:
            print('Live display was unavailable; inspect the recorded result and full logs.')
        return code, display.run_id


def result_menu(root, dispatch, run_id, code):
    history = reports(root)
    report = next((item for item in history if item['id'] == run_id), None)
    if report is None:
        pause(code)
        return
    state = {}
    while True:
        options = [(None, 'Return to workspace'), ('logs', 'View full run logs'),
                   ('diagnose', 'Explain this run log'), ('details', 'Show complete result and paths')]
        for target, result in report.get('targets', {}).items():
            label = target + ' / ' + ' / '.join(phase + ': ' + result.get(phase, 'not run')
                                               for phase in ('build', 'package', 'test'))
            options.append(('target:' + target, label, 'Enter shows package identity and recorded evidence.'))
        answer = choose(f'Result: {report["status"]} / exit {code}\nRun: {run_id}', options,
                        state=state, description=report.get('hint') or report.get('error') or
                        'Recorded results identify tested package bytes, not automatically the current source checkout.')
        if answer is None:
            return
        if answer == 'logs':
            pause(dispatch(['logs', '--run', run_id]))
        elif answer == 'diagnose':
            log = root / '.nrpe' / 'runs' / run_id / 'run.log'
            if not log.is_file():
                choose('No run log is available', [(None, 'Back')])
                continue
            arguments = ['diagnose', str(log)]
            if report.get('ca_certificate_sha256'):
                arguments.append('--ca-configured')
            pause(dispatch(arguments))
        else:
            import json
            data = report.get('targets', {}).get(answer[7:], {}) if answer.startswith('target:') else report
            text = json.dumps(data, indent=2) + '\n\nRun directory: ' + str(root / '.nrpe/runs' / run_id)
            view_text('Recorded result', text)


def prompt_value(title, default=''):
    from prompt_toolkit import prompt
    from prompt_toolkit.key_binding import KeyBindings
    bindings = KeyBindings()

    @bindings.add('escape')
    def cancel(event):
        event.app.exit(result=None)

    return prompt(safe(title) + ' (Esc to cancel): ', default=str(default), key_bindings=bindings)


def select_run(root, title='Select a run (newest first)'):
    history = reports(root)
    if not history:
        choose('No recorded runs', [(None, 'Back')])
        return None
    run_id = choose(title, [(item['id'], f'{item["id"]} / {item["action"]} / '
                            + ', '.join(item.get('targets', {})) + f' / {item["status"]}')
                           for item in history], description='/ filters date, target, action and result.')
    return next((item for item in history if item['id'] == run_id), None)


def diagnostics_menu(root, dispatch):
    while True:
        answer = choose('Diagnostics / choose the evidence', [
            ('doctor', 'Check Docker and Compose readiness'),
            ('run', 'Explain a recorded run log'),
            ('file', 'Explain a local log file'), (None, 'Back to workspace')],
            description='Log diagnosis reads plain text without executing it or changing TLS configuration.')
        if answer is None:
            return None
        if answer == 'doctor':
            code = dispatch(['doctor'])
            pause(code)
            return code
        if answer == 'run':
            report = select_run(root)
            if report is None:
                continue
            path = root / '.nrpe/runs' / report['id'] / 'run.log'
            if not path.is_file():
                choose('No log is available for that run', [(None, 'Back')])
                continue
            args = ['diagnose', str(path)]
            if report.get('ca_certificate_sha256'):
                args.append('--ca-configured')
        else:
            source = choose('Local log file', [('path', 'Enter or paste a path'), ('browse', 'Browse files')])
            if source is None:
                continue
            path = enter_path('Log file', kind='file') if source == 'path' else browse_file()
            if path is None:
                continue
            context = choose('What produced this log?', [('build', 'Build / downloads'),
                                                       ('nrpe', 'NRPE server / check_nrpe')])
            if context is None:
                continue
            args = ['diagnose', str(path), '--context', context]
            if context == 'build':
                configured = choose('Was a company CA supplied for that run?',
                                    [(False, 'No / not known'), (True, 'Yes')])
                if configured is None:
                    continue
                if configured:
                    args.append('--ca-configured')
        pause(dispatch(args))


def cleanup_menu(root, dispatch):
    """Use the existing cleanup planner, preview first, then explicit consent."""
    from .cleanup import IMAGE, inspect_images, plan
    days, keep, images = 30, 5, []
    while True:
        answer = choose('Local cleanup / retention options', [
            ('preview', 'Preview eligible files and selected images'),
            ('days', f'Minimum completed-run age: {days} days'),
            ('keep', f'Keep at least the newest {keep} runs'),
            ('image', 'Add an explicit project image tag'),
            ('clear-images', f'Clear selected images ({len(images)})'), (None, 'Back to workspace')],
            description='Current packages and retained evidence are protected. Preview never deletes; image selection never prunes Docker.')
        if answer is None:
            return
        if answer in ('days', 'keep'):
            value = prompt_value('Retention days' if answer == 'days' else 'Newest runs to retain',
                                 days if answer == 'days' else keep)
            if value is None:
                continue
            try:
                number = int(value)
                if number < 0:
                    raise ValueError()
            except ValueError:
                choose('Enter a nonnegative whole number', [(None, 'Back')])
                continue
            if answer == 'days':
                days = number
            else:
                keep = number
            continue
        if answer == 'clear-images':
            images = []
            continue
        if answer == 'image':
            image = prompt_value('Exact nrpe-custom builder/test image reference')
            if image:
                if not IMAGE.fullmatch(image):
                    choose('Use an explicit project image tag, not a base image, ID or wildcard', [(None, 'Back')])
                elif image not in images:
                    images.append(image)
            continue
        arguments = ['clean', '--older-than', str(days), '--keep-runs', str(keep)]
        for image in images:
            arguments.extend(['--image', image])
        try:
            before = plan(root, days, keep)
            image_before = inspect_images(images)[1]
            code = dispatch(arguments)
            pause(code)  # Let the full preview remain readable before confirmation.
            if code or not (before or image_before):
                continue
            approved = choose(f'Cleanup preview / {len(before)} directories / {len(image_before)} images',
                              [(False, 'Cancel deletion'), (True, 'Delete the previewed candidates')],
                              description='Only the selected retention scope is affected; changes since preview require a new review.')
            if approved is not True:
                continue
            if plan(root, days, keep) != before or inspect_images(images)[1] != image_before:
                choose('Cleanup candidates changed; preview again', [(None, 'Back to options')])
                continue
            pause(dispatch([*arguments, '--apply']))
        except (OSError, RuntimeError) as exc:
            choose('Cleanup refused: ' + str(exc), [(None, 'Back to options')])


def run_menu(root, dispatch):
    """Keep returning to the menu after each command, including failures."""
    actions = [('verify', 'Build and test packages', 'Build, validate and test arguments over TLS in containers.'),
               ('build', 'Build packages', 'Build and check exported artifacts without integration tests.'),
               ('test', 'Test existing packages', 'Test existing bytes; never rebuild packages.'),
               ('diagnostics', 'Diagnostics', 'Check Docker or explain a recorded/local build or NRPE log.'),
               ('clean', 'Local cleanup', 'Preview retention and explicitly confirm eligible deletions.'),
               ('status', 'Show package and test status', 'Validate package checksums and match recorded evidence.'),
               ('logs', 'View run logs', 'Select a recorded run; / filters its date, targets and result.'),
               ('quit', 'Quit')]
    home_state = {}
    session = new_session()
    docker_status = 'not checked'
    try:
        while True:
            history = reports(root)
            count = sum(bool(package_files(root, target)) for target in TARGETS)
            last = (f"{history[0]['action']} / {history[0]['status']}" if history else 'no recorded runs')
            heading = (f'Workspace overview\nPackages present: {count}/{len(TARGETS)} (not verified here)'
                       f'\nLatest run: {last}\nDocker readiness: {docker_status}')
            action = choose(heading, actions, state=home_state)
            if action is None or action == 'quit':
                return 0
            if action in ('verify', 'build', 'test'):
                arguments = workflow(root, action, session)
                if arguments is None:
                    continue
            elif action == 'diagnostics':
                result = diagnostics_menu(root, dispatch)
                if result is not None:
                    docker_status = 'passed last explicit check' if result == 0 else 'last explicit check failed'
                continue
            elif action == 'clean':
                cleanup_menu(root, dispatch)
                continue
            elif action == 'logs':
                report = select_run(root)
                if report is None:
                    continue
                arguments = ['logs', '--run', report['id']]
            else:
                arguments = [action]
            if action in ('verify', 'build', 'test'):
                code, run_id = dispatch_workflow(action, arguments, dispatch)
                if run_id:
                    result_menu(root, dispatch, run_id, code)
                else:
                    pause(code)
                continue
            code = dispatch(arguments)
            if action == 'doctor':
                docker_status = 'passed last explicit check' if code == 0 else 'last explicit check failed'
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
