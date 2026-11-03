/* YAASAP Géostratégie — accès abonnés (déchiffrement local, WebCrypto) */
(function () {
  var P = window.YA_PREFIX || './', LS = 'yaasap_k';
  var enc = new TextEncoder(), dec = new TextDecoder();
  var root = document.documentElement;

  function b64d(s) { var b = atob(s), u = new Uint8Array(b.length); for (var i = 0; i < b.length; i++) u[i] = b.charCodeAt(i); return u; }
  function b64e(u) { var s = ''; for (var i = 0; i < u.length; i++) s += String.fromCharCode(u[i]); return btoa(s); }
  function hex(buf) { return [].map.call(new Uint8Array(buf), function (x) { return ('0' + x.toString(16)).slice(-2); }).join(''); }
  function getK() { try { return localStorage.getItem(LS); } catch (e) { return null; } }
  function setK(k) { try { localStorage.setItem(LS, k); } catch (e) {} }
  function clearK() { try { localStorage.removeItem(LS); } catch (e) {} }

  async function aesDecrypt(keyBytes, data) {
    var key = await crypto.subtle.importKey('raw', keyBytes, 'AES-GCM', false, ['decrypt']);
    return crypto.subtle.decrypt({ name: 'AES-GCM', iv: data.slice(0, 12) }, key, data.slice(12));
  }

  /* e-mail + code -> clé maître (octets) ; lève une erreur si l'accès est inconnu ou le code faux */
  async function unwrap(email, code) {
    var r = await fetch(P + 'access.json?t=' + Date.now(), { cache: 'no-store' });
    var list = await r.json();
    email = email.trim().toLowerCase();
    code = code.replace(/[\s-]/g, '').toUpperCase();
    var h = hex(await crypto.subtle.digest('SHA-256', enc.encode('yaasap|' + email)));
    var ent = list.filter(function (x) { return x.h === h; })[0];
    if (!ent) throw new Error('inconnu');
    var base = await crypto.subtle.importKey('raw', enc.encode(email + '|' + code), 'PBKDF2', false, ['deriveBits']);
    var bits = await crypto.subtle.deriveBits({ name: 'PBKDF2', hash: 'SHA-256', salt: b64d(ent.s), iterations: ent.i || 200000 }, base, 256);
    return new Uint8Array(await aesDecrypt(new Uint8Array(bits), b64d(ent.w)));
  }

  /* affiche l'analyse chiffrée de la page, si elle existe */
  async function openPage(K) {
    var pl = document.getElementById('payload');
    if (!pl) return true;
    var o = JSON.parse(pl.textContent);
    var data = JSON.parse(dec.decode(await aesDecrypt(K, b64d(o.d))));
    document.getElementById('locked-slot').innerHTML = data.inner;
    window.NOTE_CHARTS = data.charts; window.NOTE_TIMELINES = data.timelines; window.NOTE_MAPS = data.maps || [];
    var g = document.getElementById('gate'); if (g) g.style.display = 'none';
    pl.remove();
    if (window.yaInit) window.yaInit();
    return true;
  }

  function setSub(on) { root.classList.toggle('sub', !!on); }

  /* déverrouillage automatique si une clé est déjà enregistrée sur cet appareil */
  (async function auto() {
    var k = getK();
    if (!k) return;
    try { await openPage(b64d(k)); setSub(true); }
    catch (e) { clearK(); setSub(false); }
  })();

  var form = document.getElementById('loginForm');
  if (form) {
    var msg = document.getElementById('lgMsg'), ok = document.getElementById('lgOk');
    if (ok && getK()) { form.style.display = 'none'; ok.style.display = 'block'; }
    form.addEventListener('submit', async function (ev) {
      ev.preventDefault();
      msg.className = 'login-msg'; msg.textContent = 'Vérification…';
      try {
        var K = await unwrap(document.getElementById('lgEmail').value, document.getElementById('lgCode').value);
        await openPage(K);
        setK(b64e(K)); setSub(true);
        if (ok) { form.style.display = 'none'; ok.style.display = 'block'; }
        msg.textContent = '';
      } catch (e) {
        msg.className = 'login-msg err';
        msg.textContent = (window.crypto && crypto.subtle) ? 'E-mail ou code incorrect.' : 'Navigateur non compatible : utilisez une version récente avec HTTPS.';
      }
    });
  }
  var lo = document.getElementById('logout');
  if (lo) lo.addEventListener('click', function (ev) {
    ev.preventDefault(); clearK(); setSub(false);
    var f = document.getElementById('loginForm'), o = document.getElementById('lgOk');
    if (f) f.style.display = ''; if (o) o.style.display = 'none';
  });
})();
