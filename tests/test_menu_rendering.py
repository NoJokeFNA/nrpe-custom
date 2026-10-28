"""Real prompt_toolkit rendering in small/resized terminal dimensions."""
import unittest
from unittest.mock import patch
from nrpe_cli import menu

try:
    from prompt_toolkit.application import Application
    from prompt_toolkit.input import create_pipe_input
    from prompt_toolkit.output import DummyOutput
    from prompt_toolkit.data_structures import Size
except ImportError:
    Application = None


@unittest.skipIf(Application is None, 'Install requirements-menu.txt')
class RenderingTests(unittest.TestCase):
    def test_resize_preserves_selected_entry_and_restores_scroll(self):
        class Terminal(DummyOutput):
            size = Size(rows=30, columns=100)
            def get_size(self):
                return self.size
        output = Terminal()
        frames = []
        with create_pipe_input() as pipe:
            def capture(app):
                screen = app.renderer.last_rendered_screen
                if screen is None:
                    return
                frames.append('\n'.join(''.join(screen.data_buffer[y][x].char
                                                for x in range(output.size.columns))
                                         for y in range(output.size.rows)))
                if len(frames) == 1:
                    output.size = Size(rows=16, columns=60)
                    app.invalidate()
                else:
                    pipe.send_text('q')
            def create(**kwargs):
                app = Application(input=pipe, output=output, **kwargs)
                app.after_render += capture
                return app
            state = {'focus':'item:29'}
            with patch('prompt_toolkit.application.Application', side_effect=create):
                menu.choose('A very long current directory /' + 'folder/' * 20,
                            [(f'item:{index}', f'Item {index}') for index in range(30)], state=state)
            self.assertGreaterEqual(len(frames), 2)
            self.assertIn('> Item 29', frames[1])
            self.assertEqual(state['focus'], 'item:29')
            self.assertGreater(state['scroll'], 0)

    def test_narrow_terminal_keeps_last_selected_drive_visible(self):
        for columns, rows in ((60, 16), (80, 24), (100, 30)):
            frames = []
            class Terminal(DummyOutput):
                def get_size(self):
                    return Size(rows=rows, columns=columns)
            with create_pipe_input() as pipe:
                def capture(app):
                    screen = app.renderer.last_rendered_screen
                    if screen is not None:
                        frames.append('\n'.join(''.join(screen.data_buffer[y][x].char for x in range(columns))
                                                 for y in range(rows)))
                    pipe.send_text('q')
                def create(**kwargs):
                    app = Application(input=pipe, output=Terminal(), **kwargs)
                    app.after_render += capture
                    return app
                options = [(f'drive:{index}', f'Drive {index}') for index in range(12)]
                state = {'focus':'drive:11'}
                with patch('prompt_toolkit.application.Application', side_effect=create):
                    self.assertIsNone(menu.choose('Drive selector', options, state=state,
                                                 description='Use / to filter; Esc returns.'))
                self.assertTrue(any('> Drive 11' in frame for frame in frames), (columns, rows))
                self.assertEqual(state['focus'], 'drive:11')
                self.assertIn('scroll', state)

    def test_plain_text_view_supports_search_and_escape_before_return(self):
        with create_pipe_input() as pipe:
            # Ctrl+F starts search; first Esc closes search; second closes viewer.
            pipe.send_text('\x06needle\x1b\x1b')
            def create(**kwargs):
                return Application(input=pipe, output=DummyOutput(), **kwargs)
            with patch('prompt_toolkit.application.Application', side_effect=create):
                menu.view_text('Long path', 'prefix/' * 150 + 'needle')
