const fs = require('fs');
const path = require('path');
const zlib = require('zlib');

const commit = '605197351a3c8bdd595af2d2a9bc3025bca48ea2';
const version = '5.22.0';
const localAppData = process.env.LOCALAPPDATA || path.join(process.env.USERPROFILE, 'AppData', 'Local');
const cacheDir = path.join(localAppData, 'prisma', 'binaries', version, commit, 'windows');
const enginesDir = path.join(__dirname, '..', 'node_modules', '@prisma', 'engines');
const prismaDir = path.join(__dirname, '..', 'node_modules', 'prisma');

fs.mkdirSync(cacheDir, { recursive: true });
fs.mkdirSync(enginesDir, { recursive: true });
fs.mkdirSync(prismaDir, { recursive: true });

function gunzipFile(source, target) {
  return new Promise((resolve, reject) => {
    const src = fs.createReadStream(source);
    const dest = fs.createWriteStream(target);
    const gunzip = zlib.createGunzip();

    src.pipe(gunzip).pipe(dest);
    dest.on('finish', () => {
      console.log(`[OK] Extraído: ${target} (${fs.statSync(target).size} bytes)`);
      resolve();
    });
    gunzip.on('error', reject);
    src.on('error', reject);
  });
}

async function run() {
  const qeGz = path.join(__dirname, '..', 'query_engine.dll.node.gz');
  const seGz = path.join(__dirname, '..', 'schema-engine.exe.gz');

  if (fs.existsSync(qeGz)) {
    console.log('Extraindo query_engine...');
    const target1 = path.join(enginesDir, 'query_engine-windows.dll.node');
    await gunzipFile(qeGz, target1);

    // Copiar para cache e nomes alternativos
    const targetCache = path.join(cacheDir, 'query_engine.dll.node');
    fs.copyFileSync(target1, targetCache);
    fs.copyFileSync(target1, path.join(enginesDir, 'query_engine.dll.node'));
    fs.copyFileSync(target1, path.join(prismaDir, 'query_engine-windows.dll.node'));
  }

  if (fs.existsSync(seGz)) {
    console.log('Extraindo schema-engine...');
    const targetSe = path.join(enginesDir, 'schema-engine-windows.exe');
    await gunzipFile(seGz, targetSe);

    const targetCacheSe = path.join(cacheDir, 'schema-engine.exe');
    fs.copyFileSync(targetSe, targetCacheSe);
    fs.copyFileSync(targetSe, path.join(prismaDir, 'schema-engine-windows.exe'));
    fs.copyFileSync(targetSe, path.join(enginesDir, 'schema-engine.exe'));
  }

  console.log('🎉 Prisma Engines configurados com sucesso!');
}

run().catch(console.error);
