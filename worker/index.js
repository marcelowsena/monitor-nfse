/**
 * Monitor NFS-e — Cloudflare Worker
 *
 * KV keys (binding: KV):
 *   {obra}:pendentes           → JSON array de notas NFS-e pendentes
 *   {obra}:lancadas            → JSON array de notas NFS-e lançadas
 *   {obra}:pendentes_nfe       → JSON array de NF-e (material) pendentes
 *   {obra}:lancadas_nfe        → JSON array de NF-e (material) lançadas
 *   {obra}:ultimo_nsu          → string com o último NSU NFS-e processado
 *   {obra}:ultimo_nsu_nfe      → string com o último NSU NF-e processado
 *   {obra}:ultima_verificacao  → string ISO da última verificação
 *   pdf:{chave}                → PDF bytes (ArrayBuffer)
 *
 * Rotas:
 *   GET  /                             → Dashboard HTML
 *   GET  /api/pendentes?token=...      → JSON para o SPFx web part (CORS)
 *   GET  /api/estado/:obra?token=...   → Estado do NSU para o script Python
 *   POST /api/sync  (Bearer token)     → Grava notas + estado no KV
 *   POST /api/pdf/:chave (Bearer)      → Armazena PDF no KV
 *   GET  /api/pdf/:chave?token=...     → Serve PDF ao browser
 */

const OBRAS = [
  { key: "max",                 nome: "Pulse — HLT Max Colin SPE",          regiao: "joinville" },
  { key: "arium",               nome: "Arium — HPB CDA 4",                  regiao: "joinville" },
  { key: "confraria_benjamin",  nome: "Confraria Benjamin — HLT 11",        regiao: "joinville" },
  { key: "cora",                nome: "Cora — Benjamin Constant",           regiao: "joinville" },
  { key: "nola",                nome: "Nola — HPB CDA 3",                   regiao: "joinville" },
  { key: "emanuel_pinto",       nome: "Emanuel Pinto — Empreendimento 4",   regiao: "litoral"   },
  { key: "essenza",             nome: "Essenza — HLT Empreendimento 7",     regiao: "litoral"   },
  { key: "massimo",             nome: "Massimo — Empreendimento Picarras 5",regiao: "litoral"   },
  { key: "naut",                nome: "Naut — Naut Empreendimento",         regiao: "litoral"   },
  { key: "neoon",               nome: "Neoon — Neoon 3122",                 regiao: "litoral"   },
  { key: "nort_beach",          nome: "Nort Beach — HLT Empreendimento 6",  regiao: "litoral"   },
];

// Cache em memória com TTL (1 hora = 3600s)
const CACHE_TTL = 3600;
let cache = {};

function getCached(key) {
  if (!cache[key]) return null;
  const { data, expiry } = cache[key];
  if (Date.now() > expiry) {
    delete cache[key];
    return null;
  }
  return data;
}

function setCached(key, data) {
  cache[key] = { data, expiry: Date.now() + CACHE_TTL * 1000 };
}

