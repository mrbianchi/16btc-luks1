import './app.css'
import App from './App.svelte'
import init, { luks_verify_wasm, luks_verify_master_key_wasm, luks_info_wasm } from '../../wasm/pkg'

async function main() {
  await init();

  const app = new App({
    target: document.getElementById('app')!,
    props: {
      luks_verify_wasm: luks_verify_wasm,
      luks_verify_master_key_wasm: luks_verify_master_key_wasm,
      luks_info_wasm: luks_info_wasm,
    }
  })
}

main();
