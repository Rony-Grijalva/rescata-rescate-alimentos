const { chromium } = require('playwright');
const B = process.env.BASE_URL || 'http://localhost:8123', PW = process.env.DEMO_PASSWORD || 'Rescata#2026';
const S = process.env.SHOTS || '/tmp/shots';
const out = []; const ok = (c, m) => { out.push((c ? 'PASS ' : 'FAIL ') + m); if (!c) process.exitCode = 1; };
(async () => {
  const br = await chromium.launch();
  const errs = [];
  async function ctx(w = 1366, h = 820) { const c = await br.newContext({ viewport: { width: w, height: h }, deviceScaleFactor: 1 }); const p = await c.newPage();
    p.on('pageerror', e => errs.push('pageerror ' + e.message)); p.on('console', m => { if (m.type() === 'error' && !/401|403|409|422|Failed to load resource/.test(m.text())) errs.push('console ' + m.text()); }); return [c, p]; }
  const login = async (p, email, pw = PW) => { await p.goto(B); await p.fill('#lg-email', email); await p.fill('#lg-pass', pw); await p.click('.lg-go'); };
  // login screen
  let [c, p] = await ctx(); await p.goto(B); await p.waitForSelector('.lg-card');
  ok(await p.locator('.lg-hero img').isVisible(), 'login: ilustración visible');
  ok(!(await p.locator('#nav a').count()), 'login: sin menú antes de autenticar');
  await p.waitForTimeout(700); await p.screenshot({ path: S + '/01_login.png' });
  // URL tampering sin sesion
  await p.goto(B + '/#/usuarios'); await p.waitForSelector('.lg-card'); ok(true, 'sin sesión: #/usuarios muestra login');
  const r = await p.evaluate(() => fetch('/api/crud/donantes', { headers: { 'X-Rol': 'admin' } }).then(r => r.status)); ok(r === 401, 'API sin sesión con X-Rol falso => 401 (' + r + ')');
  // clave incorrecta
  await login(p, 'coordinador@rescata.pe', 'mala'); await p.waitForSelector('.lg-msg.err'); const t = await p.textContent('.lg-msg.err'); ok(/incorrectos/.test(t), 'clave incorrecta: ' + t);
  await p.waitForTimeout(300); await p.screenshot({ path: S + '/02_login_error.png' });
  // cuentas demo
  const cuentas = await p.evaluate(() => fetch('/api/auth/demo').then(r => r.json()).then(j => j.data.cuentas));
  const pick = (rol) => cuentas.filter(x => x.rol === rol)[0].email;
  const roles = { admin: 'coordinador@rescata.pe', auditor: 'auditor@rescata.pe', donante: pick('donante'), organizacion: pick('organizacion') };
  await c.close();
  const MENUS = {};
  for (const [rol, email] of Object.entries(roles)) {
    [c, p] = await ctx(); await login(p, email); await p.waitForSelector('#nav a'); await p.waitForSelector('.kpi');
    const nav = await p.$$eval('#nav a', a => a.map(x => x.textContent.trim())); MENUS[rol] = nav;
    ok(nav.length > 0, `${rol}: menú (${nav.join(' | ')})`);
    ok(await p.locator('.banner img').isVisible(), `${rol}: banner ilustrado`);
    await p.waitForTimeout(500); await p.screenshot({ path: `${S}/10_${rol}_panel.png` });
    // recorrer todos los módulos
    for (const a of await p.$$('#nav a')) { const h = await a.getAttribute('href'); await a.click(); await p.waitForTimeout(450);
      const bad = await p.locator('#view .empty:has-text("Error")').count(); ok(!bad, `${rol} ${h} carga`); }
    // URL tampering: módulo ajeno
    const ajeno = rol === 'admin' ? 'xx' : 'usuarios'; await p.goto(B + '/#/' + ajeno); await p.waitForTimeout(600);
    ok(/#\/panel/.test(p.url()), `${rol}: #/${ajeno} => devuelto al panel`);
    if (rol !== 'admin') {
      ok((await p.evaluate(() => fetch('/api/usuarios').then(r => r.status))) === 403, `${rol}: GET /api/usuarios => 403`);
      ok((await p.evaluate(() => fetch('/api/sistema/reiniciar', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' }).then(r => r.status))) === 403, `${rol}: reiniciar => 403`);
      ok(await p.locator('#btn-reset.hide').count() === 1, `${rol}: botón reiniciar oculto`);
    }
    if (rol === 'donante') { ok((await p.evaluate(() => fetch('/api/crud/organizaciones').then(r => r.status))) === 403, 'donante: CRUD organizaciones 403'); await p.goto(B + '/#/solicitudes'); await p.waitForTimeout(500); ok(/#\/panel/.test(p.url()), 'donante: #/solicitudes bloqueado'); await p.screenshot({ path: S + '/11_denegado.png' }); }
    // logout
    await p.click('#user'); await p.screenshot({ path: `${S}/12_${rol}_menu.png` }); await p.click('.umenu .out'); await p.waitForSelector('.lg-card');
    ok(/Sesión cerrada/.test(await p.textContent('.lg-msg')), `${rol}: logout`);
    ok((await p.evaluate(() => fetch('/api/me').then(r => r.status))) === 401, `${rol}: tras logout /api/me 401`);
    await p.goBack().catch(() => {}); await p.waitForTimeout(400); ok(await p.locator('.lg-card').count() === 1 || await p.locator('#nav a').count() === 0, `${rol}: atrás no recupera la sesión`);
    await c.close();
  }
  // admin: usuarios + cambio de clave + persistencia
  [c, p] = await ctx(); await login(p, roles.admin); await p.waitForSelector('.kpi');
  await p.goto(B + '/#/usuarios'); await p.waitForSelector('table'); await p.screenshot({ path: S + '/20_usuarios.png' });
  const filas0 = await p.locator('tbody tr').count();
  await p.click('text=Nueva cuenta'); await p.waitForSelector('.modal');
  await p.selectOption('select[name=rol]', 'auditor'); await p.fill('input[name=nombre]', 'Auditora Prueba'); await p.fill('input[name=email]', 'prueba@rescata.pe'); await p.fill('input[name=password]', 'Clave2026x');
  await p.screenshot({ path: S + '/21_nueva_cuenta.png' }); await p.click('.modal .btn:has-text("Crear cuenta")'); await p.waitForTimeout(700);
  ok(await p.locator('tbody tr').count() === filas0 + 1, 'admin: cuenta creada aparece en la tabla');
  // validación: correo duplicado
  await p.click('text=Nueva cuenta'); await p.selectOption('select[name=rol]', 'auditor'); await p.fill('input[name=nombre]', 'Dup'); await p.fill('input[name=email]', 'prueba@rescata.pe'); await p.fill('input[name=password]', 'Clave2026x'); await p.click('.modal .btn:has-text("Crear cuenta")'); await p.waitForTimeout(500);
  ok(await p.locator('.modal .err:has-text("registrado")').count() >= 1, 'admin: correo duplicado rechazado en el formulario'); await p.keyboard.press('Escape');
  // nueva cuenta inicia sesión
  const [c2, p2] = await ctx(); await login(p2, 'prueba@rescata.pe', 'Clave2026x'); await p2.waitForSelector('.kpi'); ok(true, 'cuenta nueva inicia sesión'); 
  // cambio de clave
  await p2.click('#user'); await p2.click('.umenu button:has-text("Cambiar")'); await p2.waitForSelector('.modal');
  const inputs = p2.locator('.modal input[type=password]'); await inputs.nth(0).fill('Clave2026x'); await inputs.nth(1).fill('Nueva2026y'); await inputs.nth(2).fill('otra'); await p2.click('.modal .btn:has-text("Actualizar")'); await p2.waitForTimeout(400);
  ok(await p2.locator('.modal .err:has-text("coincide")').count() >= 1, 'cambio de clave: no coincide');
  await inputs.nth(2).fill('Nueva2026y'); await p2.click('.modal .btn:has-text("Actualizar")'); await p2.waitForTimeout(600); ok(await p2.locator('.modal').count() === 0, 'cambio de clave OK');
  await c2.close();
  const [c3, p3] = await ctx(); await login(p3, 'prueba@rescata.pe', 'Clave2026x'); await p3.waitForSelector('.lg-msg.err'); ok(true, 'clave vieja ya no sirve'); await login(p3, 'prueba@rescata.pe', 'Nueva2026y'); await p3.waitForSelector('.kpi'); ok(true, 'clave nueva sirve'); await c3.close();
  // bloqueo
  const [c4, p4] = await ctx(); for (let i = 0; i < 5; i++) { await login(p4, 'prueba@rescata.pe', 'x' + i); await p4.waitForSelector('.lg-msg.err'); }
  await login(p4, 'prueba@rescata.pe', 'Nueva2026y'); await p4.waitForSelector('.lg-msg.err'); const bl = await p4.textContent('.lg-msg.err'); ok(/bloquead|intent/i.test(bl), 'bloqueo tras 5 fallos: ' + bl); await p4.screenshot({ path: S + '/22_bloqueo.png' }); await c4.close();
  await p.reload(); await p.waitForSelector('table'); await p.waitForTimeout(500);
  ok(await p.locator('tbody tr:has-text("Bloqueada")').count() === 1, 'admin ve la cuenta bloqueada'); 
  await p.click('tbody tr:has-text("Bloqueada") button[title="Desbloquear cuenta"]'); await p.waitForTimeout(600); ok(await p.locator('tbody tr:has-text("Bloqueada")').count() === 0, 'admin desbloquea');
  await c.close();
  // responsive
  for (const [n, w, h] of [['tablet', 820, 1100], ['movil', 390, 800]]) { const [cc, pp] = await ctx(w, h); await pp.goto(B); await pp.waitForSelector('.lg-card'); await pp.waitForTimeout(700); await pp.screenshot({ path: `${S}/30_login_${n}.png`, fullPage: true });
    await login(pp, roles.organizacion); await pp.waitForSelector('.kpi'); await pp.waitForTimeout(500); await pp.screenshot({ path: `${S}/31_org_${n}.png` });
    const ov = await pp.evaluate(() => document.documentElement.scrollWidth > innerWidth + 2); ok(!ov, `${n}: sin scroll horizontal`); await cc.close(); }
  ok(errs.length === 0, 'sin errores JS: ' + errs.slice(0, 4).join(' || '));
  console.log(out.join('\n')); await br.close();
})().catch(e => { console.log(out.join('\n')); console.error(e); process.exit(1); });
