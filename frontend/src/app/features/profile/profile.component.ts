import { Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { IconComponent } from '../../shared/icon.component';

@Component({
  selector: 'app-profile', standalone: true,
  imports: [RouterLink, IconComponent],
  templateUrl: './profile.component.html', styleUrl: './profile.component.scss',
})
export class ProfileComponent {
  readonly auth = inject(AuthService);
  readonly initial = computed(() => this.auth.user()?.name.trim().charAt(0).toLocaleUpperCase() || '');
}
