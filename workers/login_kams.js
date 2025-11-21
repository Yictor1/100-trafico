const { test } = require('@playwright/test');
const path = require('path');
const fs = require('fs');

const MODEL_NAME = process.env.MODEL_NAME;

if (!MODEL_NAME) {
    throw new Error('❌ ERROR: Debes especificar el modelo para el login. Ejemplo: MODEL_NAME=yic npx playwright test ...');
}

const authFile = path.join(__dirname, `../modelos/${MODEL_NAME}/.auth/user.json`);
console.log(`👤 Configurando login para modelo: ${MODEL_NAME} `);
console.log(`🔐 Archivo de credenciales: ${authFile} `);

test('Login manual en Kams', async ({ browser }) => {
    test.setTimeout(10 * 60 * 1000); // 10 minutos de timeout

    // Crear directorio si no existe
    const authDir = path.dirname(authFile);
    if (!fs.existsSync(authDir)) {
        fs.mkdirSync(authDir, { recursive: true });
    }

    const context = await browser.newContext();
    const page = await context.newPage();

    console.log('🌐 Abriendo Kams login...');
    await page.goto('https://kams.com/login');

    console.log('⏸️  Por favor, inicia sesión manualmente en el navegador.');
    console.log('   El sistema detectará automáticamente cuando completes el login.');

    // Esperar a que salga de la página de login (máximo 8 minutos)
    const startTime = Date.now();
    const maxWait = 8 * 60 * 1000;

    while (Date.now() - startTime < maxWait) {
        const currentUrl = page.url();

        // Si ya no estamos en /login, el login fue exitoso
        if (!currentUrl.includes('/login')) {
            console.log(`✅ Login detectado! URL actual: ${currentUrl} `);
            break;
        }

        await page.waitForTimeout(2000); // Verificar cada 2 segundos
    }

    // Guardar credenciales
    console.log('💾 Guardando credenciales...');
    await context.storageState({ path: authFile });
    console.log('✅ Credenciales guardadas en:', authFile);

    // Esperar un poco más para que veas el mensaje
    await page.waitForTimeout(3000);

    await context.close();
});
