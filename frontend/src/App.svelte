<script>
  let url = $state('');
  let loading = $state(false);
  let result = $state(null);
  let error = $state('');

  async function verify() {
    if (!url.trim()) return;

    loading = true;
    error = '';
    result = null;

    try {
      const res = await fetch('http://localhost:8000/verify', {
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
    }
  }
</script>

<div class="hero">
  <h1>🐱 Lynx Fact Checker</h1>
  <p>Pega un link de TikTok y deja que Dark Michi lo analice</p>
</div>

<div class="input-area">
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
    <p>Dark Michi está analizando el contenido...</p>
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
  hecho con 🐱 por Dark Michi
</div>
