const fs = require('fs');
const out = [];
for (const dir of ['package','creativity/package','economics/package','entrepreneur/package','financial/package','management/package']) {
  const m = require('./npm/' + dir + '/dist/index.cjs');
  for (const [k, v] of Object.entries(m)) {
    if (Array.isArray(v)) for (const q of v) if (q && q.quote) out.push({figure: q.figure, mark: q.mark, quote: q.quote, pkg: dir});
    else if (v && typeof v === 'object') for (const [k2, arr] of Object.entries(v)) if (Array.isArray(arr)) for (const q of arr) if (q && q.quote) out.push({figure: q.figure, mark: q.mark, quote: q.quote, pkg: dir});
  }
}
fs.writeFileSync('foba_quotes.jsonl', out.map(o => JSON.stringify(o)).join('\n') + '\n');
console.log(out.length);