export default {
  async fetch(request, env) {
    const url    = new URL(request.url);
    const origin = request.headers.get('Origin') || '';

    const cors = {
      'Access-Control-Allow-Origin':  origin || '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
    };

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: cors });
    }

    const json = (body, status = 200) =>
      new Response(JSON.stringify(body), {
        status,
        headers: { ...cors, 'Content-Type': 'application/json' },
      });

    const checkToken  = () => url.searchParams.get('token') === env.API_TOKEN;
    const checkBearer = () => (request.headers.get('Authorization') || '') === `Bearer ${env.API_TOKEN}`;

    // ── GET /api/pendentes?token=... ────────────────────────────────
    if (url.pathname === '/api/pendentes' && request.method === 'GET') {
      if (!checkToken()) return json({ error: 'Unauthorized' }, 401);

      // Tentar cache primeiro
      const cacheKey = 'pendentes_all';
      let dados = getCached(cacheKey);

      if (!dados) {
        // Se não estiver em cache, carregar do KV e cachear
        dados = await Promise.all(OBRAS.map(o => carregarObra(o, env)));
        setCached(cacheKey, dados);
      }

      return json(dados);
    }

    // ── GET /api/estado/:obra?token=... ─────────────────────────────
    if (url.pathname.startsWith('/api/estado/') && request.method === 'GET') {
      if (!checkToken()) return json({ error: 'Unauthorized' }, 401);
      const obra = url.pathname.split('/')[3];
      const [nsu, verif, nsuNfe] = await Promise.all([
        env.KV.get(`${obra}:ultimo_nsu`, 'text'),
        env.KV.get(`${obra}:ultima_verificacao`, 'text'),
        env.KV.get(`${obra}:ultimo_nsu_nfe`, 'text'),
      ]);
      return json({
        ultimo_nsu:         parseInt(nsu    || '0', 10),
        ultima_verificacao: verif || '',
        ultimo_nsu_nfe:     parseInt(nsuNfe || '0', 10),
      });
    }

    // ── POST /api/sync  (Bearer) ────────────────────────────────────
    if (url.pathname === '/api/sync' && request.method === 'POST') {
      if (!checkBearer()) return json({ error: 'Unauthorized' }, 401);
      const { obra, pendentes, lancadas, ultimo_nsu, ultima_verificacao,
              pendentes_nfe, lancadas_nfe, ultimo_nsu_nfe } = await request.json();
      if (!obra) return json({ error: 'Campo "obra" obrigatorio' }, 400);

      // Tentar sincronizar com retry (em caso de limite do KV)
      const putWithRetry = async (key, value) => {
        for (let i = 0; i < 3; i++) {
          try {
            await env.KV.put(key, value);
            return true;
          } catch (e) {
            console.error(`Retry ${i+1}/3 para ${key}:`, e);
            if (i < 2) await new Promise(resolve => setTimeout(resolve, 1000));
          }
        }
        console.error(`Falha permanente ao salvar ${key} após 3 tentativas`);
        return false;
      };

      // Executar com retry
      const results = await Promise.all([
        pendentes !== undefined
          ? putWithRetry(`${obra}:pendentes`, JSON.stringify(pendentes))
          : Promise.resolve(true),
        lancadas !== undefined
          ? putWithRetry(`${obra}:lancadas`, JSON.stringify(lancadas))
          : Promise.resolve(true),
        ultimo_nsu !== undefined
          ? putWithRetry(`${obra}:ultimo_nsu`, String(ultimo_nsu))
          : Promise.resolve(true),
        ultima_verificacao !== undefined
          ? putWithRetry(`${obra}:ultima_verificacao`, ultima_verificacao)
          : Promise.resolve(true),
        pendentes_nfe !== undefined
          ? putWithRetry(`${obra}:pendentes_nfe`, JSON.stringify(pendentes_nfe))
          : Promise.resolve(true),
        lancadas_nfe !== undefined
          ? putWithRetry(`${obra}:lancadas_nfe`, JSON.stringify(lancadas_nfe))
          : Promise.resolve(true),
        ultimo_nsu_nfe !== undefined
          ? putWithRetry(`${obra}:ultimo_nsu_nfe`, String(ultimo_nsu_nfe))
          : Promise.resolve(true),
      ]);

      // Invalidar cache desta obra e do agregado
      delete cache[`obra_${obra}`];
      delete cache['pendentes_all'];

      const allSuccess = results.every(r => r);
      return json({ ok: allSuccess, obra, status: allSuccess ? 'synced' : 'partial' });
    }

    // ── GET /api/pdf/:chave?token=... ───────────────────────────────
    if (url.pathname.startsWith('/api/pdf/') && request.method === 'GET') {
      if (!checkToken()) return json({ error: 'Unauthorized' }, 401);
      const chave = url.pathname.split('/api/pdf/')[1];
      const buf = await env.KV.get(`pdf:${chave}`, 'arrayBuffer');
      if (!buf) return new Response('PDF não encontrado', { status: 404 });
      return new Response(buf, {
        headers: {
          ...cors,
          'Content-Type': 'application/pdf',
          'Content-Disposition': `inline; filename="${chave}.pdf"`,
        },
      });
    }

    // ── POST /api/pdf/:chave (Bearer) ────────────────────────────────
    if (url.pathname.startsWith('/api/pdf/') && request.method === 'POST') {
      if (!checkBearer()) return json({ error: 'Unauthorized' }, 401);
      const chave = url.pathname.split('/api/pdf/')[1];
      const buf = await request.arrayBuffer();

      // Tentar salvar PDF com retry (em caso de limite do KV)
      let salvo = false;
      for (let i = 0; i < 3; i++) {
        try {
          await env.KV.put(`pdf:${chave}`, buf);
          salvo = true;
          break;
        } catch (e) {
          if (i === 2) {
            // Após 3 tentativas, retornar erro mas não falhar a sincronização
            console.error(`Falha ao salvar PDF ${chave}:`, e);
            return json({ warning: 'PDF não salvo (KV limite?)', chave }, 202);
          }
          await new Promise(resolve => setTimeout(resolve, 1000)); // Esperar 1s antes de retry
        }
      }

      return json({ ok: true });
    }

    // ── GET / — Dashboard HTML (requer token) ──────────────────────
    if (!checkToken()) {
      return new Response('Acesso negado. Adicione ?token=SEU_TOKEN na URL.', {
        status: 401,
        headers: { 'Content-Type': 'text/plain;charset=UTF-8' },
      });
    }
    return dashboard(env);
  },
};

