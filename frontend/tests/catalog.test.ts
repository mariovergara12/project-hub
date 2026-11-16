import { afterEach, expect, it, vi } from 'vitest';
vi.mock('../src/lib/supabase', () => ({ supabase: { auth: {} } }));
import { api, loadCatalog } from '../src/api';

afterEach(() => vi.restoreAllMocks());
it('loads every catalog page before offering selections and sorts names', async () => {
    const get = vi.spyOn(api, 'get');
    get.mockResolvedValueOnce({ items: [{ id: 'a', name: 'typescript' }], next_cursor: 'a' });
    get.mockResolvedValueOnce({ items: [{ id: 'b', name: 'react' }], next_cursor: null });
    const signal = new AbortController().signal;
    await expect(loadCatalog('/skills', signal)).resolves.toEqual({
        items: [{ id: 'b', name: 'react' }, { id: 'a', name: 'typescript' }], next_cursor: null,
    });
    expect(get).toHaveBeenNthCalledWith(1, '/skills?limit=100', signal);
    expect(get).toHaveBeenNthCalledWith(2, '/skills?limit=100&cursor=a', signal);
});
it('returns an empty catalog as an empty list', async () => {
    vi.spyOn(api, 'get').mockResolvedValue({ items: [], next_cursor: null });
    await expect(loadCatalog('/interests')).resolves.toEqual({ items: [], next_cursor: null });
});
it('stops if the server repeats a cursor rather than requesting forever', async () => {
    const get = vi.spyOn(api, 'get').mockResolvedValue({ items: [], next_cursor: 'same' });
    await expect(loadCatalog('/skills')).rejects.toThrow('complete catalog');
    expect(get).toHaveBeenCalledTimes(2);
});
