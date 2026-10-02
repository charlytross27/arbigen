import { Component, computed, inject, signal } from '@angular/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { map, timer } from 'rxjs';
import type { CatalogCampaign } from '../../core/models/catalog.model';
import { IconComponent } from '../../shared/icon.component';
import { CatalogDemoService } from './catalog-demo.service';

type CatalogScope = 'all' | 'examples' | 'session';

@Component({
  selector: 'app-catalogs', standalone: true,
  imports: [RouterLink, IconComponent],
  templateUrl: './catalogs.component.html', styleUrl: './catalogs.component.scss',
})
export class CatalogsComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  readonly catalog = inject(CatalogDemoService);

  private readonly routeParams = toSignal(this.route.paramMap, { initialValue: this.route.snapshot.paramMap });
  readonly ready = toSignal(timer(220).pipe(map(() => true)), { initialValue: false });
  readonly routeId = computed(() => this.routeParams().get('id'));
  readonly selected = computed(() => {
    const id = this.routeId();
    return id ? this.catalog.campaigns().find(item => item.id === id) ?? null : null;
  });
  readonly search = signal('');
  readonly scope = signal<CatalogScope>('all');
  readonly busyAction = signal<string | null>(null);
  readonly actionError = signal<string | null>(null);

  readonly filtered = computed(() => {
    const query = this.search().trim().toLocaleLowerCase('es-MX');
    return this.catalog.campaigns().filter(item =>
      (this.scope() === 'all' || item.origin === (this.scope() === 'examples' ? 'example' : 'session'))
      && (!query || `${item.name} ${item.productName} ${item.configuration.style}`.toLocaleLowerCase('es-MX').includes(query))
    );
  });

  readonly stats = computed(() => {
    const campaigns = this.catalog.campaigns();
    return {
      campaigns: campaigns.length,
      assets: campaigns.reduce((sum, item) => sum + item.assets.length, 0),
      session: campaigns.filter(item => item.origin === 'session').length,
    };
  });

  setSearch(event: Event): void { this.search.set((event.target as HTMLInputElement).value); }
  setScope(scope: CatalogScope): void { this.scope.set(scope); }
  formatDate(date: string): string { return new Intl.DateTimeFormat('es-MX', { day: 'numeric', month: 'short', year: 'numeric' }).format(new Date(date)); }

  deleteCampaign(id: string): void {
    this.catalog.deleteCampaign(id);
    if (this.routeId()) void this.router.navigate(['/catalogs']);
  }

  async addVariation(campaign: CatalogCampaign): Promise<void> {
    if (this.busyAction()) return;
    this.actionError.set(null);
    this.busyAction.set('add');
    try { await this.catalog.addVariation(campaign.id); }
    catch { this.actionError.set('No pudimos crear la vista local. Inténtalo de nuevo.'); }
    finally { this.busyAction.set(null); }
  }

  async regenerateAsset(campaign: CatalogCampaign, assetId: string): Promise<void> {
    if (this.busyAction()) return;
    this.actionError.set(null);
    this.busyAction.set(assetId);
    try { await this.catalog.regenerateAsset(campaign.id, assetId); }
    catch { this.actionError.set('No pudimos regenerar esta vista local. Inténtalo de nuevo.'); }
    finally { this.busyAction.set(null); }
  }
}