// ──────────────────────────────────────────────────────────────────
// Dashboard HTML
// ──────────────────────────────────────────────────────────────────

async function dashboard(env) {
  const dadosObras     = await Promise.all(OBRAS.map(o => carregarObra(o, env)));
  const totalPendentes = dadosObras.reduce((s, o) => s + o.pendentes.length, 0);

  const html = `<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Monitor NFS-e — INVCP</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; }
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
           background: #f4f6f9; margin: 0; padding: 1.5rem; color: #1a1a2e; }
    .header { display: flex; align-items: center; gap: 1rem;
              background: #1F4E79; color: white;
              padding: 1rem 1.5rem; border-radius: 10px; margin-bottom: 1.5rem; }
    .header h1 { margin: 0; font-size: 1.3rem; }
    .header .sub { opacity: .75; font-size: .85rem; margin-top: .2rem; }
    .total-badge { margin-left: auto; background: #C0392B; color: white;
                   padding: .3rem .9rem; border-radius: 20px; font-weight: 600; }
    .total-badge.ok { background: #27AE60; }
    .obra { background: white; border-radius: 10px; margin-bottom: 1.2rem;
            box-shadow: 0 1px 4px rgba(0,0,0,.08); overflow: hidden; }
    .obra-header { display: flex; align-items: center; gap: .8rem;
                   padding: .9rem 1.2rem; border-bottom: 1px solid #eee; }
    .obra-header h2 { margin: 0; font-size: 1rem; flex: 1; }
    .badge { padding: .25rem .75rem; border-radius: 12px; font-size: .78rem; font-weight: 600; }
    .badge.pendente { background: #fde8e8; color: #7B2C2C; }
    .badge.ok       { background: #e8f5e9; color: #1B5E20; }
    .meta { font-size: .75rem; color: #888; padding: .4rem 1.2rem;
            border-bottom: 1px solid #f0f0f0; background: #fafafa; }
    table { width: 100%; border-collapse: collapse; }
    th { background: #7B2C2C; color: white; padding: .6rem .9rem;
         text-align: left; font-size: .82rem; }
    td { padding: .55rem .9rem; font-size: .85rem; border-bottom: 1px solid #f5f5f5; }
    tr:last-child td { border-bottom: none; }
    tr:nth-child(even) td { background: #fdf5f5; }
    .valor { text-align: right; font-variant-numeric: tabular-nums; }
    .num   { font-family: monospace; }
    .empty { padding: 1rem 1.2rem; color: #27AE60; font-size: .9rem; }
    .footer { text-align: center; font-size: .75rem; color: #aaa; margin-top: 1rem; }
  </style>
</head>
<body>
<div class="header">
  <div>
    <h1>📋 Monitor NFS-e — INVCP</h1>
    <div class="sub">Notas emitidas no SEFAZ não lançadas no Sienge</div>
  </div>
  <div class="total-badge ${totalPendentes > 0 ? '' : 'ok'}">
    ${totalPendentes > 0 ? `⚠ ${totalPendentes} pendente(s)` : '✓ Tudo lançado'}
  </div>
</div>
${dadosObras.map(renderObra).join('\n')}
<div class="footer">
  Monitor NFS-e · Atualizado a cada hora via GitHub Actions · Dados: SEFAZ ADN Nacional
</div>
</body></html>`;

  return new Response(html, { headers: { 'Content-Type': 'text/html;charset=UTF-8' } });
}

