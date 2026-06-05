<script>
  let url = $state('');
  let loading = $state(false);
  /** @type {any} */
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

  function aiStructured() {
    return result?.ai_analysis?.structured ?? null;
  }

  function claims() {
    return aiStructured()?.claims ?? [];
  }

  function hasVerifiableClaims() {
    const structured = aiStructured();
    if (structured && structured.tiene_claims_verificables === false) return false;
    if (structured && structured.tiene_claims_verificables === true) return true;

    return claims().some((/** @type {any} */ claim) => {
      const verdict = String(claim.veredicto ?? '').toLowerCase();
      return verdict && !['opinion', 'opinión', 'no verificable', 'unverifiable'].includes(verdict);
    });
  }

  function isEntertainmentOrNoClaims() {
    const decision = result?.filter?.decision ?? '';
    const tool = result?.filter?.herramienta ?? '';
    return !hasVerifiableClaims() || decision === 'STOP' || tool === '🛑 Ninguna';
  }

  function verdictTitle() {
    if (!result) return '';
    if (result.ai_analysis && !aiStructured()) return 'La IA no respondió completo';
    if (isEntertainmentOrNoClaims()) return 'Parece entretenimiento o no tiene datos verificables';
    return 'Encontré datos para revisar';
  }

  function verdictSubtitle() {
    if (!result) return '';
    if (result.ai_analysis && !aiStructured()) {
      return 'El contenido fue leído, pero el modelo no regresó un resumen estructurado. Puedes intentar de nuevo en unos segundos.';
    }
    if (isEntertainmentOrNoClaims()) {
      return 'No detecté afirmaciones concretas que valga la pena fact-checkear. Aun así te dejo lo que sí pude leer del TikTok.';
    }
    return 'Dark Michi separó los claims para que puedas leer rápido qué se está diciendo y qué tan verificable es.';
  }

  function verdictIcon() {
    if (!result) return '🔎';
    if (result.ai_analysis && !aiStructured()) return '⏳';
    if (isEntertainmentOrNoClaims()) return '🎭';
    return '🧠';
  }

  function evidenceItems() {
    const items = [];
    if (result?.extractor?.description) items.push('Descripción del TikTok');
    if (result?.whisper_output) items.push('Audio transcrito con Whisper');
    if (result?.extractor?.text_slides?.length) items.push('Texto en slides');
    if (result?.extractor?.extracted_text?.length) items.push('OCR de imágenes');
    return items;
  }

  function summaryText() {
    return aiStructured()?.resumen || result?.filter?.razon || 'No hay resumen disponible todavía.';
  }

  function resetResult() {
    result = null;
    error = '';
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
  <section class:soft-result={isEntertainmentOrNoClaims()} class="result-page">
    <div class="result-hero-card">
      <div class="result-icon">{verdictIcon()}</div>
      <div>
        <p class="eyebrow">Lectura rápida</p>
        <h2>{verdictTitle()}</h2>
        <p>{verdictSubtitle()}</p>
      </div>
    </div>

    <div class="result-grid">
      <article class="insight-card primary-card">
        <span class="card-label">Resumen IA</span>
        <p class="summary-text">{summaryText()}</p>
      </article>

      <article class="insight-card mini-card">
        <span class="card-label">Decisión</span>
        <strong>{result.filter?.decision ?? 'N/A'}</strong>
        <small>{result.filter?.herramienta ?? 'Sin herramienta'}</small>
      </article>

      <article class="insight-card mini-card">
        <span class="card-label">Score</span>
        <strong>{result.filter?.score_claim ?? 0}/4</strong>
        <small>señales de claim concreto</small>
      </article>
    </div>

    {#if claims().length && hasVerifiableClaims()}
      <section class="section-card">
        <div class="section-heading">
          <span>🧩</span>
          <div>
            <h3>Claims detectados</h3>
            <p>Lo importante, separado en piezas rápidas.</p>
          </div>
        </div>

        <div class="claims-list">
          {#each claims() as claim}
            <article class="claim-card">
              <div class="claim-topline">
                <strong>{claim.veredicto ?? 'sin veredicto'}</strong>
                <span>{claim.confianza ?? 'confianza no indicada'}</span>
              </div>
              <p class="claim-text">{claim.claim}</p>
              <p class="claim-reason">{claim.justificacion}</p>
            </article>
          {/each}
        </div>
      </section>
    {:else}
      <section class="section-card empty-state">
        <div class="section-heading">
          <span>🎬</span>
          <div>
            <h3>No hay claims claros que verificar</h3>
            <p>Este TikTok parece más de entretenimiento, opinión o curiosidad ligera.</p>
          </div>
        </div>
        <p>
          No significa que el video sea malo. Solo quiere decir que no encontré una afirmación concreta tipo
          “X causa Y”, “según tal fuente”, “esto cura”, “esto pasó en tal fecha” o algo que se pueda contrastar bien.
        </p>
      </section>
    {/if}

    <section class="section-card evidence-card">
      <div class="section-heading">
        <span>🔎</span>
        <div>
          <h3>Qué leyó Dark Michi</h3>
          <p>Fuentes usadas para entender el contenido.</p>
        </div>
      </div>

      <div class="evidence-list">
        {#each evidenceItems() as item}
          <span>{item}</span>
        {/each}
        {#if !evidenceItems().length}
          <span>Solo metadata básica</span>
        {/if}
      </div>
    </section>

    {#if result.whisper_output}
      <details class="transcript-card">
        <summary>🎤 Ver transcripción del audio</summary>
        <p>{result.whisper_output}</p>
      </details>
    {/if}

    <div class="result-actions">
      <button class="secondary-button" onclick={resetResult}>Analizar otro TikTok</button>
    </div>
  </section>
{/if}

<div class="footer">
  hecho con &lt;3 por dark lynx
</div>
