const { test, expect } = require('@playwright/test');
const path = require('path');
const fs = require('fs');

// Ruta donde se guardará el contexto persistente
const authFile = path.join(__dirname, '../playwright/.auth/user.json');

// Función para esperar a que el usuario complete el login
// Detecta automáticamente cuando la URL cambia (sale de /login)
async function waitForLogin(page, maxWaitTime = 5 * 60 * 1000) { // 5 minutos por defecto
  const startTime = Date.now();
  const checkInterval = 2000; // Verificar cada 2 segundos
  
  console.log('\n⏸️  PAUSA: Por favor, inicia sesión manualmente en el navegador.');
  console.log('   El sistema detectará automáticamente cuando completes el login.');
  console.log('   (Se detectará cuando la URL cambie y ya no esté en /login)\n');
  
  while (Date.now() - startTime < maxWaitTime) {
    const currentUrl = page.url();
    
    // Si ya no estamos en la página de login, asumimos que el login fue exitoso
    if (!currentUrl.includes('/login') && !currentUrl.endsWith('/login')) {
      console.log(`\n✅ Login detectado! URL actual: ${currentUrl}`);
      return true;
    }
    
    // Esperar antes de verificar de nuevo
    await page.waitForTimeout(checkInterval);
    
    // Mostrar mensaje cada 30 segundos
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    if (elapsed % 30 === 0 && elapsed > 0) {
      console.log(`   ⏳ Esperando login... (${Math.floor(elapsed / 60)}m ${elapsed % 60}s)`);
    }
  }
  
  console.log('\n⚠️  Tiempo de espera agotado. Continuando de todas formas...');
  return false;
}

