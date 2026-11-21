/** Testes das funções puras do importador de ficheiro (leitura CSV e associação de colunas). */
const { test } = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const codigo = fs.readFileSync(path.join(__dirname, '..', 'js', 'importar-ficheiro.js'), 'utf8');
const janela = {};
const contexto = {
  window: janela,
  document: { readyState: 'complete', addEventListener() {}, body: { appendChild() {} }, querySelectorAll: () => [] },
  MutationObserver: class { observe() {} },
  setTimeout, Set, Event: class {},
  HTMLInputElement: { prototype: {} }, HTMLTextAreaElement: { prototype: {} },
};
vm.createContext(contexto);
vm.runInContext(codigo, contexto);
const api = janela.SIGE_IMPORTAR_FICHEIRO;

test('CSV com ponto e vírgula, aspas e BOM', () => {
  const l = api.lerCsv('﻿Nome;Obs\r\n"Silva; João";"diz ""olá"""\r\nAna;x\r\n');
  assert.strictEqual(JSON.stringify(l), JSON.stringify([['Nome', 'Obs'], ['Silva; João', 'diz "olá"'], ['Ana', 'x']]));
});

test('CSV com vírgulas', () => {
  assert.strictEqual(JSON.stringify(api.lerCsv('a,b\n1,2')), '[["a","b"],["1","2"]]');
});

test('normalização ignora acentos e símbolos', () => {
  assert.strictEqual(api.norm('Data de Nascimento *'), 'datadenascimento');
  assert.strictEqual(api.norm('Matrícula'), 'matricula');
});

test('associa colunas aos campos por rótulo', () => {
  const campos = [
    { campo: 'c1', chaves: ['nomecompleto', 'nome'] },
    { campo: 'c2', chaves: ['datadenascimento'] },
  ];
  const m = api.associar(['Nome', 'Data de Nascimento', 'Outra'], campos);
  assert.strictEqual(m.map(x => x.campo).join(','), 'c1,c2');
});
