import {cloudflareTest} from '@cloudflare/vitest-plugin';
import {defineConfig} from 'vitest/config';

export default defineConfig({
 test:{include:['tests/mc-batch.vitest.mjs']},
 plugins:[cloudflareTest({wrangler:{configPath:'./tests/mc-batch.wrangler.json'}})],
});
