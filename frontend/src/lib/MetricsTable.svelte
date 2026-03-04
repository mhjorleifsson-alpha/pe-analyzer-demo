<script lang="ts">
  import type { BuyoutMetrics, GrowthMetrics, MinorityMetrics, DealCategory } from './types';
  export let metrics: BuyoutMetrics | GrowthMetrics | MinorityMetrics;
  export let category: DealCategory;

  const LABELS: Record<string, Record<string, string>> = {
    buyout: {
      revenue: 'Revenue',
      ebitda: 'EBITDA',
      ebitda_margin: 'EBITDA Margin',
      revenue_growth_rate: 'Revenue Growth',
      net_debt: 'Net Debt',
      leverage_ratio: 'Leverage Ratio (x)',
    },
    growth: {
      revenue: 'Revenue',
      arr: 'ARR',
      mrr: 'MRR',
      revenue_growth_rate: 'Revenue Growth',
      gross_margin: 'Gross Margin',
      net_revenue_retention: 'Net Revenue Retention',
      debt_levels: 'Debt Levels',
    },
    minority: {
      revenue: 'Revenue',
      ebitda: 'EBITDA',
      arr: 'ARR',
      revenue_growth_rate: 'Revenue Growth',
      ebitda_margin: 'EBITDA Margin',
      gross_margin: 'Gross Margin',
      debt_levels: 'Debt Levels',
    },
  };

  $: rows = Object.entries(LABELS[category] ?? {}).map(([key, label]) => ({
    label,
    value: (metrics as unknown as Record<string, string | null>)[key] ?? null,
  }));
</script>

<div class="rounded-xl border bg-white shadow-sm overflow-hidden">
  <div class="px-6 py-4 border-b flex items-center justify-between">
    <h3 class="font-semibold text-zinc-800">Key Metrics</h3>
  </div>
  <table class="w-full text-sm">
    <tbody>
      {#each rows as row, i}
        <tr class="{i % 2 === 0 ? 'bg-white' : 'bg-zinc-50'}">
          <td class="px-6 py-3 font-medium text-zinc-500 w-1/2">{row.label}</td>
          <td class="px-6 py-3 text-zinc-800 font-mono">{row.value ?? '—'}</td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>
