const { test, expect } = require('@playwright/test');
const path = require('path');
const fs = require('fs');

// ==========================================
// CONFIGURACIÓN
// ==========================================
const MODEL_NAME = process.env.MODEL_NAME;

if (!MODEL_NAME) {
  throw new Error('❌ ERROR: Debes especificar el modelo. Ejemplo: MODEL_NAME=yic npx playwright test ...');
}

// Ruta específica por modelo: Trafico/modelos/{modelo}/.auth/user.json
const authFile = path.join(__dirname, `../modelos/${MODEL_NAME}/.auth/user.json`);

console.log(`🔐 Usando archivo de autenticación para ${MODEL_NAME}: ${authFile}`);

const VIDEO_PATH = process.env.VIDEO_PATH;
const VIDEO_TITLE = process.env.VIDEO_TITLE || 'Default Title';
const VIDEO_TAGS = process.env.VIDEO_TAGS || 'tag1,tag2';

test.describe('Automatización API Kams', () => {

  test('Subida vía API Inyectada', async ({ browser }) => {
    // Validaciones previas
    if (!fs.existsSync(authFile)) {
      throw new Error('❌ No hay credenciales guardadas. Ejecuta el login manual primero.');
    }
    if (!VIDEO_PATH || !fs.existsSync(VIDEO_PATH)) {
      console.log('⚠️  No se especificó VIDEO_PATH o no existe. Se saltará la subida real.');
      return;
    }

    console.log('📂 Cargando sesión...');
    const context = await browser.newContext({ storageState: authFile });
    const page = await context.newPage();

    // 1. Ir a una página segura dentro del dominio para tener las cookies/tokens
    console.log('🌐 Navegando a Kams...');
    await page.goto('https://kams.com/upload');
    await page.waitForLoadState('networkidle');

    // 2. Truco del Input Oculto:
    // Creamos un input file en el DOM para cargar el video desde Node hacia el Navegador
    console.log('🔧 Preparando inyección de archivo...');
    await page.evaluate(() => {
      const input = document.createElement('input');
      input.type = 'file';
      input.id = 'gemini-upload-hack';
      input.style.display = 'none';
      document.body.appendChild(input);
    });

    // Usamos Playwright para poner el archivo en ese input
    await page.locator('#gemini-upload-hack').setInputFiles(VIDEO_PATH);

    // 3. Ejecutar la lógica de subida dentro del navegador
    console.log('🚀 Iniciando subida vía API interna...');

    const result = await page.evaluate(async ({ title, tags }) => {
      // --- CÓDIGO QUE CORRE DENTRO DEL NAVEGADOR ---

      // A. Obtener el archivo del input
      const fileInput = document.getElementById('gemini-upload-hack');
      const file = fileInput.files[0];
      if (!file) throw new Error('No se pudo cargar el archivo en el navegador');

      console.log(`📦 Preparando subida de: ${file.name} (${file.size} bytes)`);

      // A.1. Obtener token de autorización desde localStorage
      let authToken = null;

      console.log('🔍 Buscando token en localStorage...');
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        const value = localStorage.getItem(key);
        console.log(`   - ${key}: ${value ? value.substring(0, 40) + '...' : 'null'}`);

        // Buscar token (usualmente está en una key como 'token', 'auth_token', etc.)
        if (key.toLowerCase().includes('token') || key.toLowerCase().includes('auth')) {
          console.log(`🔑 Token encontrado en localStorage.${key}`);
          authToken = value;
          break;
        }
      }

      if (!authToken) {
        throw new Error('❌ No se encontró el token de autorización en localStorage. Asegúrate de estar logueado.');
      }

      console.log(`🔑 Usando token: ${authToken.substring(0, 30)}...`);

      // B. Paso 1: Subir Video (/v1/videos/upload)
      const formData = new FormData();
      formData.append('video', file);

      const uploadResponse = await fetch('https://api.kams.com/v1/videos/upload', {
        method: 'POST',
        body: formData,
        headers: {
          'Accept': 'application/json, text/plain, */*',
          'Authorization': `Bearer ${authToken}`
        }
      });

      if (!uploadResponse.ok) {
        const errorText = await uploadResponse.text();
        throw new Error(`Error en subida: ${uploadResponse.status} - ${errorText}`);
      }

      const uploadData = await uploadResponse.json();
      console.log('✅ Subida completada. Respuesta:', uploadData);

      // Obtener videoId de la respuesta
      const videoId = uploadData.id || uploadData.videoId || (uploadData.data && uploadData.data.id);

      if (!videoId) {
        return { success: false, step: 'upload', response: uploadData, message: 'No se encontró videoId en la respuesta' };
      }

      // C. Paso 2: Enviar Detalles (/v1/videos/upload-details)
      const detailsPayload = {
        videoId: videoId,
        title: title,
        tags: tags,
        is_nsfw: true,
        uploadDate: "",
        uploadDateTimezone: "America/Bogota"
      };

      const detailsResponse = await fetch('https://api.kams.com/v1/videos/upload-details', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'Authorization': `Bearer ${authToken}`
        },
        body: JSON.stringify(detailsPayload)
      });

      if (!detailsResponse.ok) {
        const errorText = await detailsResponse.text();
        throw new Error(`Error en detalles: ${detailsResponse.status} - ${errorText}`);
      }

      const detailsData = await detailsResponse.json();
      return { success: true, videoId, details: detailsData };

    }, { title: VIDEO_TITLE, tags: VIDEO_TAGS });

    console.log('🏁 Resultado final:', JSON.stringify(result, null, 2));

    if (result.success) {
      console.log(`✅ VIDEO PUBLICADO EXITOSAMENTE! ID: ${result.videoId}`);
    } else {
      console.error('❌ Falló la secuencia:', result.message);
      if (result.step === 'upload') {
        console.log('🔍 Respuesta de subida para análisis:', result.response);
      }
    }

    await context.close();
  });
});
