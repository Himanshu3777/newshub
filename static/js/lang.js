/* NewsHub language switcher: English / Hindi (Google Translate) / Hinglish.
   Hindi and English run through Google Translate (googtrans cookie + reload).
   Google offers no "Hinglish", so Hinglish mode transliterates every
   Devanagari text on the page into Roman script right here in the browser -
   same Hindi words, just readable without knowing the Devanagari script. */
(function () {
  "use strict";
  var KEY = "nw_lang";
  function getPref() { try { return localStorage.getItem(KEY) || ""; } catch (e) { return ""; } }
  function setPref(v) { try { localStorage.setItem(KEY, v); } catch (e) {} }
  function setTransCookie(v) {
    var d = new Date(); d.setFullYear(d.getFullYear() + 1);
    var exp = ";path=/;expires=" + d.toUTCString();
    document.cookie = "googtrans=" + v + exp;
    document.cookie = "googtrans=" + v + exp + ";domain=" + location.hostname;
  }
  function clearTransCookie() {
    var p = ";path=/;expires=Thu, 01 Jan 1970 00:00:00 GMT";
    document.cookie = "googtrans=" + p;
    document.cookie = "googtrans=" + p + ";domain=" + location.hostname;
    document.cookie = "googtrans=" + p + ";domain=." + location.hostname;
  }

  /* ---------- Devanagari -> Roman (Hinglish) ---------- */
  var VOW = {"अ":"a","आ":"aa","इ":"i","ई":"ee","उ":"u","ऊ":"oo","ऋ":"ri","ए":"e","ऐ":"ai","ओ":"o","औ":"au","ऑ":"o","ऍ":"e"};
  var MAT = {"ा":"aa","ि":"i","ी":"ee","ु":"u","ू":"oo","ृ":"ri","े":"e","ै":"ai","ो":"o","ौ":"au","ॉ":"o","ॅ":"e"};
  var CON = {"क":"k","ख":"kh","ग":"g","घ":"gh","ङ":"ng","च":"ch","छ":"chh","ज":"j","झ":"jh","ञ":"ny","ट":"t","ठ":"th","ड":"d","ढ":"dh","ण":"n","त":"t","थ":"th","द":"d","ध":"dh","न":"n","प":"p","फ":"ph","ब":"b","भ":"bh","म":"m","य":"y","र":"r","ल":"l","व":"v","श":"sh","ष":"sh","स":"s","ह":"h"};
  var NUK = {"क":"q","ख":"kh","ग":"gh","ज":"z","ड":"r","ढ":"rh","फ":"f"};
  var DIG = {"०":"0","१":"1","२":"2","३":"3","४":"4","५":"5","६":"6","७":"7","८":"8","९":"9"};
  var HALANT = "्", NUKTA = "़";
  var DEV = /[ऀ-ॿ]/;
  function conv(text) {
    if (!DEV.test(text)) return text;
    var out = "", i = 0, n = text.length;
    while (i < n) {
      var ch = text[i];
      if (Object.prototype.hasOwnProperty.call(CON, ch)) {
        var stem = CON[ch], j = i + 1;
        if (j < n && text[j] === NUKTA) { if (NUK[ch]) stem = NUK[ch]; j++; }
        if (j < n && text[j] === HALANT) { out += stem; i = j + 1; continue; }
        if (j < n && Object.prototype.hasOwnProperty.call(MAT, text[j])) { out += stem + MAT[text[j]]; i = j + 1; continue; }
        out += stem + "a"; i = j; continue;
      }
      if (Object.prototype.hasOwnProperty.call(VOW, ch)) { out += VOW[ch]; i++; continue; }
      if (ch === "ं" || ch === "ँ") { out += "n"; i++; continue; }
      if (ch === "ः") { out += "h"; i++; continue; }
      if (Object.prototype.hasOwnProperty.call(DIG, ch)) { out += DIG[ch]; i++; continue; }
      if (ch === HALANT || ch === NUKTA) { i++; continue; }
      out += ch; i++;
    }
    return out;
  }
  var SKIP = { SCRIPT: 1, STYLE: 1, NOSCRIPT: 1, CODE: 1, TEXTAREA: 1, IFRAME: 1 };
  function convertNode(root) {
    if (!root) return;
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (node) {
        var p = node.parentElement;
        if (!p || SKIP[p.tagName]) return NodeFilter.FILTER_REJECT;
        if (p.closest("#google_translate_element,.notranslate,.lang-switch,script,style")) return NodeFilter.FILTER_REJECT;
        return DEV.test(node.nodeValue) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    var nodes = [], nd;
    while ((nd = walker.nextNode())) nodes.push(nd);
    nodes.forEach(function (t) { t.nodeValue = conv(t.nodeValue); });
  }
  var converting = false;
  function startObserver() {
    var mo = new MutationObserver(function (muts) {
      if (converting) return; converting = true;
      muts.forEach(function (m) {
        m.addedNodes.forEach(function (an) {
          if (an.nodeType === 1) convertNode(an);
          else if (an.nodeType === 3) { var v = conv(an.nodeValue); if (v !== an.nodeValue) an.nodeValue = v; }
        });
      });
      converting = false;
    });
    mo.observe(document.body, { childList: true, subtree: true });
  }

  /* ---------- Switcher wiring ---------- */
  function markActive(lang) {
    document.querySelectorAll(".lang-btn").forEach(function (b) {
      b.classList.toggle("active", b.getAttribute("data-lang") === lang);
    });
  }
  function choose(lang) {
    setPref(lang);
    if (lang === "hi") setTransCookie("/auto/hi");
    else if (lang === "en") setTransCookie("/auto/en");
    else clearTransCookie();
    location.reload();
  }
  document.addEventListener("DOMContentLoaded", function () {
    document.querySelectorAll(".lang-btn").forEach(function (b) {
      b.addEventListener("click", function () { choose(b.getAttribute("data-lang")); });
    });
    var lang = getPref();
    if (!lang) {
      lang = (document.cookie.indexOf("/hi") >= 0 && document.cookie.indexOf("googtrans") >= 0) ? "hi" : "en";
    }
    markActive(lang);
    if (lang === "hinglish") {
      convertNode(document.body);
      document.querySelectorAll("[placeholder]").forEach(function (el) {
        el.setAttribute("placeholder", conv(el.getAttribute("placeholder")));
      });
      startObserver();
    }
  });
})();
