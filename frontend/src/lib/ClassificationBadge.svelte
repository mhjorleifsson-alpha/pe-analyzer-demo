<script lang="ts">
  import type { DealClassification } from './types';
  export let classification: DealClassification;

  const colours: Record<string, string> = {
    buyout:   'bg-purple-100 text-purple-800',
    growth:   'bg-green-100 text-green-800',
    minority: 'bg-blue-100 text-blue-800',
  };

  $: pct = Math.round(classification.confidence * 100);
</script>

<div class="rounded-xl border bg-white p-6 shadow-sm space-y-4">
  <div class="flex items-center justify-between">
    <span class="text-sm font-medium text-zinc-400 uppercase tracking-wide">Deal Type</span>
    <span class="rounded-full px-3 py-1 text-sm font-semibold {colours[classification.category] ?? 'bg-zinc-100 text-zinc-700'}">
      {classification.category.toUpperCase()}
    </span>
  </div>

  <div class="space-y-1">
    <div class="flex justify-between text-xs text-zinc-500">
      <span>Confidence</span>
      <span>{pct}%</span>
    </div>
    <div class="h-2 rounded-full bg-zinc-100 overflow-hidden">
      <div class="h-full rounded-full bg-blue-500 transition-all" style="width: {pct}%"></div>
    </div>
  </div>

  <p class="text-sm text-zinc-600 italic">{classification.reasoning}</p>
</div>
