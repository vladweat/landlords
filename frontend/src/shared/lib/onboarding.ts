const ONBOARDING_KEY = 'landlords_onboarding_completed';

export function isOnboardingCompleted(): boolean {
  return localStorage.getItem(ONBOARDING_KEY) === 'true';
}

export function setOnboardingCompleted(): void {
  localStorage.setItem(ONBOARDING_KEY, 'true');
}

export function resetOnboarding(): void {
  localStorage.removeItem(ONBOARDING_KEY);
}
