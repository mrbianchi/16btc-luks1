<script lang="ts">
  import { saveAs } from 'file-saver';
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher();

  let hashText = '';
  let error = '';
  let copied = false;

  async function load() {
    try {
      const res = await fetch('./hashcat-29511.txt');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      hashText = (await res.text()).trim();
    } catch (e) {
      error = 'No se pudo cargar el hash.';
    }
  }

  load();

  async function copy() {
    if (!hashText) return;
    try {
      await navigator.clipboard.writeText(hashText);
      copied = true;
      setTimeout(() => (copied = false), 1500);
    } catch (e) {
      error = 'No se pudo copiar. Seleccioná el texto y copiá manualmente.';
    }
  }

  function download() {
    const blob = new Blob([hashText], { type: 'text/plain;charset=utf-8' });
    saveAs(blob, 'hashcat-29511.txt');
  }

  function back() {
    dispatch('back');
  }
</script>

<main>
  <h1>Hashcat hash</h1>
  <p class="subtitle">LUKS1 · modo 14600 · Tails 0.20.1</p>

  <div class="toolbar">
    <button on:click={copy} disabled={!hashText}>{copied ? '¡Copiado!' : 'Copiar'}</button>
    <button on:click={download} disabled={!hashText}>Descargar</button>
    <button on:click={back}>← Volver al finder</button>
  </div>

  {#if error}
    <p class="feedback error">{error}</p>
  {/if}

  {#if hashText}
    <pre class="hash">{hashText}</pre>
  {:else if !error}
    <p class="hint">Cargando hash…</p>
  {/if}
</main>

<style>
  main {
    color: #e0e0e0;
    text-align: center;
  }

  h1 {
    color: #ffffff;
    margin: 0;
  }

  .subtitle {
    color: #888;
    margin-top: 0.25rem;
    margin-bottom: 1rem;
  }

  .toolbar {
    display: flex;
    gap: 0.5rem;
    justify-content: center;
    margin-bottom: 1rem;
  }

  button {
    border-radius: 8px;
    border: 1px solid #555;
    padding: 0.6em 1.2em;
    font-size: 1em;
    font-weight: 500;
    font-family: 'Courier New', Courier, monospace;
    background-color: #3a3a3a;
    color: #e0e0e0;
    cursor: pointer;
    transition: border-color 0.25s;
  }

  button:hover {
    border-color: #646cff;
  }

  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .hash {
    background: #1e1e1e;
    color: #81c784;
    border: 1px solid #444;
    border-radius: 6px;
    padding: 1rem;
    text-align: left;
    white-space: pre-wrap;
    word-break: break-all;
    font-family: 'Courier New', Courier, monospace;
    font-size: smaller;
    max-height: 60vh;
    overflow-y: auto;
    margin: 0;
  }

  .feedback {
    text-align: center;
    font-weight: bold;
  }

  .error {
    color: #ef5350;
  }

  .hint {
    color: #888;
    font-size: smaller;
  }
</style>
