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

    for path, content in edits.items():
        path.write_text(content, encoding='utf-8')
        print('patched', path)
    print('Code patch applied. Builds are experimental and unsigned.')


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit('usage: python patch_extensions.py READ_ALOUD_CHECKOUT TWP_CHECKOUT')
    patch(Path(sys.argv[1]), Path(sys.argv[2]))
