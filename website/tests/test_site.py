"""Static docs, safe output replacement and human-only deployment invariants."""

import contextlib
import io
import json
import hashlib
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from website.build import ROOT as PROJECT, build, validate
from website.publish import publish, git


class SiteTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / 'site'

    def test_every_source_page_and_anchor_resolves_at_project_base(self):
        manifest = build(self.output)
        validate(self.output, '/nrpe-custom')
        self.assertGreaterEqual(manifest['pages'], 32)
        home = (self.output / 'index.html').read_text()
        self.assertIn('Custom NRPE builds.', home)
        self.assertIn('/nrpe-custom/faq/', home)
        faq = (self.output / 'faq/index.html').read_text()
        self.assertIn('class="faq-item"', faq)
        self.assertIn('What happened to SLES 15', faq)
        self.assertNotIn('AGENTS.md', manifest['files'])
        self.assertFalse(any(name.endswith(('.key', '.pem', '.log')) for name in manifest['files']))
        self.assertEqual((self.output / 'notices/NRPE-GPL-2.0.md').read_bytes(),
                         (PROJECT / 'packaging/licenses/sles12sp3/NRPE-GPL-2.0.md').read_bytes())

    def test_docs_remain_the_content_source_and_search_is_local(self):
        build(self.output)
        search = json.loads((self.output / 'assets/search-index.json').read_text())
        entry = next(page for page in search if page['url'].endswith('/local-cleanup/'))
        self.assertIn('--apply', entry['text'])
        self.assertIn('maintenance guard', entry['text'])
        self.assertTrue(all(page['url'].startswith('/nrpe-custom/') for page in search))

    def test_missing_internal_anchor_is_a_build_validation_error(self):
        build(self.output)
        path = self.output / 'index.html'
        path.write_text(path.read_text() + '<a href="/nrpe-custom/faq/#missing-anchor">Broken</a>')
        with self.assertRaisesRegex(ValueError, 'Missing anchor'):
            validate(self.output, '/nrpe-custom')

    def test_arbitrary_nonempty_output_is_never_replaced(self):
        self.output.mkdir()
        note = self.output / 'operator.txt'
        note.write_text('keep')
        with self.assertRaisesRegex(ValueError, 'not owned'):
            build(self.output)
        self.assertEqual(note.read_text(), 'keep')

    def test_owned_output_can_be_rebuilt_without_stale_files(self):
        build(self.output)
        (self.output / 'stale.html').write_text('old')
        path = self.output / 'site-manifest.json'
        manifest = json.loads(path.read_text())
        manifest['files']['stale.html'] = hashlib.sha256(b'old').hexdigest()
        path.write_text(json.dumps(manifest))
        build(self.output)
        self.assertFalse((self.output / 'stale.html').exists())

    def test_linked_output_is_not_replaced(self):
        destination = self.root / 'other'
        destination.mkdir()
        try:
            self.output.symlink_to(destination, target_is_directory=True)
        except OSError:
            self.skipTest('Host does not allow symlinks')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            build(self.output)
        self.assertTrue(destination.exists())

    def test_unknown_files_in_owned_output_and_workflow_state_are_protected(self):
        build(self.output)
        note = self.output / 'operator-backup.txt'
        note.write_text('keep')
        with self.assertRaisesRegex(ValueError, 'unknown files'):
            build(self.output)
        self.assertEqual(note.read_text(), 'keep')
        with self.assertRaisesRegex(ValueError, 'dedicated output'):
            build(PROJECT / '.nrpe')

    def test_reviewed_content_and_readme_target_changes_are_reflected(self):
        source = self.root / 'source'
        source.mkdir()
        for name in ('README.md', 'CONTRIBUTING.md', 'THIRD_PARTY.md', 'LICENSE'):
            shutil.copyfile(PROJECT / name, source / name)
        for name in ('docs', 'website/assets', 'website/content', 'packaging/licenses/sles12sp3'):
            shutil.copytree(PROJECT / name, source / name)
        (source / 'website/content/test observation.md').write_text(
            '# A fixture observation\n\n**Test fixture only**\n\nAn example used by an isolated unit test.\n')
        readme = source / 'README.md'
        readme.write_text(readme.read_text().replace('Debian 12 Bookworm', 'Debian 12 fixture label'))
        build(self.output, root=source)
        homepage = (self.output / 'index.html').read_text()
        self.assertIn('Debian 12 fixture label', homepage)
        self.assertNotIn('Debian 12 Bookworm', homepage)
        listing = (self.output / 'field-notes/index.html').read_text()
        self.assertIn('A fixture observation', listing)
        self.assertIn('/nrpe-custom/field-notes/test%20observation/', listing)


class PublicationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.repo = self.directory / 'repo'
        self.repo.mkdir()
        git(self.repo, 'init', '-b', 'develop')
        git(self.repo, 'config', 'user.name', 'Example Maintainer')
        git(self.repo, 'config', 'user.email', 'maintainer@example.invalid')
        (self.repo / '.gitignore').write_text('.nrpe/\n')
        git(self.repo, 'add', '--', '.gitignore')
        git(self.repo, 'commit', '-m', 'docs: initialize test source')
        self.source = git(self.repo, 'rev-parse', 'HEAD')
        self.output = self.repo / '.nrpe/site'
        self.output.parent.mkdir()
        build(self.output)
        self.bind_manifest()
        self.remote = self.directory / 'remote.git'
        subprocess.check_call(['git', 'init', '--bare', str(self.remote)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        git(self.repo, 'remote', 'add', 'origin', str(self.remote))
        redirect = contextlib.redirect_stdout(io.StringIO())
        redirect.__enter__()
        self.addCleanup(redirect.__exit__, None, None, None)

    def bind_manifest(self):
        path = self.output / 'site-manifest.json'
        manifest = json.loads(path.read_text())
        manifest.update(source_commit=self.source, dirty=False)
        path.write_text(json.dumps(manifest))

    def test_preview_does_not_change_refs_or_source_index(self):
        before = git(self.repo, 'show-ref')
        self.assertIsNone(publish(self.repo, self.output))
        self.assertEqual(git(self.repo, 'show-ref'), before)
        self.assertEqual(git(self.repo, 'status', '--porcelain'), '')

    def test_append_only_human_deployment_contains_only_checked_site_files(self):
        first = publish(self.repo, self.output, push=True)
        second = publish(self.repo, self.output, push=True)
        self.assertEqual(git(self.repo, 'rev-parse', second + '^'), first)
        self.assertEqual(git(self.repo, 'rev-parse', 'HEAD'), self.source)
        self.assertEqual(git(self.repo, 'status', '--porcelain'), '')
        refs = git(self.repo, 'ls-remote', '--heads', 'origin')
        self.assertIn('refs/heads/gh-pages', refs)
        self.assertNotIn('refs/heads/master', refs)
        self.assertNotIn('refs/heads/develop', refs)
        names = git(self.repo, 'ls-tree', '-r', '--name-only', second).splitlines()
        self.assertIn('index.html', names)
        self.assertNotIn('.gitignore', names)
        self.assertEqual(git(self.repo, 'show', '-s', '--format=%an', second), 'Example Maintainer')

    def test_dirty_source_and_feature_branch_are_refused(self):
        (self.repo / 'unreviewed.txt').write_text('not reviewed')
        with self.assertRaisesRegex(RuntimeError, 'clean committed'):
            publish(self.repo, self.output, push=True)
        (self.repo / 'unreviewed.txt').unlink()
        git(self.repo, 'switch', '-c', 'feat/example')
        with self.assertRaisesRegex(RuntimeError, 'review website'):
            publish(self.repo, self.output, push=True)

    def test_extra_changed_and_stale_assets_are_refused(self):
        extra = self.output / 'private.log'
        extra.write_text('not public')
        with self.assertRaisesRegex(RuntimeError, 'extra or missing'):
            publish(self.repo, self.output, push=True)
        extra.unlink()
        page = self.output / 'index.html'
        page.write_text(page.read_text() + 'changed')
        with self.assertRaisesRegex(RuntimeError, 'asset changed'):
            publish(self.repo, self.output, push=True)

    def test_wrong_base_path_and_bot_identity_are_refused(self):
        path = self.output / 'site-manifest.json'
        manifest = json.loads(path.read_text())
        manifest['base_path'] = '/'
        path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(RuntimeError, 'production base path'):
            publish(self.repo, self.output, push=True)
        manifest['base_path'] = '/nrpe-custom'
        path.write_text(json.dumps(manifest))
        git(self.repo, 'config', 'user.name', 'github-actions[bot]')
        with self.assertRaisesRegex(ValueError, 'human author'):
            publish(self.repo, self.output, push=True)
