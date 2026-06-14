<script lang="ts">
  import { onMount } from 'svelte';

  let {
    option,
    height = 280,
  }: {
    option: Record<string, unknown>;
    height?: number;
  } = $props();

  let el: HTMLDivElement = $state(null as unknown as HTMLDivElement);

  onMount(() => {
    let chart: ReturnType<typeof import('echarts')['init']> | null = null;
    let ro: ResizeObserver | null = null;

    import('echarts').then((echarts) => {
      chart = echarts.init(el, null, { renderer: 'canvas' });
      chart.setOption(option);
      ro = new ResizeObserver(() => chart!.resize());
      ro.observe(el);
    });

    return () => {
      ro?.disconnect();
      chart?.dispose();
    };
  });
</script>

<div bind:this={el} style="height: {height}px; width: 100%;"></div>
