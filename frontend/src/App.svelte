<script>
  let url = $state('');
  let loading = $state(false);
  let result = $state(null);
  let error = $state('');
  let autoVerifying = $state(false);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  const pasos = [
    { num: 1, texto: 'Abre TikTok y busca el video que te interesa' },
    { num: 2, texto: 'Toca el botón de compartir (la flecha →)' },
    { num: 3, texto: 'Selecciona "Lynx Fact Checker" de la lista de apps' },
    { num: 4, texto: 'Listo, Dark Michi lo analizará automáticamente' },
  ];

  // Detectar cuando la app recibe un link compartido
  function detectarCompartido() {
    const params = new URLSearchParams(window.location.search);
    const sharedUrl = params.get('url');
    if (sharedUrl && sharedUrl.trim()) {
      url = sharedUrl.trim();
      autoVerifying = true;
      verify();
    }
  }

  // También escuchar mensajes del service worker
  if (typeof navigator !== 'undefined' && 'serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', (e) => {
      if (e.data?.url) {
        url = e.data.url;
        autoVerifying = true;
        verify();
      }
    });
  }

  async function verify() {
    if (!url.trim()) return;

    loading = true;
    error = '';
    result = null;

    try {
      const res = await fetch(`${API_URL}/verify`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      });

      const data = await res.json();

      if (!res.ok) {
        error = data.detail || 'Error del servidor';
      } else {
        result = data;
      }
    } catch (e) {
      error = 'No se pudo conectar con el servidor. ¿Está corriendo el backend?';
    } finally {
      loading = false;
      autoVerifying = false;
    }
  }

  // Ejecutar al montar el componente
  $effect(() => {
    detectarCompartido();
  });
</script>

<div class="hero">
  <h1>🐱 Lynx Fact Checker</h1>
  <p>Verifica datos de videos de TikTok con ayuda de Dark Michi</p>
</div>

<div class="tutorial">
  <h2 class="tutorial-title">📋 Cómo compartir un TikTok</h2>
  <div class="steps">
    {#each pasos as paso}
      <div class="step-card">
        <span class="step-num">{paso.num}</span>
        <p class="step-text">{paso.texto}</p>
      </div>
    {/each}
  </div>
</div>

<div class="input-area">
  {#if autoVerifying}
    <div class="auto-msg">🔗 Recibiendo enlace compartido...</div>
  {/if}
  <input
    type="url"
    placeholder="https://vt.tiktok.com/..."
    bind:value={url}
    disabled={loading}
    onkeydown={(e) => e.key === 'Enter' && verify()}
  />
  <button onclick={verify} disabled={loading || !url.trim()}>
    {loading ? 'Verificando...' : '🔍 Verificar'}
  </button>
</div>

{#if loading}
  <div class="spinner-wrap">
    <div class="spinner"></div>
    {#if autoVerifying}
      <p>Dark Michi recibió el enlace y está analizando...</p>
    {:else}
      <p>Dark Michi está analizando el contenido...</p>
    {/if}
  </div>
{/if}

{#if error}
  <div class="result-box error">{error}</div>
{/if}

{#if result}
  <div class="result-box success">
    <strong>✅ Decisión:</strong> {result.filter?.decision ?? 'N/A'}
    {' | '}
    <strong>Herramienta:</strong> {result.filter?.herramienta ?? 'N/A'}
    {' | '}
    <strong>Score:</strong> {result.filter?.score_claim ?? '?'}/4
    {'\n\n'}
    {result.combined_text || '(sin texto disponible)'}
    {#if result.whisper_needed}
      {'\n\n🎤 Requiere transcripción de audio (próximamente)'}
    {/if}
  </div>
{/if}

<div class="footer">
  hecho con &lt;3 por dark lynx
</div>
