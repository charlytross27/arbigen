import { AfterViewInit, Component, ElementRef, OnDestroy, ViewChild, effect, input } from '@angular/core';
import * as echarts from 'echarts/core';
import { LineChart, BarChart, ScatterChart } from 'echarts/charts';
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components';
import { SVGRenderer } from 'echarts/renderers';
import type { EChartsOption, EChartsType } from 'echarts';

echarts.use([LineChart, BarChart, ScatterChart, GridComponent, LegendComponent, TooltipComponent, SVGRenderer]);

@Component({
  selector: 'app-analysis-chart', standalone: true,
  template: '<div #plot class="plot" role="img" [attr.aria-label]="description()"></div>',
  styles: [':host { display: block; min-width: 0; } .plot { width: 100%; height: 245px; }'],
})
export class AnalysisChartComponent implements AfterViewInit, OnDestroy {
  readonly option = input.required<EChartsOption>();
  readonly description = input.required<string>();
  @ViewChild('plot', { static: true }) private plot!: ElementRef<HTMLDivElement>;
  private chart?: EChartsType;
  private observer?: ResizeObserver;

  constructor() {
    effect(() => {
      const option = this.option();
      this.chart?.setOption(option, { notMerge: true });
    });
  }

  ngAfterViewInit(): void {
    this.chart = echarts.init(this.plot.nativeElement, undefined, { renderer: 'svg' });
    this.chart.setOption(this.option());
    this.observer = new ResizeObserver(() => this.chart?.resize());
    this.observer.observe(this.plot.nativeElement);
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
    this.chart?.dispose();
  }
}
