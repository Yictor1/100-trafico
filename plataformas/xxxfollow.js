const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const userDataDir = path.join(__dirname, 'browser-profile');

async function automateXxxFollow() {
  const browser = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    slowMo: 500,
    viewport: { width: 1920, height: 1080 }
  });
  const pages = browser.pages();
  const page = pages.length > 0 ? pages[0] : await browser.newPage();
  try {
    console.log('🚀 Iniciando automatización de xxxfollow.com...\n');
    // Preparar el video
    const videoPath = path.join(__dirname, 'test2.mp4');
    if (!fs.existsSync(videoPath)) {
      throw new Error(`Video no encontrado: ${videoPath}`);
    }
    const fileSize = fs.statSync(videoPath).size;
    console.log(`📹 Video preparado: ${videoPath}`);
    console.log(`📏 Tamaño: ${(fileSize / 1024 / 1024).toFixed(2)} MB\n`);
    // Paso 1: Navegar a /post
    console.log('📍 Paso 1: Navegando a https://www.xxxfollow.com/post');
    await page.goto('https://www.xxxfollow.com/post', { waitUntil: 'networkidle', timeout: 30000 });
    console.log('✅ Página cargada');
    await page.waitForTimeout(3000);
    // Paso 2: Configurar el interceptor del fileChooser ANTES de hacer click
    console.log('\n📍 Paso 2: Configurando interceptor de archivos...');
    // Esta promesa "escucha" cuando se abre un selector de archivos
    const fileChooserPromise = page.waitForEvent('filechooser', { timeout: 20000 });
    console.log('✅ Interceptor configurado, esperando a que se abra el explorador...');
    // Paso 3: Hacer click en el área de carga para que se abra el explorador
    console.log('\n📍 Paso 3: Buscando el área "tap to choose video"...');
    // Primero intentar con el input directamente (más confiable)
    let clickDone = false;
    try {
      console.log(' - Buscando input[type="file"]...');
      const fileInput = await page.locator('input[type="file"]').first();
      const count = await fileInput.count();
      if (count > 0) {
        console.log(` - Encontrado ${count} input(s) de archivo`);
        console.log(' - Haciendo click en el input (esto abrirá el explorador)...');
        // Click forzado porque el input puede estar oculto
        await fileInput.click({ force: true });
        console.log('✅ Click realizado en input[type="file"]');
        clickDone = true;
      }
    } catch (e) {
      console.log(` ⚠️ No funcionó con input directo: ${e.message}`);
    }
    // Si no funcionó con el input, buscar el área visible
    if (!clickDone) {
      console.log(' - Buscando área visible de drop zone...');
      const dropZoneSelectors = [
        'text=/tap to choose/i',
        'text=/choose video/i',
        'text=/drop.*here/i',
        '[class*="dropzone"]',
        '[class*="upload-area"]',
        '[class*="drop-zone"]',
        'div:has-text("tap to choose")',
        'div:has-text("choose video")'
      ];
      for (const selector of dropZoneSelectors) {
        try {
          console.log(` - Intentando: ${selector}`);
          await page.waitForSelector(selector, { timeout: 3000 });
          await page.click(selector);
          console.log(` ✅ Click realizado en: ${selector}`);
          clickDone = true;
          break;
        } catch (e) { continue; }
      }
    }
    if (!clickDone) {
      throw new Error('No se pudo hacer click en el área de carga. Verifica que estés en /post');
    }
    // Paso 4: Esperar a que se abra el fileChooser (explorador de archivos)
    console.log('\n📍 Paso 4: Esperando a que se abra el explorador de archivos...');
    console.log(' (Si ves el explorador abrirse manualmente, ¡es buena señal!)');
    let fileChooser;
    try {
      fileChooser = await fileChooserPromise;
      console.log('✅ ¡Explorador detectado por Playwright!');
    } catch (e) {
      throw new Error('El explorador de archivos no se abrió. Posibles causas:\n' +
        ' - El click no funcionó\n' +
        ' - Ya estás logueado? (verifica en el navegador)\n' +
        ' - La página cambió su estructura');
    }
    // Paso 5: Cargar el video en el fileChooser (equivalente a seleccionar el archivo)
    console.log('\n📍 Paso 5: Seleccionando video en el explorador...');
    await fileChooser.setFiles(videoPath);
    console.log('✅ Video seleccionado: test_lips.mp4');
    console.log(' (Esto es equivalente a seleccionar el archivo y dar OK)');
    // Paso 6: Esperar a que el video se procese
    console.log('\n📍 Paso 6: Esperando a que el video se procese...');
    await page.waitForTimeout(8000); // Dar tiempo generoso para que se cargue
    // Verificar que el video se cargó
    console.log('\n🔍 Verificando si el video se cargó...');
    const verification = await page.evaluate(() => {
      return {
        hasVideo: !!document.querySelector('video'),
        hasVideoSrc: !!document.querySelector('video[src]'),
        hasPreview: !!document.querySelector('[class*="preview" i]'),
        hasThumbnail: !!document.querySelector('[class*="thumbnail" i]'),
        hasProgress: !!document.querySelector('[class*="progress" i]'),
        hasFileName: document.body.textContent.includes('test_lips') || document.body.textContent.includes('.mp4'),
        videoCount: document.querySelectorAll('video').length,
        allText: document.body.textContent
      };
    });
    console.log('📊 Resultados:');
    console.log(` - Video tag presente: ${verification.hasVideo ? '✅' : '❌'}`);
    console.log(` - Video con src: ${verification.hasVideoSrc ? '✅' : '❌'}`);
    console.log(` - Preview visible: ${verification.hasPreview ? '✅' : '❌'}`);
    console.log(` - Thumbnail visible: ${verification.hasThumbnail ? '✅' : '❌'}`);
    console.log(` - Progress bar: ${verification.hasProgress ? '✅' : '❌'}`);
    console.log(` - Nombre de archivo visible: ${verification.hasFileName ? '✅' : '❌'}`);
    console.log(` - Total videos en página: ${verification.videoCount}`);
    // Screenshot para verificación
    // await page.screenshot({ path: 'verification-screenshot.png', fullPage: true });
    // console.log('📸 Screenshot guardado: verification-screenshot.png');
    // Si no hay señales de que el video se cargó, lanzar error
    if (!verification.hasVideo && !verification.hasPreview && !verification.hasFileName) {
      console.log('\n⚠️ NO HAY INDICADORES DE VIDEO CARGADO');
      console.log('🔍 Texto visible en la página:');
      console.log(verification.allText.substring(0, 500) + '...');
      throw new Error('El video no parece haberse cargado correctamente');
    }
    console.log('\n✅ ¡Video detectado! Continuando...');
    // Paso 7: Buscar botón Continue
    console.log('\n📍 Paso 7: Buscando botón "Continue"...');
    const continueSelectors = [
      'button:has-text("Continue")',
      'button:has-text("Next")',
      'text="Continue"',
      'text="Next"'
    ];
    let continueFound = false;
    for (const selector of continueSelectors) {
      try {
        await page.waitForSelector(selector, { timeout: 5000 });
        await page.click(selector);
        console.log(`✅ Click en "${selector}" realizado`);
        continueFound = true;
        break;
      } catch (e) { continue; }
    }
    if (!continueFound) {
      console.log('⚠️ No se encontró botón Continue/Next');
      console.log(' Puede que el formulario ya esté visible');
    }
    await page.waitForTimeout(3000);
    // Paso 8: Llenar formulario
    console.log('\n📍 Paso 8: Llenando formulario...');
    // Caption
    console.log(' - Buscando campo de caption...');
    const captionSelectors = [
      'textarea[placeholder*="caption" i]',
      'textarea[placeholder*="write" i]',
      'input[placeholder*="caption" i]',
      'textarea'
    ];
    let captionFilled = false;
    for (const selector of captionSelectors) {
      try {
        const field = page.locator(selector).first();
        const isVisible = await field.isVisible({ timeout: 2000 }).catch(() => false);
        if (isVisible) {
          await field.clear();
          await field.fill('Do u like my lips?');
          console.log(' ✅ Caption escrito');
          captionFilled = true;
          break;
        }
      } catch (e) { continue; }
    }
    if (!captionFilled) {
      console.log(' ⚠️ No se encontró campo de caption');
    }
    await page.waitForTimeout(1000);
    // Tags
    console.log(' - Buscando campo de tags...');
    const tagsSelectors = [
      'input#react-tags-input',
      'input[placeholder*="tag" i]',
      'input[placeholder*="Add tag" i]'
    ];
    let tagsFilled = false;
    for (const selector of tagsSelectors) {
      try {
        const field = page.locator(selector).first();
        const isVisible = await field.isVisible({ timeout: 2000 }).catch(() => false);
        if (isVisible) {
          const tags = ['lips', 'sensual'];
          for (const tag of tags) {
            await field.type(tag, { delay: 100 });
            await field.press('Enter');
            await page.waitForTimeout(500);
          }
          console.log(' ✅ Tags escritos');
          tagsFilled = true;
          break;
        }
      } catch (e) { continue; }
    }
    if (!tagsFilled) {
      console.log(' ⚠️ No se encontró campo de tags');
    }
    await page.waitForTimeout(1000);
    // Paso 9: Publicar
    console.log('\n📍 Paso 9: Buscando botón "Post"...');
    const postSelectors = [
      'button:has-text("Post")',
      'button:has-text("Publish")',
      'button:has-text("Submit")',
      'button[type="submit"]'
    ];
    let posted = false;
    for (const selector of postSelectors) {
      try {
        await page.waitForSelector(selector, { timeout: 5000 });
        await page.click(selector);
        console.log(`✅ Click en "${selector}" realizado`);
        posted = true;
        break;
      } catch (e) { continue; }
    }
    if (!posted) {
      console.log('⚠️ No se encontró botón de publicación');
      console.log(' Revisa manualmente en el navegador');
    }

    // Espera a que cambie la URL tras publicar
    const urlAntes = page.url();
    await page.waitForFunction((oldUrl) => location.href !== oldUrl, urlAntes, { timeout: 180000});
    console.log('✅ La URL ha cambiado. El video ha sido procesado para publicación.');

    console.log('\n🎉 ¡Proceso completado!');
    // await page.screenshot({ path: 'final-screenshot.png', fullPage: true });
    // console.log('📸 Screenshot final: final-screenshot.png');
  } catch (error) {
    console.error('\n❌ ERROR:', error.message);
    // console.log('\n📸 Tomando screenshot de error...');
    // await page.screenshot({ path: 'error-screenshot.png', fullPage: true });
    // console.log('✅ Screenshot guardado: error-screenshot.png');
    console.log('\n💡 Revisa el screenshot para ver qué pasó');
  } finally {
    console.log('\n⏳ Manteniendo navegador abierto 15 segundos para revisión...');
    console.log(' Verifica si el video se publicó correctamente');
    await page.waitForTimeout(15000);
    await browser.close();
  }
}
automateXxxFollow().catch(console.error);