#!/usr/bin/env python3
"""Patch fresh, pinned Read Aloud and TWP checkouts. Experimental only."""
import json
from pathlib import Path
import sys

RA_ID = 'read-aloud-traduire-ecouter@dreadaxe'
TWP_ID = 'twp-traduire-ecouter@dreadaxe'


def once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f'{label}: expected one anchor, found {count}')
    return text.replace(old, new, 1)


def twice(text, old, new, label):
    count = text.count(old)
    if count != 2:
        raise RuntimeError(f'{label}: expected two anchors, found {count}')
    return text.replace(old, new)


def patch(ra, twp):
    edits = {}

    ra_manifest_path = ra / 'manifest.json'
    ra_manifest = json.loads(ra_manifest_path.read_text(encoding='utf-8'))
    if ra_manifest['browser_specific_settings']['gecko']['id'] != '{ddc62400-f22d-4dd3-8b4a-05837de53c2e}':
        raise RuntimeError('Unexpected upstream Read Aloud ID')
    ra_manifest['browser_specific_settings']['gecko']['id'] = RA_ID
    ra_manifest['name'] = '🧪 TEST Dreadaxe — Read Aloud'
    edits[ra_manifest_path] = json.dumps(ra_manifest, indent=2, ensure_ascii=False) + '\n'

    twp_manifest_path = twp / 'src/manifest.json'
    twp_manifest = json.loads(twp_manifest_path.read_text(encoding='utf-8'))
    if twp_manifest['browser_specific_settings']['gecko']['id'] != '{036a55b4-5e72-4d05-a06c-cba2dfcc134a}':
        raise RuntimeError('Unexpected upstream TWP ID')
    twp_manifest['browser_specific_settings']['gecko']['id'] = TWP_ID
    twp_manifest['name'] = '🧪 TEST Dreadaxe — TWP'
    edits[twp_manifest_path] = json.dumps(twp_manifest, indent=2, ensure_ascii=False) + '\n'

    popup_path = ra / 'popup.html'
    popup = popup_path.read_text(encoding='utf-8')
    popup = once(popup, '  <div id="highlight">',
        '  <button id="btnTranslateRead" type="button" style="display:block;margin:8px auto;padding:10px 14px">🌐 Traduire et écouter</button>\n'
        '  <div id="highlight">', 'Read Aloud button')
    edits[popup_path] = popup

    popup_js_path = ra / 'js/popup.js'
    popup_js = popup_js_path.read_text(encoding='utf-8')
    popup_js = once(popup_js, '  $("#btnPlay").click(onPlay);',
        '  $("#btnPlay").click(onPlay);\n  $("#btnTranslateRead").click(onTranslateRead);', 'Read Aloud click')
    popup_js += '''
// Experimental Read Aloud > TWP > Read Aloud bridge.
let translateReadBusy = false;
async function onTranslateRead() {
  if (translateReadBusy) return;
  translateReadBusy = true;
  const button = $("#btnTranslateRead");
  button.prop("disabled", true).text("Traduction de la page en cours…");
  try {
    const tab = await getActiveTab();
    if (!tab || !Number.isInteger(tab.id)) throw new Error("Aucun onglet Firefox actif");
    await bgPageInvoke("stop");
    const response = await brapi.runtime.sendMessage("''' + TWP_ID + '''", {
      action: "readAloudTranslateAndWait", tabId: tab.id
    });
    if (!response || !response.ok)
      throw new Error(response?.error || "TWP expérimental ne répond pas");
    button.text("Lecture en français…");
    await bgPageInvoke("playTab", [tab.id]);
    await updateButtons();
  } catch (error) {
    handleError(error);
  } finally {
    translateReadBusy = false;
    button.prop("disabled", false).text("🌐 Traduire et écouter");
  }
}
'''
    edits[popup_js_path] = popup_js

    bg_path = twp / 'src/background/background.js'
    bg = bg_path.read_text(encoding='utf-8')
    bg += '''
// Accept only the dedicated experimental Read Aloud add-on.
chrome.runtime.onMessageExternal.addListener((request, sender, sendResponse) => {
  if (sender.id !== "''' + RA_ID + '''" || request?.action !== "readAloudTranslateAndWait") return;
  if (!Number.isInteger(request.tabId) || request.tabId < 0) {
    sendResponse({ok: false, error: "Invalid tab ID"});
    return;
  }
  chrome.tabs.sendMessage(request.tabId,
    {action: "readAloudTranslateAndWait", targetLanguage: "fr"},
    {frameId: 0},
    response => {
      const error = chrome.runtime.lastError;
      sendResponse(error ? {ok: false, error: error.message} :
        (response || {ok: false, error: "TWP unavailable on this tab"}));
    });
  return true;
});
'''
    edits[bg_path] = bg

    page_path = twp / 'src/contentScript/pageTranslator.js'
    page = page_path.read_text(encoding='utf-8')
    page = once(page, '  let pageLanguageState = "original";', '''  let pageLanguageState = "original";
  // Whole-document translation is enabled only during a Read Aloud request.
  let readAloudWholePage = false;
  let readAloudPendingRequests = 0;
  let readAloudPendingSegments = 0;
  let readAloudBridgeError = null;
  let readAloudBusy = false;''', 'TWP state')
    page = once(page,
        '                bottomIsInScreen(ptt.topElement) ||\n                topIsInScreen(ptt.bottomElement)',
        '                (readAloudWholePage && piecesToTranslateNow.length < 12) ||\n'
        '                bottomIsInScreen(ptt.topElement) ||\n                topIsInScreen(ptt.bottomElement)', 'TWP offscreen text')
    page = once(page,
        '              if (isInScreen(ati.node)) {',
        '              if ((readAloudWholePage && attributesToTranslateNow.length < 12) || isInScreen(ati.node)) {',
        'TWP offscreen attributes')
    page = once(page,
        '          if (piecesToTranslateNow.length > 0) {\n            backgroundTranslateHTML(',
        '          if (piecesToTranslateNow.length > 0) {\n            readAloudPendingRequests++;\n            backgroundTranslateHTML(',
        'TWP text request counter')
    page = once(page,
        '                translateResults(piecesToTranslateNow, results);\n              }\n            });',
        '''                translateResults(piecesToTranslateNow, results);
              }
            }).catch(err => {
              console.error(err);
              if (readAloudWholePage) readAloudBridgeError = String(err?.message || err);
            }).finally(() => { readAloudPendingRequests--; });''',
        'TWP text request settlement')
    page = once(page,
        '          if (attributesToTranslateNow.length > 0) {\n            backgroundTranslateText(',
        '          if (attributesToTranslateNow.length > 0) {\n            readAloudPendingRequests++;\n            backgroundTranslateText(',
        'TWP attr request counter')
    page = once(page,
        '                translateAttributes(attributesToTranslateNow, results);\n              }\n            });',
        '''                translateAttributes(attributesToTranslateNow, results);
              }
            }).catch(err => {
              console.error(err);
              if (readAloudWholePage) readAloudBridgeError = String(err?.message || err);
            }).finally(() => { readAloudPendingRequests--; });''',
        'TWP attr request settlement')
    # Two translation-result loops perform asynchronous custom-dictionary substitutions.
    page = twice(page, '            handleCustomWords(\n',
        '            readAloudPendingSegments++;\n            handleCustomWords(\n',
        'TWP dictionary processing start')
    page = twice(page,
        '              translateTextContent(nodes[j], parentNode, results, toRestore);\n            });',
        '''              translateTextContent(nodes[j], parentNode, results, toRestore);
            }).catch(err => {
              console.error(err);
              if (readAloudWholePage) readAloudBridgeError = String(err?.message || err);
            }).finally(() => { readAloudPendingSegments--; });''',
        'TWP dictionary processing end')
    bridge = '''
  // Explicit acknowledgement only when every known paragraph has been translated.
  async function readAloudTranslateAndWait(targetLanguage) {
    if (readAloudBusy) return {ok: false, error: "Traduction déjà en cours"};
    readAloudBusy = true;
    readAloudBridgeError = null;
    readAloudWholePage = true;
    try {
      const sourceLanguage = await new Promise(resolve =>
        pageTranslator.onGetOriginalTabLanguage(resolve));
      if (sourceLanguage === "fr" || sourceLanguage?.startsWith("fr-"))
        return {ok: true, skipped: true};
      pageTranslator.translatePage(targetLanguage || "fr");
      const deadline = Date.now() + 180000;
      let stableSince = null;
      while (Date.now() < deadline) {
        if (readAloudBridgeError) throw new Error(readAloudBridgeError);
        if (document.visibilityState === "hidden")
          throw new Error("La page a été masquée pendant la traduction");
        const queued = piecesToTranslate.some(x => !x.isTranslated) ||
                       attributesToTranslate.some(x => !x.isTranslated);
        if (!queued && readAloudPendingRequests === 0 && readAloudPendingSegments === 0) {
          if (stableSince === null) stableSince = Date.now();
          if (Date.now() - stableSince > 1000)
            return {ok: true, targetLanguage: currentTargetLanguage};
        } else stableSince = null;
        await new Promise(resolve => setTimeout(resolve, 250));
      }
      throw new Error("Délai dépassé lors de la traduction intégrale");
    } catch (error) {
      return {ok: false, error: String(error?.message || error)};
    } finally {
      readAloudWholePage = false;
      readAloudBusy = false;
    }
  }

'''
    page = once(page,
        '  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {\n    if (request.action === "translatePage") {',
        bridge + '  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {\n'
        '    if (request.action === "readAloudTranslateAndWait") {\n'
        '      readAloudTranslateAndWait(request.targetLanguage)\n'
        '        .then(sendResponse, error => sendResponse({ok: false, error: String(error)}));\n'
        '      return true;\n'
        '    }\n'
        '    if (request.action === "translatePage") {',
        'TWP content message handler')
    edits[page_path] = page


    # Reader selection: TWP handles translation; user selects the playback engine.
    ra_events_path = ra / 'js/events.js'
    ra_events = ra_events_path.read_text(encoding='utf-8')
    ra_events += '''
// Experimental bridge: let the paired TWP add-on play its already-translated tab.
brapi.runtime.onMessageExternal.addListener((request, sender) => {
  if (sender.id !== "''' + TWP_ID + '''" || request?.action !== "dreadaxePlayTranslatedTab") return;
  if (!Number.isInteger(request.tabId) || request.tabId < 0)
    return Promise.resolve({ok: false, error: "Onglet invalide"});
  return getActiveTab().then(tab => {
    if (!tab || tab.id !== request.tabId) throw new Error("L'onglet actif a changé");
    return playTab(tab.id);
  }).then(() => ({ok: true}), error => ({ok: false, error: String(error?.message || error)}));
});
'''
    edits[ra_events_path] = ra_events

    twp_mobile_html_path = twp / 'src/contentScript/html/popupMobile.html'
    mobile_html = twp_mobile_html_path.read_text(encoding='utf-8')
    mobile_html = once(mobile_html,
        '            <div data-value="more-options">',
        '''            <div data-value="dreadaxe-listen-twp"><span>🔊 Lire la page avec TWP</span></div>
            <div data-value="dreadaxe-listen-readaloud"><span>🎙 Lire avec Read Aloud (autres voix)</span></div>
            <div data-value="dreadaxe-stop-twp"><span>⏹ Arrêter la lecture TWP</span></div>
            <div data-value="more-options">''', 'TWP menu position')
    edits[twp_mobile_html_path] = mobile_html

    twp_mobile_js_path = twp / 'src/contentScript/popupMobile.js'
    mobile_js = twp_mobile_js_path.read_text(encoding='utf-8')
    mobile_helpers = '''
  // Experimental reader choice, preserving the page and active tab.
  function dreadaxeGetArticleText() {
    const root = document.querySelector("article, [role='main'], main") || document.body;
    if (!root) return "";
    const copy = root.cloneNode(true);
    copy.querySelectorAll(
      "script, style, nav, footer, header, aside, form, button, " +
      "iframe, noscript, [hidden], [aria-hidden='true'], .notranslate"
    ).forEach(node => node.remove());
    const selector = "h1,h2,h3,h4,p,li,pre,blockquote,figcaption";
    const nodes = [...copy.querySelectorAll(selector)].filter(
      node => !node.parentElement?.closest(selector)
    );
    const lines = nodes.map(node => (node.textContent || "").replace(/\\\\s+/g, " ").trim())
      .filter(Boolean);
    return (lines.length ? lines.join("\\\\n\\\\n") : copy.textContent || "").trim();
  }

  function dreadaxeSendCommand(action, extra = {}) {
    return new Promise((resolve, reject) => {
      chrome.runtime.sendMessage({action, ...extra}, response => {
        const error = chrome.runtime.lastError;
        if (error) return reject(new Error(error.message));
        if (!response?.ok) return reject(new Error(response?.error || "Commande sans réponse"));
        resolve(response);
      });
    });
  }

  async function dreadaxeReadPage(backend) {
    lastInteraction = Date.now();
    const label = shadowRoot.getElementById("question");
    label.textContent = "Préparation de la page…";
    try {
      const status = await pageTranslator.prepareForReading("fr");
      if (!status?.ok) throw new Error(status?.error || "Traduction incomplète");
      if (backend === "twp") {
        const text = dreadaxeGetArticleText();
        if (text.length < 10) throw new Error("Aucun texte lisible dans cette page");
        if (text.length > 200000) throw new Error("Page trop longue pour ce prototype");
        await dreadaxeSendCommand("dreadaxeReadWholePage", {text, targetLanguage: "fr"});
      } else {
        await dreadaxeSendCommand("dreadaxePlayWithReadAloud");
      }
      label.textContent = backend === "twp" ? "Lecture TWP lancée" : "Lecture Read Aloud lancée";
      setTimeout(updateInterface, 2800);
    } catch (error) {
      console.error("Traduire et écouter", error);
      label.textContent = "Échec de lecture : " + (error?.message || String(error));
      showPopup();
    }
  }

'''
    mobile_js = once(mobile_js, '  // menu options\\n', mobile_helpers + '  // menu options\\n', 'TWP mobile code insertion')
    mobile_js = once(mobile_js,
        '    if (action === "choose-another-language") {',
        '''    if (action === "dreadaxe-listen-twp" || action === "dreadaxe-listen-readaloud") {
      closeMenu();
      void dreadaxeReadPage(action === "dreadaxe-listen-twp" ? "twp" : "readaloud");
      return;
    } else if (action === "dreadaxe-stop-twp") {
      chrome.runtime.sendMessage({action: "stopAudio"}, checkedLastError);
      closeMenu();
      return;
    } else if (action === "choose-another-language") {''',
        'TWP listener integration')
    edits[twp_mobile_js_path] = mobile_js

    # Share the already-implemented full-document translation synchronization.
    page = edits[page_path]
    page = once(page,
        '  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {',
        '  pageTranslator.prepareForReading = readAloudTranslateAndWait;\\n'
        '  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {',
        'TWP expose page preparation')
    edits[page_path] = page

    # TWP audio pipeline already handles short text. Stream full pages in modest
    # batches rather than prefetching hundreds of speech segments at once.
    twp_tts_path = twp / 'src/background/textToSpeech.js'
    tts = twp_tts_path.read_text(encoding='utf-8')
    tts += '''
// Experimental long-article playback. Pause/resume and Android media
// notifications remain future work; stopAudio cancels future batches.
let dreadaxeSpeechGeneration = 0;
function dreadaxeSplitSpeech(text) {
  const chunks = [];
  let part = "";
  for (const word of text.split(/\\\\s+/).filter(Boolean)) {
    if (part && part.length + word.length + 1 > 1100) {
      chunks.push(part);
      part = "";
    }
    if (word.length > 1100) {
      if (part) { chunks.push(part); part = ""; }
      for (let i = 0; i < word.length; i += 1100) chunks.push(word.slice(i, i + 1100));
    } else {
      part += (part ? " " : "") + word;
    }
  }
  if (part) chunks.push(part);
  return chunks;
}
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request?.action === "dreadaxeReadWholePage") {
    const text = typeof request.text === "string" ? request.text.trim() : "";
    if (!sender.tab || text.length < 10 || text.length > 200000) {
      sendResponse({ok: false, error: "Texte invalide ou page trop longue"});
      return;
    }
    const generation = ++dreadaxeSpeechGeneration;
    googleService.stopAll();
    bingService.stopAll();
    const service = twpConfig.get("textToSpeechService") === "bing" ? bingService : googleService;
    (async () => {
      for (const chunk of dreadaxeSplitSpeech(text)) {
        if (generation !== dreadaxeSpeechGeneration) break;
        await service.textToSpeech(chunk, request.targetLanguage || "fr");
      }
    })().catch(error => console.error("Dreadaxe lecture complète", error));
    sendResponse({ok: true});
  } else if (request?.action === "stopAudio") {
    dreadaxeSpeechGeneration++;
  }
});
'''
    edits[twp_tts_path] = tts

    # The content script asks TWP background to contact the dedicated reader.
    bg = edits[bg_path]
    bg += '''
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request?.action !== "dreadaxePlayWithReadAloud") return;
  if (!sender.tab || !Number.isInteger(sender.tab.id)) {
    sendResponse({ok: false, error: "Onglet source inconnu"});
    return;
  }
  chrome.runtime.sendMessage("''' + RA_ID + '''",
    {action: "dreadaxePlayTranslatedTab", tabId: sender.tab.id},
    response => {
      const error = chrome.runtime.lastError;
      sendResponse(error ? {ok: false, error: error.message} :
        (response || {ok: false, error: "Read Aloud expérimental indisponible"}));
    });
  return true;
});
'''
    edits[bg_path] = bg

    for path, content in edits.items():
        path.write_text(content, encoding='utf-8')
        print('patched', path)
    print('Code patch applied. Builds are experimental and unsigned.')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit('usage: python patch_extensions.py READ_ALOUD_CHECKOUT TWP_CHECKOUT')
    patch(Path(sys.argv[1]), Path(sys.argv[2]))
