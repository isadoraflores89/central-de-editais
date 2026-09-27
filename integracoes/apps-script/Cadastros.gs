/**
 * Central de Editais — recebe cadastros do site e alimenta o CRM.
 *
 * Instalação (uma vez), na conta Google dona do Firebase "flores-cultura":
 * 1. Crie uma planilha PRIVADA "Central de Editais — Cadastros".
 * 2. Extensões > Apps Script. Cole este arquivo e o appsscript.json.
 * 3. Configurações do projeto > Propriedades do script:
 *      FIREBASE_DB_URL = https://flores-cultura-default-rtdb.firebaseio.com
 * 4. Implantar > Nova implantação > App da Web:
 *      Executar como: Eu | Quem pode acessar: Qualquer pessoa
 * 5. Copie a URL /exec para config/site.yaml (cadastro_endpoint).
 *
 * O que ele faz:
 * - só RECEBE (doPost). Não existe nenhuma rota que devolva dados pessoais;
 * - grava/atualiza a linha da pessoa na aba "Cadastros" (chave = e-mail);
 * - na primeira vez, manda o contato para crm/entrada_central no Firebase,
 *   de onde a intranet importa para o CRM (negócio "Central de Editais").
 */

var ABA = 'Cadastros';
var COLUNAS = [
  'primeiro_cadastro', 'ultimo_acesso', 'nome', 'email', 'whatsapp', 'uf', 'cidade',
  'perfil', 'area', 'consultoria', 'newsletter', 'aceite_privacidade', 'pagina', 'edital',
];
var LIMITES = { nome: 120, email: 160, whatsapp: 30, uf: 2, cidade: 80, perfil: 30, area: 40, pagina: 200, edital: 200 };

function doPost(e) {
  try {
    var d = JSON.parse((e && e.postData && e.postData.contents) || '{}');
    if (d.site) return resposta_({ ok: true }); // armadilha para robôs (campo invisível)

    var c = limpar_(d);
    var erro = validar_(c);
    if (erro) return resposta_({ ok: false, erro: erro });
    if (!dentroDoLimite_(c.email)) return resposta_({ ok: false, erro: 'muitas tentativas, tente em 1 minuto' });

    var lock = LockService.getScriptLock();
    lock.waitLock(10000);
    var novo;
    try { novo = gravar_(c); } finally { lock.releaseLock(); }

    if (novo) enviarAoCrm_(c);
    return resposta_({ ok: true });
  } catch (err) {
    console.error(err);
    return resposta_({ ok: false, erro: 'falha ao registrar' });
  }
}

function limpar_(d) {
  var c = {};
  Object.keys(LIMITES).forEach(function (k) {
    c[k] = String(d[k] == null ? '' : d[k]).replace(/[\u0000-\u001f<>]/g, '').trim().slice(0, LIMITES[k]);
  });
  c.email = c.email.toLowerCase();
  c.uf = c.uf.toUpperCase();
  c.consultoria = d.consultoria === true;
  c.newsletter = d.newsletter === true;
  c.aceite = d.aceite === true;
  // Impede fórmulas na planilha (=, +, -, @ no início).
  Object.keys(c).forEach(function (k) {
    if (typeof c[k] === 'string' && /^[=+\-@]/.test(c[k])) c[k] = "'" + c[k];
  });
  return c;
}

function validar_(c) {
  if (!c.aceite) return 'é preciso aceitar a política de privacidade';
  if (c.nome.length < 2) return 'nome inválido';
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(c.email)) return 'e-mail inválido';
  if (!/^[A-Z]{2}$/.test(c.uf)) return 'estado inválido';
  return null;
}

function dentroDoLimite_(email) {
  var cache = CacheService.getScriptCache();
  var chave = 'rl:' + Utilities.base64EncodeWebSafe(email).slice(0, 200);
  var n = Number(cache.get(chave) || 0);
  if (n >= 5) return false;
  cache.put(chave, String(n + 1), 60);
  return true;
}

function aba_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(ABA) || ss.insertSheet(ABA);
  if (sh.getLastRow() === 0) {
    sh.appendRow(COLUNAS);
    sh.setFrozenRows(1);
  }
  return sh;
}

/** Devolve true se o e-mail é novo. */
function gravar_(c) {
  var sh = aba_();
  var agora = new Date();
  var linha = [
    agora, agora, c.nome, c.email, c.whatsapp, c.uf, c.cidade, c.perfil, c.area,
    c.consultoria ? 'sim' : 'não', c.newsletter ? 'sim' : 'não', 'sim', c.pagina, c.edital,
  ];
  var n = sh.getLastRow();
  if (n > 1) {
    var emails = sh.getRange(2, 4, n - 1, 1).getValues();
    for (var i = 0; i < emails.length; i++) {
      if (String(emails[i][0]).toLowerCase() === c.email) {
        linha[0] = sh.getRange(i + 2, 1).getValue(); // mantém a data do primeiro cadastro
        sh.getRange(i + 2, 1, 1, linha.length).setValues([linha]);
        return false;
      }
    }
  }
  sh.appendRow(linha);
  return true;
}

function enviarAoCrm_(c) {
  var url = PropertiesService.getScriptProperties().getProperty('FIREBASE_DB_URL');
  if (!url) return;
  var notas = [
    'Cadastro na Central de Editais',
    'UF: ' + c.uf + (c.cidade ? ' (' + c.cidade + ')' : ''),
    c.perfil ? 'Perfil: ' + c.perfil : '',
    c.area ? 'Área: ' + c.area : '',
    'Quer consultoria: ' + (c.consultoria ? 'sim' : 'não'),
    'Newsletter: ' + (c.newsletter ? 'sim' : 'não'),
    c.edital ? 'Edital que abriu: ' + c.edital : '',
  ].filter(String).join(' · ');
  var contato = {
    nome: c.nome, email: c.email, whatsapp: c.whatsapp, cidade: c.cidade ? c.cidade + '/' + c.uf : c.uf,
    negocio: 'central', status: 'novo', origem: 'site', notas: notas,
    consultoria: c.consultoria, criado: new Date().toISOString(),
  };
  var r = UrlFetchApp.fetch(firebaseUrl_(url, '/crm/entrada_central.json'), {
    method: 'post',
    contentType: 'application/json',
    payload: JSON.stringify(contato),
    muteHttpExceptions: true,
  });
  if (r.getResponseCode() !== 200) console.error('Firebase ' + r.getResponseCode() + ': ' + r.getContentText());
}

/** Endereço REST do Firebase com o token OAuth de quem implantou o script. */
function firebaseUrl_(base, caminho, extra) {
  var q = 'access_token=' + encodeURIComponent(ScriptApp.getOAuthToken()) + (extra ? '&' + extra : '');
  return base.replace(/\/+$/, '') + caminho + '?' + q;
}

function resposta_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

/** Rode uma vez pelo editor para autorizar e testar o acesso ao Firebase (não cria contato). */
function testarConexao() {
  var url = PropertiesService.getScriptProperties().getProperty('FIREBASE_DB_URL');
  if (!url) throw new Error('Falta a propriedade FIREBASE_DB_URL');
  var r = UrlFetchApp.fetch(firebaseUrl_(url, '/crm/entrada_central.json', 'shallow=true'), {
    muteHttpExceptions: true,
  });
  Logger.log('Firebase respondeu ' + r.getResponseCode() + (r.getResponseCode() === 200 ? ' (ok)' : ': ' + r.getContentText()));
}
