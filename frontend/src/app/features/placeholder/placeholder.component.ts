import { Component, computed, inject } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { IconComponent, IconName } from '../../shared/icon.component';

interface PlaceholderContent { eyebrow: string; title: string; description: string; icon: IconName; steps: readonly string[]; }

const CONTENT: Record<string, PlaceholderContent> = {
  settings: { eyebrow: 'Tu espacio', title: 'Todo a tu manera', description: 'La configuración de preferencias estará disponible en una próxima iteración. Esta demostración utiliza México y pesos mexicanos como referencia.', icon: 'settings', steps: ['Mercado: México', 'Moneda: MXN', 'Datos de demostración'] },
  profile: { eyebrow: 'Perfil de demostración', title: 'Hola, Alex Demo', description: 'Estás explorando un espacio personal de ejemplo. No existe una cuenta real ni se guardan datos personales en este slice.', icon: 'user', steps: ['Usuario ficticio', 'Sin autenticación', 'Exploración libre'] },
  'not-found': { eyebrow: 'Error 404', title: 'Esta página no está en el mapa', description: 'La dirección que buscas no existe. Vuelve al inicio para seguir explorando la demostración.', icon: 'search', steps: [] },
};

@Component({
  selector: 'app-placeholder', standalone: true,
  imports: [RouterLink, IconComponent],
  templateUrl: './placeholder.component.html', styleUrl: './placeholder.component.scss',
})
export class PlaceholderComponent {
  private readonly route = inject(ActivatedRoute);
  private readonly data = toSignal(this.route.data, { initialValue: this.route.snapshot.data });
  readonly kind = computed(() => String(this.data()['kind'] ?? 'not-found'));
  readonly content = computed(() => CONTENT[this.kind()] ?? CONTENT['not-found']);
}
