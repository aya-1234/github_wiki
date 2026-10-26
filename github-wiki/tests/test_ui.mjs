import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import vm from 'node:vm';

const html = readFileSync(new URL('../static/index.html', import.meta.url), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(script, 'UI script exists');

function setup(responses) {
  const elements = new Map();
  const calls = [];
  class Element {
    constructor(id = '') {
      this.id = id;
      this.value = '';
      this.textContent = '';
      this.innerHTML = '';
      this.className = '';
      this.disabled = id === 'publish';
      this.files = [];
      this.listeners = new Map();
      this.children = [];
    }
    addEventListener(type, fn) { this.listeners.set(type, fn); }
    async dispatch(type) { return this.listeners.get(type)?.(); }
    append(...children) { this.children.push(...children); }
  }
  for (const id of ['repository', 'file', 'title', 'body', 'preview', 'warnings', 'publish', 'status']) {
    elements.set(id, new Element(id));
  }
  class FormData {
    items = new Map();
    append(name, value) { this.items.set(name, value); }
  }
  const fetch = async (url, options) => {
    calls.push({ url, options });
    const item = responses[url];
    if (!item) throw Error(`unexpected request: ${url}`);
    const response = await (typeof item === 'function' ? item(options) : item);
    return { ok: response.ok ?? true, json: async () => response.data };
  };
  vm.runInNewContext(script, {
    document: { getElementById: id => elements.get(id), createElement: () => new Element() },
    fetch, FormData,
    setTimeout: fn => { queueMicrotask(fn); return 1; },
    clearTimeout: () => {},
  });
  return { get: id => elements.get(id), calls };
}

async function settle() {
  await new Promise(resolve => setImmediate(resolve));
}

function deferred() {
  let resolve;
  const promise = new Promise(done => { resolve = done; });
  return { promise, resolve };
}

test('Markdown upload, edit, preview, and PR staging result', async () => {
  const ui = setup({
    '/api/convert': { data: { title: 'Guide', markdown: '# Guide', warnings: ['relative link'] } },
    '/api/preview': options => ({ data: { html: `<h1>${JSON.parse(options.body).markdown.slice(2)}</h1>`, warnings: ['relative link'] } }),
    '/api/stage': { data: { path: 'wiki-pages/Guide.md' } },
  });
  assert.equal(ui.get('publish').disabled, true);
  ui.get('repository').value = 'o/r';
  await ui.get('repository').dispatch('input');
  ui.get('file').files = [{ name: 'Guide.md' }];
  await ui.get('file').dispatch('change');
  assert.equal(ui.get('title').value, 'Guide');
  assert.equal(ui.get('body').value, '# Guide');
  assert.equal(ui.get('warnings').textContent, 'relative link');
  assert.equal(ui.get('preview').innerHTML, '<h1>Guide</h1>');
  assert.equal(ui.get('publish').disabled, false);
  ui.get('body').value = '# Edited';
  await ui.get('body').dispatch('input');
  await settle();
  assert.equal(ui.get('preview').innerHTML, '<h1>Edited</h1>');
  await ui.get('publish').dispatch('click');
  const sent = ui.calls.find(call => call.url === '/api/stage');
  assert.equal(JSON.parse(sent.options.body).markdown, '# Edited');
  assert.equal(ui.get('status').className, 'success');
  assert.match(ui.get('status').textContent, /wiki-pages\/Guide\.md/);
  assert.equal(ui.get('publish').disabled, true);
});

test('Office upload shows extraction warning and editable Markdown', async () => {
  const warning = '画像・図形・一部の書式は取り込まれません。元のファイルと照合してください';
  const ui = setup({
    '/api/convert': { data: { title: 'Sales', markdown: '## Sheet1\n\n| Item | Price |', warnings: [warning], sourceWarnings: [warning] } },
    '/api/preview': { data: { html: '<h2>Sheet1</h2>', warnings: [] } },
  });
  ui.get('repository').value = 'o/r';
  await ui.get('repository').dispatch('input');
  ui.get('file').files = [{ name: 'Sales.xlsx' }];
  await ui.get('file').dispatch('change');
  assert.equal(ui.get('title').value, 'Sales');
  assert.match(ui.get('body').value, /Item/);
  assert.match(ui.get('warnings').textContent, /画像/);
  assert.equal(ui.get('publish').disabled, false);
});

test('staging failure keeps edited content and allows retry', async () => {
  const ui = setup({
    '/api/convert': { data: { title: 'Guide', markdown: '# Guide', warnings: [] } },
    '/api/preview': { data: { html: '<h1>Guide</h1>' } },
    '/api/stage': { ok: false, data: { message: '同名の Wiki ページが既にあります' } },
  });
  ui.get('repository').value = 'o/r';
  await ui.get('repository').dispatch('input');
  ui.get('file').files = [{ name: 'Guide.md' }];
  await ui.get('file').dispatch('change');
  ui.get('body').value = '# Edited';
  await ui.get('publish').dispatch('click');
  assert.equal(ui.get('status').className, 'error');
  assert.match(ui.get('status').textContent, /同名/);
  assert.equal(ui.get('body').value, '# Edited');
  assert.equal(ui.get('publish').disabled, false);
});

test('older file conversion cannot replace the latest selection', async () => {
  const first = deferred(), second = deferred();
  const ui = setup({
    '/api/convert': options => options.body.items.get('file').name === 'First.md' ? first.promise : second.promise,
    '/api/preview': options => ({ data: { html: JSON.parse(options.body).markdown } }),
  });
  ui.get('repository').value = 'o/r';
  await ui.get('repository').dispatch('input');
  ui.get('file').files = [{ name: 'First.md' }];
  const firstChange = ui.get('file').dispatch('change');
  ui.get('file').files = [{ name: 'Second.md' }];
  const secondChange = ui.get('file').dispatch('change');
  assert.equal(ui.get('publish').disabled, true);
  second.resolve({ data: { title: 'Second', markdown: '# Second', warnings: [] } });
  await secondChange;
  assert.equal(ui.get('title').value, 'Second');
  assert.equal(ui.get('publish').disabled, false);
  first.resolve({ ok: false, data: { message: 'old conversion failed' } });
  await firstChange;
  assert.equal(ui.get('title').value, 'Second');
  assert.equal(ui.get('body').value, '# Second');
  assert.equal(ui.get('preview').innerHTML, '# Second');
  assert.equal(ui.get('status').className, '');
  assert.equal(ui.get('publish').disabled, false);
});

test('older conversion completing first keeps publishing disabled', async () => {
  const first = deferred(), second = deferred();
  const ui = setup({
    '/api/convert': options => options.body.items.get('file').name === 'First.md' ? first.promise : second.promise,
    '/api/preview': { data: { html: '<h1>Second</h1>' } },
  });
  ui.get('repository').value = 'o/r';
  await ui.get('repository').dispatch('input');
  ui.get('file').files = [{ name: 'First.md' }];
  const firstChange = ui.get('file').dispatch('change');
  ui.get('file').files = [{ name: 'Second.md' }];
  const secondChange = ui.get('file').dispatch('change');
  first.resolve({ data: { title: 'First', markdown: '# First', warnings: [] } });
  await firstChange;
  assert.equal(ui.get('title').value, '');
  assert.equal(ui.get('body').value, '');
  assert.equal(ui.get('publish').disabled, true);
  second.resolve({ data: { title: 'Second', markdown: '# Second', warnings: [] } });
  await secondChange;
  assert.equal(ui.get('title').value, 'Second');
  assert.equal(ui.get('publish').disabled, false);
});

test('older preview cannot replace newer edited Markdown', async () => {
  const first = deferred(), second = deferred();
  const ui = setup({
    '/api/convert': { data: { title: 'Guide', markdown: '# Base', warnings: [] } },
    '/api/preview': options => {
      const body = JSON.parse(options.body).markdown;
      if (body === '# First') return first.promise;
      if (body === '# Second') return second.promise;
      return { data: { html: '<h1>Base</h1>' } };
    },
  });
  ui.get('repository').value = 'o/r';
  await ui.get('repository').dispatch('input');
  ui.get('file').files = [{ name: 'Guide.md' }];
  await ui.get('file').dispatch('change');
  ui.get('body').value = '# First';
  await ui.get('body').dispatch('input');
  await settle();
  ui.get('body').value = '# Second';
  await ui.get('body').dispatch('input');
  await settle();
  second.resolve({ data: { html: '<h1>Second</h1>' } });
  await settle();
  assert.equal(ui.get('preview').innerHTML, '<h1>Second</h1>');
  first.resolve({ ok: false, data: { message: 'old preview failed' } });
  await settle();
  assert.equal(ui.get('preview').innerHTML, '<h1>Second</h1>');
  assert.equal(ui.get('publish').disabled, false);
});

test('relative image warning follows edited Markdown', async () => {
  const ui = setup({
    '/api/convert': { data: { title: 'Guide', markdown: '![logo](img/logo.png)', warnings: ['相対画像: img/logo.png'], sourceWarnings: [] } },
    '/api/preview': options => {
      const body = JSON.parse(options.body).markdown;
      return { data: { html: body, warnings: body.includes('img/logo.png') ? ['相対画像: img/logo.png'] : [] } };
    },
  });
  ui.get('file').files = [{ name: 'Guide.md' }];
  await ui.get('file').dispatch('change');
  assert.match(ui.get('warnings').textContent, /img\/logo.png/);
  ui.get('body').value = '![logo](https://example.com/logo.png)';
  await ui.get('body').dispatch('input');
  await settle();
  assert.equal(ui.get('warnings').textContent, '');
});

test('source warning stays visible after Markdown edits', async () => {
  const note = '抽出文字が少ないため、元の PDF と照合してください';
  const ui = setup({
    '/api/convert': { data: { title: 'Scanned', markdown: '## PDF 1ページ目', warnings: [note], sourceWarnings: [note] } },
    '/api/preview': { data: { html: '<h2>PDF</h2>', warnings: [] } },
  });
  ui.get('file').files = [{ name: 'Scanned.pdf' }];
  await ui.get('file').dispatch('change');
  ui.get('body').value = 'edited PDF text';
  await ui.get('body').dispatch('input');
  await settle();
  assert.equal(ui.get('warnings').textContent, note);
});
