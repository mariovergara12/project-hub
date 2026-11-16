import { supabase } from './lib/supabase';
import { createApiClient } from './lib/api-client';
import type { CatalogItem, Page } from './types';

export const api = createApiClient({
    baseUrl: import.meta.env.VITE_API_BASE_URL || 'https://project-hub-api-ruby.vercel.app',
    auth: supabase.auth,
});

export async function loadCatalog(path: string, signal?: AbortSignal): Promise<Page<CatalogItem>> {
    const items: CatalogItem[] = [];
    const seen = new Set<string>();
    let cursor: string | null = null;
    do {
        const query = new URLSearchParams({ limit: '100' });
        if (cursor) query.set('cursor', cursor);
        const page: Page<CatalogItem> = await api.get(`${path}?${query}`, signal);
        items.push(...page.items);
        cursor = page.next_cursor;
        if (cursor && seen.has(cursor)) throw new Error('Could not load the complete catalog. Please retry.');
        if (cursor) seen.add(cursor);
    } while (cursor);
    return { items: items.sort((a, b) => a.name.localeCompare(b.name)), next_cursor: null };
}
