<script lang="ts">
  import { saveAs } from 'file-saver';

  export let luks_verify_wasm: (target: string, passphrase: string) => string;
  export let luks_verify_master_key_wasm: (target: string, masterKeyHex: string) => string;
  export let luks_info_wasm: (target: string) => string;

  interface SlotInfo {
    active: boolean;
    iterations: number;
    salt_hex: string;
    key_material_offset: number;
    stripes: number;
  }
  interface LuksInfo {
    version: number;
    cipher_name: string;
    cipher_mode: string;
    hash_spec: string;
    payload_offset: number;
    key_bytes: number;
    mk_digest_hex: string;
    mk_digest_salt_hex: string;
    mk_digest_iterations: number;
    uuid: string;
    slots: SlotInfo[];
  }
  interface VerifyResult {
    success: boolean;
    error?: string;
    master_key_hex?: string;
    slot?: number;
    uuid?: string;
    iterations?: number;
  }
  interface MkResult {
    success: boolean;
    error?: string;
  }

  let target: 'real' | 'test' = (localStorage.getItem('target') || 'real') as 'real' | 'test';
  let info: LuksInfo | null = null;
  let infoError = '';

  function loadInfo() {
    try {
      const parsed = JSON.parse(luks_info_wasm(target));
      if (parsed.error) {
        infoError = parsed.error;
        info = null;
      } else {
        info = parsed as LuksInfo;
        infoError = '';
      }
    } catch (e) {
      infoError = 'Could not read the LUKS header.';
      info = null;
    }
  }

  let password = localStorage.getItem('password') || '';
  let attempts = localStorage.getItem('attempts') || '';
  let lastAttemptedPassword = '';
  let feedbackMessage = '';
  let feedbackError = false;
  let unlocked = false;
  let masterKeyHex: string | null = null;
  let unlockedSlot: number | null = null;

  let masterKeyInput = localStorage.getItem('masterKeyInput') || '';
  let mkResult: string | null = null;
  let mkError: string | null = null;

  const activeSlots = info ? info.slots.filter((s) => s.active) : [];

  const tryPassphrase = (p: string) => {
    if (p.length === 0) return false;

    if (!attempts.split('\n').includes(p)) {
      attempts = attempts + (attempts.length > 0 ? '\n' : '') + p;
      localStorage.setItem('attempts', attempts);
    }

    let jsonStr = luks_verify_wasm(target, p);
    let result: VerifyResult;

    try {
      result = JSON.parse(jsonStr);
    } catch (e) {
      feedbackMessage = 'Error: invalid response from WASM.';
      feedbackError = true;
      unlocked = false;
      masterKeyHex = null;
      unlockedSlot = null;
      lastAttemptedPassword = p;
      return false;
    }

    if (result.success) {
      feedbackMessage = 'Success! The passphrase unlocks the LUKS volume.';
      feedbackError = false;
      unlocked = true;
      masterKeyHex = result.master_key_hex || null;
      unlockedSlot = result.slot ?? null;
    } else {
      feedbackMessage = `Error: ${result.error || 'The passphrase is not correct.'}`;
      feedbackError = true;
      unlocked = false;
      masterKeyHex = null;
      unlockedSlot = null;
    }

    lastAttemptedPassword = p;
    return result.success;
  };

  const verifyKey = () => {
    if (!masterKeyInput.trim()) {
      mkError = 'Paste a master key (32 bytes in hex).';
      mkResult = null;
      return;
    }

    let jsonStr = luks_verify_master_key_wasm(target, masterKeyInput);
    let result: MkResult;

    try {
      result = JSON.parse(jsonStr);
    } catch (e) {
      mkError = 'Invalid response from WASM.';
      mkResult = null;
      return;
    }

    if (result.success) {
      mkResult = '✓ The master key matches the header digest.';
      mkError = null;
    } else {
      mkError = result.error || 'The master key does not match.';
      mkResult = null;
    }
  };

  $: {
    localStorage.setItem('password', password);
    if (password !== lastAttemptedPassword) {
      feedbackMessage = '';
      feedbackError = false;
    }
  }

  $: {
    localStorage.setItem('masterKeyInput', masterKeyInput);
  }

  $: {
    localStorage.setItem('target', target);
    loadInfo();
    feedbackMessage = '';
    feedbackError = false;
    unlocked = false;
    masterKeyHex = null;
    unlockedSlot = null;
    mkResult = null;
    mkError = null;
  }

  function downloadAttempts() {
    const blob = new Blob([attempts], { type: 'text/plain;charset=utf-8' });
    saveAs(blob, 'attempts.txt');
  }