function renderObra(o) {
  const tem    = o.pendentes.length > 0;
  const linhas = o.pendentes.map(n => {
    const v    = parseFloat(String(n.valor || '0').replace(',', '.'));
    const vFmt = isNaN(v) ? n.valor || '—' : v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });
    return `<tr>
      <td>${n.data_emissao || '—'}</td>
      <td class="num">${n.numero || '—'}</td>
      <td>${esc(n.nome_prest || '—')}</td>
      <td class="valor">${vFmt}</td>
    </tr>`;
  }).join('');

  return `<div class="obra">
  <div class="obra-header">
    <h2>${esc(o.nome)}</h2>
    <span class="badge ${tem ? 'pendente' : 'ok'}">${tem ? `⚠ ${o.pendentes.length} pendente(s)` : '✓ Em dia'}</span>
  </div>
  <div class="meta">Última verificação: ${o.ultima_verificacao} &nbsp;|&nbsp; NSU: ${o.ultimo_nsu}</div>
  ${tem
    ? `<table>
    <tr><th>Data Emissão</th><th>Nº NFS-e</th><th>Prestador</th><th style="text-align:right">Valor</th></tr>
    ${linhas}
  </table>`
    : `<div class="empty">✓ Todas as notas estão lançadas no Sienge.</div>`}
</div>`;
}

async function carregarObra(obra, env) {
  try {
    // Verificar cache primeiro
    const cacheKey = `obra_${obra.key}`;
    let cached = getCached(cacheKey);
    if (cached) return cached;

    const [pendentes, lancadas, nsu, verif, pendentesNfe, lancadasNfe] = await Promise.all([
      env.KV.get(`${obra.key}:pendentes`, 'json'),
      env.KV.get(`${obra.key}:lancadas`, 'json'),
      env.KV.get(`${obra.key}:ultimo_nsu`, 'text'),
      env.KV.get(`${obra.key}:ultima_verificacao`, 'text'),
      env.KV.get(`${obra.key}:pendentes_nfe`, 'json'),
      env.KV.get(`${obra.key}:lancadas_nfe`, 'json'),
    ]);

    // Garante tipo='nfse' nas notas de serviço e tipo='nfe' nas de material
    const pend    = (pendentes    || []).map(n => n.tipo ? n : { ...n, tipo: 'nfse' });
    const lanc    = (lancadas     || []).map(n => n.tipo ? n : { ...n, tipo: 'nfse' });
    const pendNfe = (pendentesNfe || []).map(n => ({ ...n, tipo: 'nfe' }));
    const lancNfe = (lancadasNfe  || []).map(n => ({ ...n, tipo: 'nfe' }));

    // Verifica quais PDFs existem (usa cache ou KV uma única vez)
    const marcarPdfs = async (notas) => {
      const cacheKey = 'pdfs_existentes';
      let pdfChaves = getCached(cacheKey);

      if (!pdfChaves) {
        // Se não estiver em cache, listar todos os PDFs do KV (leitura única)
        const listaPdfs = await env.KV.list({ prefix: 'pdf:' });
        pdfChaves = new Set(listaPdfs.keys.map(k => k.name.replace('pdf:', '')));
        setCached(cacheKey, pdfChaves);
      }

      return notas.map(n => ({ ...n, has_pdf: pdfChaves.has(n.chave) }));
    };

    // Marca PDFs em cada lista
    const pendComPdf = await marcarPdfs([...pend, ...pendNfe]);
    const lancComPdf = await marcarPdfs([...lanc, ...lancNfe]);

    // Separa NFS-e e NF-e mantendo as listas de pendentes e lancadas separadas
    const pendentes_nfse = pendComPdf.filter(n => n.tipo === 'nfse');
    const pendentes_nfe  = pendComPdf.filter(n => n.tipo === 'nfe');
    const lancadas_nfse  = lancComPdf.filter(n => n.tipo === 'nfse');
    const lancadas_nfe   = lancComPdf.filter(n => n.tipo === 'nfe');

    const resultado = {
      key: obra.key, nome: obra.nome, regiao: obra.regiao || '',
      pendentes:     pendComPdf,
      lancadas:      lancComPdf,
      pendentes_nfe: pendentes_nfe,
      lancadas_nfe:  lancadas_nfe,
      ultimo_nsu: nsu || '0',
      ultima_verificacao: verif || '—',
    };

    // Cachear resultado por 1 hora
    setCached(cacheKey, resultado);

    return resultado;
  } catch (e) {
    console.error(`Erro ao carregar obra ${obra.key}:`, e);
    return {
      key: obra.key, nome: obra.nome, regiao: obra.regiao || '',
      pendentes: [], lancadas: [], pendentes_nfe: [], lancadas_nfe: [],
      ultimo_nsu: '0', ultima_verificacao: '—',
      erro: e.message,
    };
  }
}

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}
