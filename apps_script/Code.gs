/**
 * Recebe as fichas enviadas pelo formulário e grava na aba "fichas" desta planilha.
 *
 * Instalação (uma vez, na conta Google da vigilância):
 *  1. Crie uma planilha Google na pasta do Drive onde as respostas devem ficar.
 *  2. Na planilha: Extensões > Apps Script. Apague o conteúdo e cole este arquivo.
 *  3. Configurações do projeto (ícone de engrenagem) > Propriedades do script >
 *     Adicionar propriedade: nome CHAVE, valor = uma senha longa (ex.: 20 letras e números).
 *  4. Implantar > Nova implantação > Tipo: App da Web.
 *     Executar como: Eu. Quem pode acessar: Qualquer pessoa.
 *  5. Autorize e copie a URL que termina em /exec. Ela e a CHAVE vão na aba Unidade
 *     de cada tablet.
 *
 * A mesma ficha (id_registro) enviada de novo, depois de editada, substitui a linha anterior.
 */
const ABA = "fichas";

function doPost(e) {
  let dados;
  try {
    dados = JSON.parse(e.postData.contents);
  } catch (err) {
    return resposta({ ok: false, erro: "conteúdo inválido" });
  }
  const chave = PropertiesService.getScriptProperties().getProperty("CHAVE");
  if (!chave || dados.chave !== chave) return resposta({ ok: false, erro: "chave incorreta" });

  const registros = Array.isArray(dados.registros) ? dados.registros : [];
  if (!registros.length) return resposta({ ok: true, ids: [] });

  const trava = LockService.getScriptLock();
  trava.waitLock(30000);
  try {
    const aba = obterAba();
    const cab = cabecalho(aba, registros);
    const colId = cab.indexOf("id_registro");
    const n = aba.getLastRow() - 1;
    const ids = n > 0 ? aba.getRange(2, colId + 1, n, 1).getValues().map(l => String(l[0])) : [];
    const linhaDe = new Map(ids.map((id, i) => [id, i + 2]));
    const recebidoEm = new Date().toISOString();
    const novas = [];
    for (const r of registros) {
      if (!r.id_registro) continue;
      r.recebido_em = recebidoEm;
      const linha = cab.map(c => (r[c] === undefined || r[c] === null) ? "" : String(r[c]));
      const existente = linhaDe.get(String(r.id_registro));
      if (existente) aba.getRange(existente, 1, 1, cab.length).setNumberFormat("@").setValues([linha]);
      else novas.push(linha);
    }
    if (novas.length) {
      const ini = aba.getLastRow() + 1;
      aba.getRange(ini, 1, novas.length, cab.length).setNumberFormat("@").setValues(novas);
    }
    return resposta({ ok: true, ids: registros.map(r => r.id_registro).filter(Boolean) });
  } finally {
    trava.releaseLock();
  }
}

function doGet() {
  return resposta({ ok: true, servico: "fichas dengue/chikungunya" });
}

function obterAba() {
  const pl = SpreadsheetApp.getActiveSpreadsheet();
  let aba = pl.getSheetByName(ABA);
  if (!aba) {
    aba = pl.insertSheet(ABA);
    // Texto puro: impede o Sheets de converter datas e códigos (ex.: "05" -> 5)
    aba.getRange("A:ZZ").setNumberFormat("@");
  }
  return aba;
}

// Garante que todas as colunas recebidas existam no cabeçalho, sem mudar a ordem das já existentes
function cabecalho(aba, registros) {
  let cab = aba.getLastRow() > 0 ? aba.getRange(1, 1, 1, aba.getLastColumn()).getValues()[0].map(String) : [];
  const faltando = [];
  for (const r of registros) for (const c of Object.keys(r).concat(["recebido_em"])) {
    if (!cab.includes(c) && !faltando.includes(c)) faltando.push(c);
  }
  if (faltando.length) {
    if (aba.getMaxColumns() < cab.length + faltando.length) aba.insertColumnsAfter(aba.getMaxColumns(), cab.length + faltando.length - aba.getMaxColumns());
    aba.getRange(1, cab.length + 1, 1, faltando.length).setNumberFormat("@").setValues([faltando]);
    cab = cab.concat(faltando);
    aba.setFrozenRows(1);
  }
  return cab;
}

function resposta(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}
