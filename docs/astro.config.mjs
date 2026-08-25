// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// The account-level custom domain (msadrashakouri.ir) is inherited by this
// project site automatically, so the docs are served at /DailyDriver/.
export default defineConfig({
  site: 'https://msadrashakouri.ir',
  base: '/DailyDriver/',
  integrations: [
    starlight({
      title: 'DailyDriver',
      description:
        'Personal, terminal-based life tracker documentation — prayers, sleep, journal, calendars, search.',
      editLink: {
        // Starlight appends the entry's path relative to the collection
        // directory (src/content/docs/...), so the base stops at docs/.
        baseUrl: 'https://github.com/MSadraShakouri/DailyDriver/edit/main/docs/',
      },
      sidebar: [
        { label: 'Overview', link: '/' },
        { label: 'Getting Started', link: '/getting-started/' },
        { label: 'Architecture', link: '/architecture/' },
        { label: 'Roadmap', link: '/roadmap/' },
        {
          label: 'Commands',
          items: [{ autogenerate: { directory: 'commands' } }],
        },
        {
          label: 'Concepts',
          items: [{ autogenerate: { directory: 'concepts' } }],
        },
        {
          label: 'Reference',
          items: [{ autogenerate: { directory: 'reference' } }],
        },
      ],
    }),
  ],
});
