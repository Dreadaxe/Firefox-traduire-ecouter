'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {JSDOM} = require('jsdom');

function getBetween(filepath, begin, end) {
  const code = fs.readFileSync(filepath, 'utf8');
  const start = code.indexOf(begin);
  assert.notEqual(start, -1, 'Code de départ absent : ' + begin);
  const finish = end == null ? code.length : code.indexOf(end, start + begin.length);
  assert.notEqual(finish, -1, 'Fin de fonction absente : ' + end);
  return code.slice(start, finish);
}

const MOBILE = 'sources/twp/src/contentScript/popupMobile.js';
const TTS = 'sources/twp/src/background/textToSpeech.js';
const TWP_BG = 'sources/twp/src/background/background.js';
const RA_BG = 'sources/read-aloud/js/events.js';

function extract(html) {
  const {window} = new JSDOM(html);
  const block = getBetween(MOBILE, '  function dreadaxeGetArticleText() {', '\n\n  function dreadaxeSendCommand');
  const result = vm.runInNewContext(block + '\ndreadaxeGetArticleText();', {document:window.document});
  window.close();
  return result;
}

function chunk(text) {
  const block = getBetween(TTS, 'function dreadaxeSplitSpeech(text) {', '\nchrome.runtime.onMessage.addListener');
  return [...vm.runInNewContext(block + '\ndreadaxeSplitSpeech(TEXT);', {TEXT:text})];
}

test('Récupérer article et non pas menus et boutons', () => {
  const article = extract(`
    <nav>NE PAS LIRE CETTE NAVIGATION</nav>
    <main><header>NE PAS LIRE CET EN-TETE</header>
      <article><h1>Premier titre</h1><p>Premier paragraphe de texte.</p>
        <ul><li>Deuxième élément</li><li><p>Troisième élément</p></li></ul>
        <aside>NE PAS LIRE CETTE PUBLICITE</aside>
        <p>Dernier paragraphe de texte.</p>
      </article>
    </main>
    <footer>NE PAS LIRE CE PIED DE PAGE</footer>
  `);
  assert.match(article, /Premier titre/);
  assert.match(article, /Dernier paragraphe de texte/);
  assert.ok(article.indexOf('Premier paragraphe') < article.indexOf('Deuxième élément'));
  assert.ok(article.indexOf('Deuxième élément') < article.indexOf('Troisième élément'));
  assert.ok(article.indexOf('Troisième élément') < article.indexOf('Dernier paragraphe'));
  assert.equal((article.match(/Troisième élément/g) || []).length, 1);
  assert.doesNotMatch(article, /NE PAS LIRE/);
});

test('Lecture d’une très longue page sans omission ni inversion', () => {
  const paragraphs = Array.from({length:600}, (_,i)=>'Paragraphe numéro '+i+' : '+('texte '+i+' ').repeat(25));
  const html = '<main><article>'+paragraphs.map(s=>'<p>'+s+'</p>').join('')+'</article></main>';
  const article = extract(html);
  assert.ok(article.length > 100000);
  let prev = -1;
  paragraphs.forEach((p) => {
    const pos = article.indexOf(p.trim());
    assert.ok(pos > prev, 'Paragraphe absent ou déplacé : '+p.slice(0,35));
    prev = pos;
  });
  const chunks = chunk(article);
  assert.ok(chunks.length > 100, 'les segments ne sont pas suffisamment découpés');
  assert.ok(chunks.every(t=>t.length <= 1100), 'taille de segment > 1100');
  assert.equal(chunks.join(' ').replace(/\s+/g,' ').trim(),article.replace(/\s+/g,' ').trim());
});

test('Écarter les textes trop longs et accepter les paragraphes normaux', () => {
  assert.deepEqual(chunk(''), []);
  assert.deepEqual(chunk(' bonjour tout le monde '), ['bonjour tout le monde']);
  const big = 'un '.repeat(1000);
  const parts = chunk(big);
  assert.ok(parts.length > 1);
  assert.ok(parts.every(p=>p.length <= 1100));
  assert.equal(parts.join(' '),big.trim().replace(/\s+/g,' '));
});

