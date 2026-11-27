// @vitest-environment jsdom
import type { ReactNode } from 'react';
import type { Session } from '@supabase/supabase-js';
import { act, cleanup, renderHook, waitFor } from '@testing-library/react';
import { afterEach, expect, it, vi } from 'vitest';
import { AuthContext } from '../src/auth-context';
import { refreshResources, useResource } from '../src/use-resource';

const mocks = vi.hoisted(() => ({ get: vi.fn() }));
vi.mock('../src/api', () => ({ api: { get: mocks.get } }));
afterEach(() => { cleanup(); vi.resetAllMocks(); });
it('cancels previous account requests and never renders their late data', async () => {
    let account = 'user-a';
    const completions: ((data: unknown) => void)[] = [];
    mocks.get.mockImplementation(() => new Promise(resolve => completions.push(resolve)));
    function Wrapper({ children }: { children: ReactNode }) {
        const session = { user: { id: account } } as Session;
        return <AuthContext value={{ session, loading: false, recovery: false, finishRecovery: () => {} }}>{children}</AuthContext>;
    }
    const { result, rerender } = renderHook(() => useResource<{ owner: string }>('/me'), { wrapper: Wrapper });
    await waitFor(() => expect(mocks.get).toHaveBeenCalledTimes(1));
    account = 'user-b';
    rerender();
    await waitFor(() => expect(mocks.get).toHaveBeenCalledTimes(2));
    expect(mocks.get.mock.calls[0][1].aborted).toBe(true);
    await act(async () => completions[0]({ owner: 'user-a' }));
    expect(result.current.data).toBeUndefined();
    expect(result.current.loading).toBe(true);
    await act(async () => completions[1]({ owner: 'user-b' }));
    expect(result.current.data).toEqual({ owner: 'user-b' });
});
it('hides old filter results immediately and ignores late responses', async () => {
    const completions: ((data: unknown) => void)[] = [];
    mocks.get.mockImplementation(() => new Promise(resolve => completions.push(resolve)));
    const { result, rerender } = renderHook(({ path }) => useResource<string[]>(path), {
        initialProps: { path: '/projects?q=old' },
    });
    await act(async () => completions[0](['old project']));
    expect(result.current.data).toEqual(['old project']);
    rerender({ path: '/projects?q=new' });
    expect(result.current.data).toBeUndefined();
    expect(result.current.loading).toBe(true);
    await act(async () => completions[1](['new project']));
    expect(result.current.data).toEqual(['new project']);
});

it('refreshes all active filtered lists for changed resources only', async () => {
    mocks.get.mockResolvedValue([]);
    const teams = renderHook(() => useResource('/me/teams?status=open'));
    renderHook(() => useResource('/projects?limit=4'));
    await waitFor(() => expect(mocks.get).toHaveBeenCalledTimes(2));
    act(() => refreshResources(['/me/teams']));
    await waitFor(() => expect(mocks.get).toHaveBeenCalledTimes(3));
    expect(mocks.get.mock.calls[2][0]).toBe('/me/teams?status=open');
    await waitFor(() => expect(teams.result.current.loading).toBe(false));
});
