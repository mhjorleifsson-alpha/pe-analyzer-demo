<script lang="ts">
  import type { CompanyVitals } from './types';
  export let vitals: CompanyVitals;

  const fields: { label: string; key: keyof CompanyVitals }[] = [
    { label: 'Industry', key: 'industry' },
    { label: 'Sector', key: 'sector' },
    { label: 'Geography', key: 'geography' },
    { label: 'Founded', key: 'founding_year' },
  ];
</script>

<div class="rounded-xl border bg-white p-6 shadow-sm">
  <h2 class="text-xl font-bold text-zinc-900 mb-1">{vitals.name ?? '—'}</h2>
  {#if vitals.description}
    <p class="text-sm text-zinc-500 mb-4">{vitals.description}</p>
  {/if}
  <dl class="grid grid-cols-2 gap-x-4 gap-y-2">
    {#each fields as f}
      <dt class="text-xs font-medium text-zinc-400 uppercase tracking-wide">{f.label}</dt>
      <dd class="text-sm text-zinc-700">{vitals[f.key] ?? '—'}</dd>
    {/each}
  </dl>
</div>
