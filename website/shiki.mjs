// Build-only tokenization. No Shiki code or language grammar is sent to browsers.
import { createHighlighter } from 'shiki';

if (Number(process.versions.node.split('.')[0]) !== 24) {
  throw new Error('Website highlighting requires Node.js 24 LTS.');
}
const template = { match: '@[A-Za-z_][A-Za-z0-9_]*@', name: 'variable.language.nrpe' };
const argument = { match: '\\$ARG[0-9]+\\$', name: 'variable.language.nrpe' };
const nrpe = {
  name: 'nrpe', scopeName: 'source.nrpe', displayName: 'NRPE config',
  patterns: [
    { match: '^\\s*#.*$', name: 'comment.line.number-sign.nrpe' },
    {
      begin: '^(\\s*)(command)(\\[)([^\\]\\r\\n]+)(\\])(\\s*)(=)', end: '$',
      beginCaptures: {
        2: { name: 'support.type.property-name.nrpe' },
        3: { name: 'punctuation.definition.nrpe' },
        4: { name: 'entity.name.function.nrpe' },
        5: { name: 'punctuation.definition.nrpe' },
        7: { name: 'keyword.operator.assignment.nrpe' },
      },
      contentName: 'string.unquoted.nrpe',
      patterns: [template, argument,
        { begin: "'", end: "'", name: 'string.quoted.single.nrpe', patterns: [template, argument] },
        { begin: '"', end: '"', name: 'string.quoted.double.nrpe', patterns: [template, argument] },
        { match: '(?<!\\S)--?[A-Za-z][A-Za-z0-9_-]*', name: 'entity.other.attribute-name.nrpe' },
        { include: 'source.shell' }],
    },
    {
      begin: '^(\\s*)([A-Za-z_][A-Za-z0-9_]*)(\\s*)(=)', end: '$',
      beginCaptures: {
        2: { name: 'support.type.property-name.nrpe' },
        4: { name: 'keyword.operator.assignment.nrpe' },
      },
      contentName: 'string.unquoted.nrpe', patterns: [template, argument],
    },
  ],
};
const highlighter = await createHighlighter({
  themes: ['github-dark-default'],
  langs: ['bash', 'powershell', 'ini', 'python', 'yaml', 'json', 'dockerfile', 'diff', nrpe],
});
try {
  process.stdin.setEncoding('utf8');
  let input = '';
  for await (const chunk of process.stdin) input += chunk;
  const requests = JSON.parse(input);
  const theme = highlighter.getTheme('github-dark-default');
  const palette = [...new Set([theme.fg, theme.bg, ...theme.settings.flatMap(item =>
    [item.settings.foreground, item.settings.background]).filter(Boolean)])];
  const blocks = requests.map(([lang, source]) => {
    const result = highlighter.codeToTokens(source, { lang, theme: 'github-dark-default' });
    return result.tokens.map(line => line.map(({ content, color, bgColor, fontStyle }) =>
      ({ content, color: color || theme.fg, bgColor, fontStyle })));
  });
  process.stdout.write(JSON.stringify({ fg: theme.fg, bg: theme.bg, palette, blocks }));
} finally {
  highlighter.dispose();
}
