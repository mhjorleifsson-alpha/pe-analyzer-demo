<script lang="ts">
  import Dropzone from '$lib/Dropzone.svelte';
  import AnalysisProgress from '$lib/AnalysisProgress.svelte';
  import VitalsCard from '$lib/VitalsCard.svelte';
  import ClassificationBadge from '$lib/ClassificationBadge.svelte';
  import MetricsTable from '$lib/MetricsTable.svelte';
  import type { DealAnalysis } from '$lib/types';

  type AppState = 'idle' | 'analyzing' | 'results' | 'error';

  let state: AppState = 'idle';
  let currentStep = '';
  let selectedFiles: File[] = [];
  let result: DealAnalysis | null = null;
  let errorMessage = '';

  function onFiles(e: CustomEvent<File[]>) {
    selectedFiles = e.detail;
  }

  async function analyze() {
    if (!selectedFiles.length) return;
    state = 'analyzing';
    currentStep = 'extracting';
    result = null;
    errorMessage = '';

    const formData = new FormData();
    for (const file of selectedFiles) {
      formData.append('files', file);
    }

    try {
      const response = await fetch('/analyze', { method: 'POST', body: formData });

      if (!response.ok || !response.body) {
        throw new Error(`Server error: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const event = JSON.parse(line.slice(6));

          if (event.type === 'progress') {
            currentStep = event.step;
          } else if (event.type === 'result') {
            result = event.data as DealAnalysis;
            state = 'results';
          } else if (event.type === 'error') {
            throw new Error(event.message);
          }
        }
      }
    } catch (err) {
      errorMessage = err instanceof Error ? err.message : String(err);
      state = 'error';
    }
  }

  function reset() {
    state = 'idle';
    selectedFiles = [];
    result = null;
    errorMessage = '';
    currentStep = '';
  }

  function copyJson() {
    if (result) navigator.clipboard.writeText(JSON.stringify(result, null, 2));
  }
</script>

<svelte:head>
  <title>PE Deal Analyzer</title>
</svelte:head>

<div class="min-h-screen bg-zinc-50">
  <header class="border-b bg-white px-6 py-4">
    <div class="max-w-3xl mx-auto flex items-center justify-between">
      <div>
        <h1 class="text-xl font-bold text-zinc-900">PE Deal Analyzer</h1>
        <p class="text-xs text-zinc-400">Private Equity Deal Sourcing Assistant</p>
      </div>
    </div>
  </header>

  <main class="max-w-3xl mx-auto px-6 py-10 space-y-6">

    {#if state === 'idle'}
      <Dropzone on:files={onFiles} />

      {#if selectedFiles.length > 0}
        <div class="rounded-lg bg-white border p-4 text-sm text-zinc-600">
          <p class="font-medium text-zinc-800 mb-2">{selectedFiles.length} file(s) selected:</p>
          <ul class="list-disc list-inside space-y-1">
            {#each selectedFiles as f}
              <li>{f.name}</li>
            {/each}
          </ul>
        </div>
      {/if}

      <button
        on:click={analyze}
        disabled={!selectedFiles.length}
        class="w-full rounded-lg bg-zinc-900 py-3 text-sm font-semibold text-white
               hover:bg-zinc-700 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
      >
        Analyze Deal
      </button>
    {/if}

    {#if state === 'analyzing'}
      <div class="rounded-xl border bg-white p-8 shadow-sm">
        <h2 class="font-semibold text-zinc-800 mb-6">Analyzing deal documents...</h2>
        <AnalysisProgress {currentStep} />
      </div>
    {/if}

    {#if state === 'results' && result}
      <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <VitalsCard vitals={result.vitals} />
        <ClassificationBadge classification={result.classification} />
      </div>
      <MetricsTable metrics={result.metrics} category={result.classification.category} />

      <div class="flex gap-3">
        <button
          on:click={copyJson}
          class="rounded-lg border px-4 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-100 transition-colors"
        >
          Copy JSON
        </button>
        <button
          on:click={reset}
          class="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-semibold text-white hover:bg-zinc-700 transition-colors"
        >
          Analyze Another Deal
        </button>
      </div>
    {/if}

    {#if state === 'error'}
      <div class="rounded-xl border border-red-200 bg-red-50 p-6">
        <p class="font-semibold text-red-700 mb-1">Analysis failed</p>
        <p class="text-sm text-red-600">{errorMessage}</p>
      </div>
      <button
        on:click={reset}
        class="rounded-lg border px-4 py-2 text-sm font-medium text-zinc-600 hover:bg-zinc-100"
      >
        Try Again
      </button>
    {/if}

  </main>
</div>