</script>

<main>
  <h1>LUKS Finder</h1>
  <p class="subtitle">{target === 'real' ? 'Tails 0.20.1 · persistent partition' : 'Test data (synthetic fixture)'}</p>

  <div class="target-switch">
    <button class:active={target === 'real'} on:click={() => (target = 'real')}>Real target</button>
    <button class:active={target === 'test'} on:click={() => (target = 'test')}>Test data</button>
  </div>

  {#if target === 'test'}
    <p class="test-hint">
      Test passphrase: <code>testpass</code><br />
      Expected master key: <code>000102030405060708090a0b0c0d0e0f101112131415161718191a1b1c1d1e1f</code>
    </p>
  {/if}

  {#if infoError}
    <div class="card error-card">
      <p class="error">{infoError}</p>
    </div>
  {/if}

  {#if info}
    <div class="card info-card">
      <h3>Target (LUKS1 header)</h3>
      <table>
        <tbody>
          <tr><td>UUID</td><td><code>{info.uuid}</code></td></tr>
          <tr><td>Version</td><td>{info.version}</td></tr>
          <tr><td>Cipher</td><td>{info.cipher_name}-{info.cipher_mode}</td></tr>
          <tr><td>Hash</td><td>{info.hash_spec}</td></tr>
          <tr><td>Master key</td><td>{info.key_bytes} bytes</td></tr>
          <tr><td>Digest MK</td><td><code>{info.mk_digest_hex}</code></td></tr>
          <tr><td>Digest iterations</td><td>{info.mk_digest_iterations}</td></tr>
          <tr><td>Active slots</td><td>{activeSlots.length} / {info.slots.length}</td></tr>
        </tbody>
      </table>
      {#each activeSlots as slot, i}
        <p class="slot-line">Active slot #{i}: {slot.iterations} PBKDF2-SHA1 iterations, {slot.stripes} stripes, key material at sector {slot.key_material_offset}.</p>
      {/each}
    </div>
  {/if}

  <div class="card">
    <h3>Manual Finder</h3>
    <p>
      <input
        placeholder="passphrase"
        bind:value={password}
        on:keydown={(e) => e.key === 'Enter' && tryPassphrase(password)}
      />
    </p>
    <button on:click={() => tryPassphrase(password)} disabled={password === lastAttemptedPassword}>
      Try
    </button>

    {#if feedbackMessage}
      <p class="feedback {feedbackError ? 'error' : 'success'}">{feedbackMessage}</p>
    {/if}

    {#if unlocked && masterKeyHex}
      <div class="result">
        <p class="success">Volume unlocked (slot {unlockedSlot}).</p>
        <p><strong>Master key (hex):</strong></p>
        <pre class="hex">{masterKeyHex}</pre>
        <p class="hint">This master key verifies the header digest and unlocks the volume.</p>
      </div>
    {/if}
  </div>

  <div class="card verifier-card">
    <h3>Master key verifier</h3>
    <p class="hint">Confirms that a recovered master key belongs to this volume.</p>
    <p>
      <textarea
        bind:value={masterKeyInput}
        rows="3"
        class="hex-input"
        placeholder="master key in hex (64 characters)"
      ></textarea>
    </p>
    <button on:click={verifyKey}>Verify key</button>
    {#if mkResult}
      <p class="feedback success">{mkResult}</p>
    {/if}
    {#if mkError}
      <p class="feedback error">{mkError}</p>
    {/if}
  </div>

  <div class="footer-area">
    Attempts: {attempts.split('\n').filter(Boolean).length} ({attempts.length} bytes)
    <br />
    <button on:click={downloadAttempts}>Download attempts</button>
  </div>
</main>

<style>
  :global(body) {
    margin: 0;
    display: flex;
    place-items: center;
    min-width: 320px;
    min-height: 100vh;
  }

  :global(#app) {
    width: 100%;
    max-width: 720px;
    margin: 0 auto;
    padding: 2rem;
    text-align: center;
  }

  main {
    color: #e0e0e0;
  }

  h1 {
    color: #ffffff;
    margin: 0;
  }

  h3 {
    color: #ffffff;
    margin-top: 0;
  }

  .subtitle {
    color: #888;
    margin-top: 0.25rem;
    margin-bottom: 1rem;
  }

  .target-switch {
    display: flex;
    gap: 0.5rem;
    justify-content: center;
    margin-bottom: 1rem;
  }

  .target-switch button.active {
    background-color: #2e7d32;
    border-color: #4caf50;
    color: #ffffff;
  }

  .test-hint {
    color: #888;
    font-size: smaller;
    margin: 0 0 1.5rem;
    text-align: center;
  }

  input,
  textarea {
    width: 100%;
    text-align: center;
    background: #2a2a2a;
    color: #e0e0e0;
    border: 1px solid #555;
    padding: 0.6em;
    border-radius: 6px;
    font-family: 'Courier New', Courier, monospace;
    font-size: larger;
    box-sizing: border-box;
  }

  textarea.hex-input {
    text-align: left;
    font-size: smaller;
    resize: vertical;
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

  * {
    font-family: 'Courier New', Courier, monospace;
    font-size: larger;
  }

  .card {
    margin-bottom: 2rem;
    border: 1px solid #555;
    padding: 1.5rem;
    border-radius: 8px;
    background: #1e1e1e;
    text-align: left;
  }

  .info-card table {
    width: 100%;
    border-collapse: collapse;
  }

  .info-card td {
    padding: 0.3rem 0.5rem;
    border-bottom: 1px solid #333;
    font-size: smaller;
    word-break: break-all;
  }

  .info-card td:first-child {
    color: #b0b0b0;
    white-space: nowrap;
    width: 40%;
  }

  code {
    background: #2a2a2a;
    color: #ffab40;
    padding: 0.1rem 0.35rem;
    border-radius: 4px;
    font-size: smaller;
    word-break: break-all;
  }

  .slot-line {
    font-size: smaller;
    color: #b0b0b0;
    margin: 0.5rem 0 0;
  }

  .feedback {
    margin-top: 1rem;
    text-align: center;
    font-weight: bold;
  }

  .success {
    color: #4caf50;
  }

  .error {
    color: #ef5350;
  }

  .result {
    margin-top: 1rem;
    text-align: center;
  }

  .result strong {
    color: #b0b0b0;
  }

  .hex {
    background: #2a2a2a;
    color: #81c784;
    padding: 0.75rem;
    border-radius: 4px;
    word-break: break-all;
    white-space: pre-wrap;
    font-size: small;
    max-height: 200px;
    overflow-y: auto;
    text-align: left;
    border: 1px solid #444;
    margin: 0.5rem 0;
  }

  .hint {
    color: #888;
    font-size: smaller;
    margin-top: 0.25rem;
  }

  .verifier-card button {
    background-color: #2e7d32;
    color: #ffffff;
    border: 1px solid #388e3c;
    width: 100%;
  }

  .verifier-card button:hover {
    background-color: #388e3c;
    border-color: #4caf50;
  }

  .error-card {
    text-align: center;
  }

  .footer-area {
    margin-top: 2rem;
    color: #888;
    font-size: 0.85em;
  }

  .footer-area button {
    font-size: 0.85em;
    margin-top: 0.5rem;
  }
</style>


