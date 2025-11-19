#!/usr/bin/env node

/**
 * Script para crear tabla de un modelo nuevo en Supabase
 * Uso: node create_model_table.js <nombre_modelo>
 */

const { spawn } = require('child_process');

const modeloSlug = process.argv[2];

if (!modeloSlug) {
    console.log('❌ Error: Debes proporcionar el nombre del modelo');
    console.log('Uso: node create_model_table.js <nombre_modelo>');
    process.exit(1);
}

console.log(`🚀 Creando tabla para modelo: ${modeloSlug}\n`);

const env = {
    ...process.env,
    SUPABASE_ACCESS_TOKEN: 'sbp_114cffc9ead1a9878855bc481627037730b54b46'
};

const mcp = spawn('npx', [
    '-y',
    '@supabase/mcp-server-supabase@latest',
    '--project-ref=osdpemjvcsmfbacmjlcv'
], { env });

let buffer = '';
let requestId = 0;

function sendRequest(method, params) {
    requestId++;
    const request = {
        jsonrpc: '2.0',
        id: requestId,
        method,
        params
    };
    mcp.stdin.write(JSON.stringify(request) + '\n');
    return requestId;
}

mcp.stdout.on('data', (data) => {
    buffer += data.toString();
    const lines = buffer.split('\n');

    for (let i = 0; i < lines.length - 1; i++) {
        const line = lines[i].trim();
        if (line) {
            try {
                const response = JSON.parse(line);

                if (response.id === 1) {
                    console.log('✅ Conectado a Supabase\n');
                    console.log(`📋 Creando tabla "${modeloSlug}"...\n`);

                    const createTableSQL = `
CREATE TABLE IF NOT EXISTS ${modeloSlug} (
  video TEXT NOT NULL,
  caption TEXT NOT NULL,
  tags TEXT NOT NULL,
  plataforma TEXT NOT NULL,
  estado TEXT NOT NULL,
  scheduled_time VARCHAR NOT NULL
);
`;

                    sendRequest('tools/call', {
                        name: 'apply_migration',
                        arguments: {
                            name: `create_${modeloSlug}_table`,
                            query: createTableSQL
                        }
                    });
                }

                else if (response.id === 2) {
                    if (response.error) {
                        console.log('❌ Error:', response.error.message);
                        mcp.kill();
                        process.exit(1);
                    }

                    console.log(`✅ Tabla "${modeloSlug}" creada exitosamente!\n`);

                    setTimeout(() => {
                        mcp.kill();
                        process.exit(0);
                    }, 500);
                }

            } catch (e) {
                // Ignorar
            }
        }
    }

    buffer = lines[lines.length - 1];
});

mcp.stderr.on('data', (data) => {
    console.error('⚠️  stderr:', data.toString());
});

sendRequest('initialize', {
    protocolVersion: '2024-11-05',
    capabilities: {},
    clientInfo: { name: 'create-model-table', version: '1.0.0' }
});

setTimeout(() => {
    console.log('\n⏱️  Timeout');
    mcp.kill();
    process.exit(1);
}, 30000);
