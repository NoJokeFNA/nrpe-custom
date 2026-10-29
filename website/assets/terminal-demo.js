// An in-memory example, deliberately independent of the real CLI/controller.
const demo = document.querySelector('[data-terminal-demo]');
if (demo) {
  const find = name => demo.querySelector(`[data-demo-${name}]`);
  const output = find('output'), input = find('input'), target = find('target');
  const menu = [...demo.querySelectorAll('[data-demo-command]')];
  const targets = [...target.options].map(option => option.value);
  const artifacts = new Set(), reports = [];
  let expired = 2, generation = 0, busy = false, pending = null, selected = 0;
  const line = text => {
    const row = document.createElement('span');
    row.className = 'demo-line'; row.textContent = text + '\n'; output.append(row);
    while (output.children.length > 80) output.firstElementChild.remove();
    output.scrollTop = output.scrollHeight;
  };
  const phase = value => { find('phase').textContent = value; };
  const lock = value => {
    busy = value; target.disabled = value; find('cancel').disabled = !value;
    output.setAttribute('aria-busy', String(value));
  };
  const dismiss = () => { pending = null; find('confirm').hidden = true; };
  const cancel = () => {
    generation++; dismiss();
    if (busy) line('Run cancelled. No unfinished demo package was recorded.');
    lock(false); phase('Ready');
  };
  const confirm = (question, callback) => {
    pending = callback; find('question').textContent = question;
    find('confirm').hidden = false; find('yes').focus();
  };
  const status = () => {
    line('Sample workspace — runtime arguments remain disabled by default.');
    targets.forEach(name => line(`${name.padEnd(12)} ${artifacts.has(name) ? 'sample package present' : 'not built'}`));
  };
  const help = () => {
    line('Demo commands (the real CLI supports more options):');
    line('  python3 nrpe.py verify debian12');
    line('  build TARGET [--rebuild]   test TARGET   status   doctor');
    line('  logs [--last]   clean   clean --apply   help   clear');
    line('Choose another target above. Build results and diagnostics are simulated.');
  };
  const run = async (action, name, rebuild) => {
    if (action === 'test' && !artifacts.has(name)) { line('No demo package exists. Use build or verify first.'); return; }
    if (action !== 'test' && artifacts.has(name) && !rebuild) {
      confirm(`A demo package already exists for ${name}. Rebuild it?`, () => run(action, name, true)); return;
    }
    const token = ++generation;
    lock(true);
    const steps = action === 'test' ? ['Install in a disposable test container', 'Exercise disabled/enabled arguments over TLS']
      : ['Build the distribution package', 'Inspect package metadata and corresponding sources',
         ...(action === 'verify' ? ['Install and exercise arguments over TLS'] : [])];
    line(`${action} ${name} — simulated run`);
    for (const step of steps) {
      phase(step); line('→ ' + step);
      await new Promise(resolve => setTimeout(resolve, 550));
      if (generation !== token) return;
    }
    artifacts.add(name);
    reports.push(`${action} ${name}: sample checks completed; this is not a real build result.`);
    line('✓ Demo complete. A real run requires your workstation and Docker.');
    lock(false); phase('Demo complete');
  };
  const execute = command => {
    const raw = command.trim();
    if (!raw) return;
    if (busy) { line('A demo run is active. Cancel it before starting another command.'); return; }
    dismiss(); line('$ ' + raw);
    let words = raw.split(/\s+/);
    if (['python3', 'python'].includes(words[0])) words.shift();
    if (words[0] === 'nrpe.py') words.shift();
    const action = words.shift(), name = words.find(word => !word.startsWith('-'));
    if (['verify', 'build', 'test'].includes(action)) {
      if (!targets.includes(name) || words.some(word => word !== name && word !== '--rebuild')
          || (action === 'test' && words.includes('--rebuild'))) {
        line('Choose one supported demo target. Use help for the available command subset.'); return;
      }
      target.value = name; void run(action, name, words.includes('--rebuild')); return;
    }
    if (['help', '--help', '-h'].includes(action) && !words.length) { help(); return; }
    if (action === 'clear' && !words.length) { output.replaceChildren(); return; }
    if (action === 'status' && !words.length) { status(); return; }
    if (action === 'doctor' && !words.length) {
      line('Example diagnostics: Docker reachable; Compose available; workspace writable.');
      line('These fixture results do not inspect your browser or workstation.'); return;
    }
    if (action === 'logs' && (!words.length || words.join(' ') === '--last')) {
      line(reports.at(-1) || 'No demo run yet. Try verify debian12.'); return;
    }
    if (action === 'clean' && (!words.length || words.join(' ') === '--apply')) {
      line(`Cleanup preview: ${expired} sample expired reports beyond the 5 newest retained runs.`);
      line('Current package outputs and current evidence are retained.');
      if (words.length && expired) confirm('Apply this cleanup to the demo workspace?', () => {
        line(`Removed ${expired} sample expired reports. Packages retained.`); expired = 0; phase('Cleanup complete');
      });
      return;
    }
    line('Command not implemented in this browser demo. Type help for supported examples.');
  };
  const choose = index => {
    selected = (index + menu.length) % menu.length;
    menu.forEach((button, i) => { button.tabIndex = i === selected ? 0 : -1; button.classList.toggle('selected', i === selected); });
  };
  menu.forEach((button, index) => {
    button.addEventListener('focus', () => choose(index));
    button.addEventListener('click', () => {
      choose(index); const action = button.dataset.demoCommand;
      execute(action === 'verify' ? `verify ${target.value}` : action);
    });
    button.addEventListener('keydown', event => {
      if (!['ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();
      choose(event.key === 'Home' ? 0 : event.key === 'End' ? menu.length - 1 : selected + (event.key === 'ArrowDown' ? 1 : -1));
      menu[selected].focus();
    });
  });
  find('form').addEventListener('submit', event => { event.preventDefault(); execute(input.value); input.value = ''; });
  find('cancel').addEventListener('click', cancel);
  find('no').addEventListener('click', () => { dismiss(); line('Action cancelled. Demo data retained.'); input.focus(); });
  find('yes').addEventListener('click', () => { const action = pending; dismiss(); action?.(); input.focus(); });
  demo.addEventListener('keydown', event => {
    if (event.key === 'Escape' || (busy && event.ctrlKey && event.key.toLowerCase() === 'c')) {
      event.preventDefault(); cancel(); input.focus();
    }
  });
  const reset = () => {
    cancel(); artifacts.clear(); reports.length = 0; expired = 2;
    output.replaceChildren(); input.value = ''; target.selectedIndex = 0;
    line('Welcome to the NRPE Custom interactive demo.');
    line('Use the menu or type help. All data stays in this page and resets on reload.');
    choose(0);
  };
  find('reset').addEventListener('click', reset);
  demo.hidden = false; reset();
}
