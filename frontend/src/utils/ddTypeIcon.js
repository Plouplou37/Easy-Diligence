import {
  BriefcaseIcon,
  ChartBarIcon,
  CogIcon,
  DocumentTextIcon,
  GlobeEuropeAfricaIcon,
  ShieldCheckIcon,
} from '@heroicons/react/24/outline';

/**
 * Outline icon for a DD type, guessed from its name.
 *
 * The `icon` column holds emojis (📋, 💰…), which sat among the outline icons
 * of every other screen. Only the session creation page drew a real icon, with
 * its own keyword guess: this is that guess, shared.
 */
export const getDdTypeIcon = (ddType) => {
  const name = String((typeof ddType === 'object' ? ddType?.name : ddType) || '').toLowerCase();
  if (name.includes('financial') || name.includes('example')) return ChartBarIcon;
  if (name.includes('operational') || name.includes('operation')) return CogIcon;
  if (name.includes('legal') || name.includes('compliance') || name.includes('sanity')) return ShieldCheckIcon;
  if (name.includes('investment')) return BriefcaseIcon;
  if (name.includes('esg') || name.includes('environmental') || name.includes('sustainab')) return GlobeEuropeAfricaIcon;
  return DocumentTextIcon;
};