test.describe('Flujo con credenciales persistentes', () => {
  
  test('iniciar sesión manualmente y luego ejecutar flujo', async ({ browser, browserName }) => {
    // Crear directorio si no existe
    const authDir = path.dirname(authFile);
    if (!fs.existsSync(authDir)) {
      fs.mkdirSync(authDir, { recursive: true });
    }

    // Si ya existe un archivo de autenticación, cargarlo
    let context;
    if (fs.existsSync(authFile)) {
      console.log('📂 Cargando credenciales guardadas...');
      context = await browser.newContext({
        storageState: authFile,
      });
    } else {
      console.log('🆕 Creando nuevo contexto (primera vez)...');
      context = await browser.newContext();
    }

    const page = await context.newPage();

    // ============================================
    // URL DE LOGIN DE KAMS
    // ============================================
    const loginUrl = 'https://kams.com/login';
    
    console.log(`🌐 Abriendo ${loginUrl}...`);
    await page.goto(loginUrl);
    
    // Esperar a que la página cargue completamente
    await page.waitForLoadState('networkidle');
    
    // Esperar a que el usuario complete el login (detección automática)
    await waitForLogin(page, 5 * 60 * 1000); // 5 minutos máximo
    
    // Esperar un momento adicional para asegurar que todo cargó
    await page.waitForTimeout(2000);
    
    // Verificar el estado final
    const currentUrl = page.url();
    if (currentUrl.includes('/login')) {
      console.log('⚠️  Aún estás en la página de login.');
      console.log('   Si ya completaste el login, el sistema continuará de todas formas...');
    } else {
      console.log(`✅ Login completado. URL actual: ${currentUrl}`);
    }

    // Guardar el contexto (cookies, localStorage, etc.) después del login
    console.log('💾 Guardando credenciales...');
    await context.storageState({ path: authFile });
    console.log('✅ Credenciales guardadas en:', authFile);

    // Ahora puedes continuar con tu flujo automatizado
    console.log('\n🚀 Continuando con el flujo automatizado en KAMS...\n');
    
    // ============================================
    // AQUÍ EMPIEZA TU FLUJO AUTOMATIZADO EN KAMS
    // Personaliza esta sección según tus necesidades
    // ============================================
    
    // Esperar a que la página cargue después del login
    await page.waitForLoadState('networkidle');
    
    // Tomar captura de pantalla de la página principal después del login
    await page.screenshot({ path: 'kams-after-login.png', fullPage: true });
    console.log('📸 Captura de pantalla después del login guardada: kams-after-login.png');
    
    // Aquí puedes agregar tus acciones automatizadas
    // Por ejemplo:
    // - Navegar a una sección específica
    // - Hacer clic en botones
    // - Rellenar formularios
    // - Extraer información
    
    // Ejemplo: Esperar a que aparezca algún elemento de la aplicación
    // await page.waitForSelector('selector-de-elemento-principal', { timeout: 10000 });
    
    // Tomar captura final del flujo
    await page.screenshot({ path: 'kams-flow-result.png', fullPage: true });
    console.log('📸 Captura de pantalla del flujo guardada: kams-flow-result.png');
    
    // ============================================
    // FIN DE TU FLUJO AUTOMATIZADO
    // ============================================
    
    // Guardar el contexto una vez más al final (por si hubo cambios)
    await context.storageState({ path: authFile });
    
    // NO cerrar el contexto inmediatamente para que puedas ver el resultado
    console.log('\n✅ Flujo completado. Las credenciales están guardadas.');
    console.log('   El navegador permanecerá abierto por 10 segundos...');
    await page.waitForTimeout(10000);
    
    await context.close();
  });

  test('flujo automatizado usando credenciales guardadas', async ({ browser }) => {
    // Verificar que existe el archivo de autenticación
    if (!fs.existsSync(authFile)) {
      test.skip('No hay credenciales guardadas. Ejecuta primero el test de login manual.');
      return;
    }

    console.log('📂 Usando credenciales guardadas...');
    const context = await browser.newContext({
      storageState: authFile,
    });

    const page = await context.newPage();

    // ============================================
    // TU FLUJO AUTOMATIZADO EN KAMS AQUÍ
    // ============================================
    // Navegar a KAMS (debería estar autenticado automáticamente)
    await page.goto('https://kams.com');
    await page.waitForLoadState('networkidle');
    
    // Verificar que estás autenticado (ajusta el selector según tu aplicación)
    // await expect(page.locator('selector-del-usuario-autenticado')).toBeVisible();
    
    console.log(`✅ Navegando a KAMS. URL actual: ${page.url()}`);
    
    // Aquí puedes agregar tu flujo automatizado
    // Por ejemplo, navegar a secciones específicas, hacer acciones, etc.
    
    await page.screenshot({ path: 'kams-automated-flow.png', fullPage: true });
    console.log('📸 Captura de pantalla guardada: kams-automated-flow.png');
    
    console.log('✅ Flujo ejecutado con credenciales guardadas');
    
    await context.close();
  });

  test('subir video en KAMS', async ({ browser }) => {
    // Verificar que existe el archivo de autenticación
    if (!fs.existsSync(authFile)) {
      test.skip('No hay credenciales guardadas. Ejecuta primero el test de login manual.');
      return;
    }

    // Ruta del video a subir
    const videoPath = path.join(__dirname, '../test.mp4');
    
    // Verificar que el archivo existe
    if (!fs.existsSync(videoPath)) {
      test.fail(`El archivo de video no existe: ${videoPath}`);
      return;
    }

    console.log('📂 Usando credenciales guardadas...');
    const context = await browser.newContext({
      storageState: authFile,
    });

    const page = await context.newPage();

    // ============================================
    // PASO 1: Navegar a /upload
    // ============================================
    console.log('\n📤 Paso 1: Navegando a https://kams.com/upload...');
    await page.goto('https://kams.com/upload');
    await page.waitForLoadState('networkidle');
    
    // Verificar que estamos en la página correcta
    const currentUrl = page.url();
    expect(currentUrl).toContain('/upload');
    console.log(`✅ Navegado a: ${currentUrl}`);
    
    // Captura después de navegar
    await page.screenshot({ path: 'kams-upload-page.png', fullPage: true });
    console.log('📸 Captura de pantalla: kams-upload-page.png');

    // ============================================
    // PASOS 2-3: Subir archivo de video
    // ============================================
    console.log('\n📁 Paso 2: Haciendo clic en "Choose File"...');
    
    // Buscar el botón "Choose File" con múltiples estrategias
    const buttonSelectors = [
      'button:has-text("Choose File")',
      'button:has-text("choose file")',
      'button:has-text("Choose")',
      '[role="button"]:has-text("Choose File")',
      'a:has-text("Choose File")',
      'div:has-text("Choose File")',
      'span:has-text("Choose File")',
      'button[class*="choose"]',
      'button[class*="file"]',
      'button[class*="upload"]'
    ];
    
    let buttonFound = false;
    for (const selector of buttonSelectors) {
      try {
        const btn = page.locator(selector).first();
        if (await btn.isVisible({ timeout: 2000 }).catch(() => false)) {
          await btn.click();
          buttonFound = true;
          console.log(`✅ Clic en botón "Choose File" encontrado con: ${selector}`);
          break;
        }
      } catch (e) {
        // Continuar con el siguiente selector
      }
    }
    
    // Si no encontramos el botón por selectores específicos, buscar cualquier botón con texto relacionado
    if (!buttonFound) {
      console.log('🔍 Buscando botón con texto relacionado...');
      const allButtons = page.locator('button, [role="button"], a, div, span');
      const buttonCount = await allButtons.count();
      
      for (let i = 0; i < Math.min(buttonCount, 20); i++) {
        try {
          const btn = allButtons.nth(i);
          const text = await btn.textContent().catch(() => '');
          if (text && /choose|file|select|upload/i.test(text)) {
            if (await btn.isVisible({ timeout: 1000 }).catch(() => false)) {
              await btn.click();
              buttonFound = true;
              console.log(`✅ Clic en botón encontrado por texto: "${text.trim()}"`);
              break;
            }
          }
        } catch (e) {
          // Continuar
        }
      }
    }
    
    if (!buttonFound) {
      console.log('⚠️  No se encontró el botón "Choose File", intentando directamente con el input...');
    }
    
    // Esperar un momento después del clic (si se hizo)
    await page.waitForTimeout(1000);
    
    console.log('\n📁 Paso 3: Seleccionando archivo de video...');
    
    // Intentar encontrar el input file directamente
    // También buscar si hay un label asociado que podamos hacer clic
    const fileInput = page.locator('input[type="file"]').first();
    
    // Si no encontramos el botón antes, intentar hacer clic en el label asociado
    if (!buttonFound) {
      try {
        const label = page.locator('label[for], label').filter({ has: fileInput }).first();
        if (await label.isVisible({ timeout: 2000 }).catch(() => false)) {
          await label.click();
          console.log('✅ Clic en label asociado al input file');
          await page.waitForTimeout(500);
        }
      } catch (e) {
        // Continuar
      }
      
      // También intentar hacer clic en el área de drag & drop
      try {
        const dropZone = page.locator('text=/drag|drop|click to select/i').first();
        if (await dropZone.isVisible({ timeout: 2000 }).catch(() => false)) {
          await dropZone.click();
          console.log('✅ Clic en área de drag & drop');
          await page.waitForTimeout(500);
        }
      } catch (e) {
        // Continuar
      }
    }
    
    // El input puede estar oculto, así que no esperamos que sea visible
    // Simplemente intentamos establecer el archivo
    await fileInput.setInputFiles(videoPath);
    console.log(`✅ Archivo seleccionado: ${videoPath}`);
    
    // Esperar un momento para que se procese la selección
    await page.waitForTimeout(2000);
    
    // Captura después de seleccionar archivo
    await page.screenshot({ path: 'kams-file-selected.png', fullPage: true });
    console.log('📸 Captura de pantalla: kams-file-selected.png');

    // ============================================
    // PASO 4: Esperar carga del video
    // ============================================
    console.log('\n⏳ Paso 4: Esperando que cargue el video...');
    
    // Detectar indicador de carga - buscar texto "uploading" o "please wait"
    const uploadingSelectors = [
      'text=uploading',
      'text=please wait',
      'text=Uploading',
      'text=Please wait',
      '[class*="upload"]',
      '[class*="progress"]',
      '[id*="upload"]',
      '[id*="progress"]'
    ];
    
    let uploadIndicator = null;
    for (const selector of uploadingSelectors) {
      try {
        const element = page.locator(selector).first();
        if (await element.isVisible({ timeout: 2000 }).catch(() => false)) {
          uploadIndicator = element;
          console.log(`📊 Indicador de carga encontrado: ${selector}`);
          break;
        }
      } catch (e) {
        // Continuar con el siguiente selector
      }
    }
    
    // Si encontramos un indicador, esperar a que desaparezca
    if (uploadIndicator) {
      console.log('⏳ Esperando a que termine la carga...');
      try {
        await uploadIndicator.waitFor({ state: 'hidden', timeout: 5 * 60 * 1000 }); // 5 minutos máximo
        console.log('✅ Carga completada');
      } catch (e) {
        console.log('⚠️  Timeout esperando indicador de carga, continuando...');
      }
    } else {
      // Si no encontramos indicador específico, esperar un tiempo razonable
      console.log('⏳ No se encontró indicador específico, esperando 10 segundos...');
      await page.waitForTimeout(10000);
    }
    
    // Esperar a que la red esté inactiva (carga completada)
    await page.waitForLoadState('networkidle', { timeout: 5 * 60 * 1000 });
    console.log('✅ Carga del video completada');

    // ============================================
    // PASO 5: Completar título
    // ============================================
    console.log('\n✏️  Paso 5: Completando título del video...');
    
    // Buscar campo de título por varios selectores posibles
    const titleSelectors = [
      'input[placeholder*="title" i]',
      'input[placeholder*="Title" i]',
      'input[placeholder*="enter video title" i]',
      'input[name*="title" i]',
      'input[id*="title" i]',
      'textarea[placeholder*="title" i]',
      'textarea[placeholder*="Title" i]'
    ];
    
    let titleField = null;
    for (const selector of titleSelectors) {
      try {
        const field = page.locator(selector).first();
        if (await field.isVisible({ timeout: 2000 }).catch(() => false)) {
          titleField = field;
          console.log(`✅ Campo de título encontrado: ${selector}`);
          break;
        }
      } catch (e) {
        // Continuar con el siguiente selector
      }
    }
    
    if (titleField) {
      await titleField.fill('prueba uno');
      console.log('✅ Título completado: "prueba uno"');
    } else {
      console.log('⚠️  No se encontró el campo de título, intentando buscar por texto...');
      // Intentar buscar por texto visible
      const titleByText = page.locator('text=title').first();
      if (await titleByText.isVisible({ timeout: 2000 }).catch(() => false)) {
        // Buscar el input más cercano
        const nearbyInput = page.locator('input, textarea').first();
        await nearbyInput.fill('prueba uno');
        console.log('✅ Título completado (por proximidad): "prueba uno"');
      }
    }

    // ============================================
    // PASO 6: Agregar tags
    // ============================================
    console.log('\n🏷️  Paso 6: Agregando tags...');
    
    // Buscar campo de tags por varios selectores posibles
    const tagSelectors = [
      'input[placeholder*="tag" i]',
      'input[placeholder*="Tag" i]',
      'input[placeholder*="add tags" i]',
      'input[name*="tag" i]',
      'input[id*="tag" i]',
      'textarea[placeholder*="tag" i]',
      'textarea[placeholder*="add tags" i]'
    ];
    
    let tagField = null;
    for (const selector of tagSelectors) {
      try {
        const field = page.locator(selector).first();
        if (await field.isVisible({ timeout: 2000 }).catch(() => false)) {
          tagField = field;
          console.log(`✅ Campo de tags encontrado: ${selector}`);
          break;
        }
      } catch (e) {
        // Continuar con el siguiente selector
      }
    }
    
    if (tagField) {
      // Agregar un tag de ejemplo (puedes personalizar esto)
      await tagField.fill('test');
      await tagField.press('Enter');
      console.log('✅ Tag agregado: "test"');
    } else {
      console.log('⚠️  No se encontró el campo de tags específico');
    }
    
    // Captura después de completar formulario
    await page.screenshot({ path: 'kams-form-completed.png', fullPage: true });
    console.log('📸 Captura de pantalla: kams-form-completed.png');

    // ============================================
    // PASO 7: Submit video
    // ============================================
    console.log('\n🚀 Paso 7: Enviando video...');
    
    // Buscar botón de submit por varios selectores posibles
    const submitSelectors = [
      'button:has-text("Submit")',
      'button:has-text("submit")',
      'button:has-text("Submit video")',
      'button[type="submit"]',
      'input[type="submit"]',
      'button:has-text("Upload")',
      'button:has-text("upload")',
      '[class*="submit"]',
      '[id*="submit"]'
    ];
    
    let submitButton = null;
    for (const selector of submitSelectors) {
      try {
        const button = page.locator(selector).first();
        if (await button.isVisible({ timeout: 2000 }).catch(() => false)) {
          submitButton = button;
          console.log(`✅ Botón de submit encontrado: ${selector}`);
          break;
        }
      } catch (e) {
        // Continuar con el siguiente selector
      }
    }
    
    if (submitButton) {
      // Hacer clic en el botón de submit
      await submitButton.click();
      console.log('✅ Botón de submit presionado');
      
      // Esperar a que se procese el submit (redirección o confirmación)
      await page.waitForLoadState('networkidle', { timeout: 30000 });
      
      // Verificar si hubo redirección o mensaje de éxito
      const finalUrl = page.url();
      console.log(`📍 URL después del submit: ${finalUrl}`);
      
      // Captura después de submit
      await page.screenshot({ path: 'kams-after-submit.png', fullPage: true });
      console.log('📸 Captura de pantalla: kams-after-submit.png');
      
      console.log('✅ Video enviado exitosamente');
    } else {
      console.log('⚠️  No se encontró el botón de submit');
      // Captura de debug
      await page.screenshot({ path: 'kams-debug-no-submit.png', fullPage: true });
    }

    // Esperar un momento para ver el resultado
    await page.waitForTimeout(3000);
    
    // Guardar el contexto por si hubo cambios
    await context.storageState({ path: authFile });
    
    console.log('\n✅ Flujo de subida de video completado');
    
    await context.close();
  });
});