test('Ne transmettre à Read Aloud que l’onglet actif et la bonne extension', async () => {
  const block = getBetween(RA_BG, '// Experimental bridge: let the paired TWP add-on', null);
  let handler, selectedId=18, plays=[];
  const sandbox = {
    brapi:{runtime:{onMessageExternal:{addListener: fn=>{handler=fn}}}},
    getActiveTab:async()=>({id:selectedId}),
    playTab:async id=>{plays.push(id)},
    Promise
  };
  vm.runInNewContext(block,sandbox);
  assert.equal(handler({action:'dreadaxePlayTranslatedTab',tabId:18},{id:'autre-extension'}), undefined);
  const res=await handler({action:'dreadaxePlayTranslatedTab',tabId:18},{id:'twp-traduire-ecouter@dreadaxe'});
  assert.equal(res.ok,true);
  assert.deepEqual(plays,[18]);
  selectedId=19;
  const bad=await handler({action:'dreadaxePlayTranslatedTab',tabId:18},{id:'twp-traduire-ecouter@dreadaxe'});
  assert.equal(bad.ok,false);
  assert.deepEqual(plays,[18]);
});

test('TWP transmet l’onglet d’origine sans changer d’onglet', async () => {
  const block = getBetween(TWP_BG, 'chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {\n  if (request?.action !== "dreadaxePlayWithReadAloud")', null);
  let handler, sent;
  const runtime = {
    lastError:null,
    onMessage:{addListener:fn=>{handler=fn}},
    sendMessage:(extension,message,callback)=>{
      sent={extension,message}; callback({ok:true});
    }
  };
  vm.runInNewContext(block,{chrome:{runtime}});
  const answer=await new Promise(resolve=>handler({action:'dreadaxePlayWithReadAloud'},{tab:{id:42}},resolve));
  assert.equal(answer.ok,true);
  assert.equal(sent.extension,'read-aloud-traduire-ecouter@dreadaxe');
  assert.equal(sent.message.tabId,42);
  const invalid=await new Promise(resolve=>handler({action:'dreadaxePlayWithReadAloud'},{},resolve));
  assert.equal(invalid.ok,false);
});

test('Contrôles lecture/pause/reprise/arrêt et MediaSession optionnelle', async () => {
  const block = getBetween(TTS, '// Experimental long-article playback.', '  // Listen for messages coming from contentScript or other scripts.');
  let listener, mediaHandlers={}, sent=[], paused=0, resumed=0, stopped=0;
  let releaseAudio=()=>{};
  const googleService={
    stopAll(){stopped++},
    pauseCurrent(){paused++},
    resumeCurrent(){resumed++},
    textToSpeech(text){
      sent.push(text);
      return new Promise(resolve=>{releaseAudio=resolve});
    }
  };
  const bingService={
    stopAll(){},
    pauseCurrent(){},
    resumeCurrent(){},
    textToSpeech: async ()=>{}
  };
  const chrome={runtime:{onMessage:{addListener:fn=>{listener=fn}}}};
  vm.runInNewContext(block,{
    chrome, googleService,bingService,console,Promise,
    navigator:{mediaSession:{setActionHandler:(name,fn)=>{mediaHandlers[name]=fn}}},
    twpConfig:{get:()=> 'google'}
  });
  assert.deepEqual(Object.keys(mediaHandlers).sort(),['pause','play','stop']);
  const longText=('Longue phrase de test et encore un mot. ').repeat(130);
  let reply=null;
  listener({action:'dreadaxeReadWholePage',text:longText,targetLanguage:'fr'},
    {tab:{id:5}},res=>{reply=res});
  assert.equal(reply.ok,true);
  assert.equal(sent.length,1,'premier lot seulement');
  mediaHandlers.pause();
  assert.equal(paused,1);
  mediaHandlers.play();
  assert.equal(resumed,1);
  let stoppedResponse;
  listener({action:'dreadaxeStopWholePage'},{tab:{id:5}},res=>{stoppedResponse=res});
  assert.equal(stoppedResponse.ok,true);
  assert.ok(stopped >= 3);
  releaseAudio();
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(sent.length,1,'un arrêt ne doit pas lancer les lots suivants');
});

test('Menu mobile : sélection explicite de deux lecteurs et contrôles',()=>{
  const html=fs.readFileSync('sources/twp/src/contentScript/html/popupMobile.html','utf8');
  for (const key of ['dreadaxe-listen-twp','dreadaxe-listen-readaloud','dreadaxe-pause-twp','dreadaxe-resume-twp','dreadaxe-stop-twp']) {
    assert.ok(html.includes('data-value="'+key+'"'), 'Commande absente du menu : '+key);
  }
});
