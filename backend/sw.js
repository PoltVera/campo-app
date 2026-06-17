const CACHE_NAME = 'campo-app-v1';
const urlsToCache = ['/', '/static/sw.js'];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    fetch(event.request).catch(() =>
      caches.match(event.request)
    )
  );
});

// Sincronizar registros pendientes cuando vuelve internet
self.addEventListener('sync', event => {
  if (event.tag === 'sync-registros') {
    event.waitUntil(sincronizarRegistros());
  }
});

async function sincronizarRegistros() {
  const db = await abrirDB();
  const pendientes = await obtenerPendientes(db);
  
  for (const registro of pendientes) {
    try {
      const res = await fetch('/registro', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(registro.datos)
      });
      if (res.ok) {
        await eliminarPendiente(db, registro.id);
      }
    } catch (e) {
      console.log('Sin internet, reintentará después');
    }
  }
}

function abrirDB() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open('campo-app-db', 1);
    req.onupgradeneeded = e => {
      e.target.result.createObjectStore('pendientes', { keyPath: 'id', autoIncrement: true });
    };
    req.onsuccess = e => resolve(e.target.result);
    req.onerror = reject;
  });
}

function obtenerPendientes(db) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pendientes', 'readonly');
    const req = tx.objectStore('pendientes').getAll();
    req.onsuccess = e => resolve(e.target.result);
    req.onerror = reject;
  });
}

function eliminarPendiente(db, id) {
  return new Promise((resolve, reject) => {
    const tx = db.transaction('pendientes', 'readwrite');
    const req = tx.objectStore('pendientes').delete(id);
    req.onsuccess = resolve;
    req.onerror = reject;
  });
}