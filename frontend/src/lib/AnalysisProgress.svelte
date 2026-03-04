<script lang="ts">
  export let currentStep: string = '';

  const steps = [
    { id: 'extracting', label: 'Extracting documents' },
    { id: 'classifying', label: 'Classifying deal' },
    { id: 'extracting_metrics', label: 'Extracting metrics' },
  ];

  function stepIndex(id: string): number {
    return steps.findIndex((s) => s.id === id);
  }

  $: currentIndex = stepIndex(currentStep);
</script>

<div class="space-y-3">
  {#each steps as step, i}
    <div class="flex items-center gap-3">
      <div
        class="h-6 w-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0
               {i < currentIndex ? 'bg-green-500 text-white' :
                i === currentIndex ? 'bg-blue-500 text-white animate-pulse' :
                'bg-zinc-200 text-zinc-400'}"
      >
        {#if i < currentIndex}✓{:else}{i + 1}{/if}
      </div>
      <span
        class="text-sm {i === currentIndex ? 'font-semibold text-zinc-800' : 'text-zinc-400'}"
      >
        {step.label}
      </span>
    </div>
  {/each}
</div>
