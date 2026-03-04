<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  const dispatch = createEventDispatcher<{ files: File[] }>();

  let dragging = false;
  let inputEl: HTMLInputElement;

  const ACCEPTED = '.pdf,.docx,.xlsx,.pptx';

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    dragging = false;
    const files = Array.from(e.dataTransfer?.files ?? []);
    if (files.length) dispatch('files', files);
  }

  function handleChange(e: Event) {
    const input = e.target as HTMLInputElement;
    const files = Array.from(input.files ?? []);
    if (files.length) dispatch('files', files);
  }
</script>

<button
  class="w-full rounded-xl border-2 border-dashed p-12 text-center transition-colors
         {dragging ? 'border-blue-500 bg-blue-50' : 'border-zinc-300 hover:border-zinc-400 hover:bg-zinc-50'}"
  on:dragover|preventDefault={() => (dragging = true)}
  on:dragleave={() => (dragging = false)}
  on:drop={handleDrop}
  on:click={() => inputEl.click()}
  type="button"
>
  <input
    bind:this={inputEl}
    type="file"
    multiple
    accept={ACCEPTED}
    class="hidden"
    on:change={handleChange}
  />
  <div class="pointer-events-none space-y-2">
    <p class="text-lg font-medium text-zinc-700">Drop files here or click to upload</p>
    <p class="text-sm text-zinc-400">PDF · DOCX · XLSX · PPTX · Multiple files supported</p>
  </div>
</button>
